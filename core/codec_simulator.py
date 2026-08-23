"""
Lossy codec artifact generator — the heart of the simulation.

Performs an in-memory encode → decode loop through FFmpeg (via PyAV)
to capture the exact sample-level changes introduced by lossy codecs:

* Ogg Vorbis (``libvorbis``) at 160 / 320 kbps — Spotify simulation
* AAC (``aac``) at 256 kbps — Apple Music / YouTube / Tidal simulation

**Encoder-delay compensation** is critical for sample-accurate phase
alignment between the original and decoded buffers.  Lossy codecs add
priming samples (encoder delay / lookahead) at the start of the stream.
We detect this delay using:

1. The codec context's ``delay`` property (if reported).
2. A cross-correlation fallback on the first ~1 s of audio to find the
   precise sample offset.

After alignment the decoded buffer is trimmed/padded to exactly match
the original sample count.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def _add_audio_stream(container, codec: str, sample_rate: int):
    """Add an audio stream, handling codec availability and experimental flags.

    For Vorbis encoding, ``libvorbis`` is preferred but not always available
    in bundled PyAV builds.  The fallback ``vorbis`` (native FFmpeg encoder)
    requires ``strict_std_compliance = -2`` (experimental).
    """
    import av  # noqa: F811

    # Try preferred codec first
    try:
        stream = container.add_stream(codec, rate=sample_rate)
        return stream
    except Exception:
        pass

    # Fallback for vorbis
    if "vorbis" in codec:
        logger.info("libvorbis unavailable, using native vorbis (experimental)")
        stream = container.add_stream("vorbis", rate=sample_rate)
        stream.codec_context.options["strict"] = "experimental"
        return stream

    # Fallback for AAC (unlikely to need it, but just in case)
    logger.warning("Codec '%s' unavailable, trying fallback", codec)
    stream = container.add_stream("aac", rate=sample_rate)
    return stream


def encode_decode(
    audio: np.ndarray,
    sample_rate: int,
    codec: str,
    bitrate: int,
    container: str,
) -> np.ndarray:
    """Encode *audio* to a lossy codec and decode back to PCM.

    Parameters
    ----------
    audio : np.ndarray
        Float32 stereo audio, shape ``(samples, channels)``.
    sample_rate : int
        Sample rate in Hz.
    codec : str
        FFmpeg codec name (``'libvorbis'`` or ``'aac'``).
    bitrate : int
        Target bitrate in bits/s (e.g. ``160_000``).
    container : str
        Container format (``'ogg'`` or ``'adts'``).

    Returns
    -------
    np.ndarray
        Decoded audio, float32, shape ``(samples, channels)`` —
        same sample count as the input, phase-aligned.
    """
    import av  # lazy import so the module is importable before av is installed

    if audio.ndim == 1:
        audio = audio[:, np.newaxis]

    original_length, channels = audio.shape
    layout = "mono" if channels == 1 else "stereo"

    # ── ENCODE ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    out_container = av.open(buf, mode="w", format=container)

    stream = _add_audio_stream(out_container, codec, sample_rate)

    stream.bit_rate = bitrate
    stream.layout = layout

    # Codec frame size (samples per frame).  Typical values:
    # libvorbis: variable (often 64–8192), aac: 1024
    frame_size = stream.codec_context.frame_size
    if not frame_size or frame_size <= 0:
        frame_size = 1024

    # Record encoder delay (priming samples) for phase compensation
    encoder_delay: int = getattr(stream.codec_context, "delay", 0) or 0

    pts = 0
    for start_idx in range(0, original_length, frame_size):
        end_idx = min(start_idx + frame_size, original_length)
        chunk = audio[start_idx:end_idx].T.copy().astype(np.float32)

        # Pad the last chunk to a full frame if needed
        actual_samples = chunk.shape[1]
        if actual_samples < frame_size:
            chunk = np.pad(chunk, ((0, 0), (0, frame_size - actual_samples)))

        frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout=layout)
        frame.sample_rate = sample_rate
        frame.pts = pts
        pts += frame_size

        for packet in stream.encode(frame):
            out_container.mux(packet)

    # Flush the encoder (drains any remaining buffered audio)
    for packet in stream.encode(None):
        out_container.mux(packet)

    out_container.close()

    # ── DECODE ──────────────────────────────────────────────────────
    buf.seek(0)
    in_container = av.open(buf, mode="r")

    decoded_chunks: list[np.ndarray] = []
    for frame in in_container.decode(audio=0):
        arr = frame.to_ndarray()  # planar: (channels, samples)
        if frame.format.is_planar:
            arr = arr.T  # → (samples, channels)
        arr = arr.astype(np.float32)
        decoded_chunks.append(arr)

    in_container.close()

    if not decoded_chunks:
        logger.error("Codec decode produced no frames")
        return audio.copy()

    decoded = np.concatenate(decoded_chunks, axis=0)

    # Ensure correct channel count
    if decoded.ndim == 1:
        decoded = decoded[:, np.newaxis]
    if decoded.shape[1] != channels:
        # Reshape if planar/interleaved mismatch produced wrong dim
        if decoded.shape[0] == channels and decoded.shape[1] != channels:
            decoded = decoded.T

    # ── PHASE ALIGNMENT ────────────────────────────────────────────
    decoded = _align_phase(audio, decoded, encoder_delay, original_length, channels)

    return decoded


# ════════════════════════════════════════════════════════════════════
#  Phase alignment helpers
# ════════════════════════════════════════════════════════════════════

def _align_phase(
    original: np.ndarray,
    decoded: np.ndarray,
    encoder_delay: int,
    target_length: int,
    channels: int,
) -> np.ndarray:
    """Strip encoder priming samples and trim/pad to match *target_length*.

    Tries the reported *encoder_delay* first.  If it is zero or produces
    a poor correlation, falls back to a cross-correlation search.
    """
    # Try encoder-reported delay first
    if encoder_delay > 0:
        offset = encoder_delay
        logger.debug("Using encoder-reported delay: %d samples", offset)
    else:
        # Cross-correlation fallback
        offset = _find_offset_xcorr(original, decoded)
        logger.debug("Cross-correlation found offset: %d samples", offset)

    # Validate the offset with a quick correlation check
    if offset > 0 and encoder_delay > 0:
        # Double-check: if xcorr gives a very different result, prefer xcorr
        xcorr_offset = _find_offset_xcorr(original, decoded)
        if abs(xcorr_offset - offset) > 64:
            logger.info(
                "Encoder delay (%d) disagrees with xcorr (%d); using xcorr",
                offset,
                xcorr_offset,
            )
            offset = xcorr_offset

    # Apply the offset
    if 0 < offset < decoded.shape[0]:
        decoded = decoded[offset:]

    # Trim or pad to exact original length
    if decoded.shape[0] > target_length:
        decoded = decoded[:target_length]
    elif decoded.shape[0] < target_length:
        pad = np.zeros(
            (target_length - decoded.shape[0], channels), dtype=np.float32
        )
        decoded = np.concatenate([decoded, pad], axis=0)

    return decoded


def _find_offset_xcorr(
    original: np.ndarray,
    decoded: np.ndarray,
    max_offset: int = 8192,
) -> int:
    """Find the sample delay between *original* and *decoded* via
    normalised cross-correlation on the first ~1 s of channel 0.

    Returns the offset (in samples) at which the decoded signal
    best aligns with the original.
    """
    # Use first ~1 second of channel 0
    seg_len = min(original.shape[0], 44100)
    search_len = min(decoded.shape[0], seg_len + max_offset)

    if seg_len < 256 or search_len < 256:
        return 0

    orig_seg = original[:seg_len, 0].astype(np.float64)
    dec_seg = decoded[:search_len, 0].astype(np.float64)

    # Subtract means for proper normalisation
    orig_seg = orig_seg - np.mean(orig_seg)
    dec_seg = dec_seg - np.mean(dec_seg)

    orig_energy = np.sqrt(np.sum(orig_seg ** 2))
    if orig_energy < 1e-10:
        return 0

    # mode='valid' slides orig_seg over dec_seg
    correlation = np.correlate(dec_seg, orig_seg, mode="valid")

    if correlation.size == 0:
        return 0

    offset = int(np.argmax(np.abs(correlation)))

    # Sanity: offset must be reasonable
    if offset > max_offset:
        return 0

    return offset
