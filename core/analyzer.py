"""
Audio measurement conforming to ITU-R BS.1770-4.

* **Integrated Loudness (LUFS)** — via ``pyloudnorm`` which implements
  the standard two-stage gating:
    1. Absolute gate at −70 LUFS
    2. Relative gate at −10 LU below the ungated loudness
* **True Peak (dBTP)** — 4× polyphase oversampling per Annex 2 of
  BS.1770-4, using ``scipy.signal.resample_poly``.
* **Gate Map** — per-block gating analysis for visualisation of which
  400 ms blocks pass/fail the BS.1770-4 relative gate.
* **True Peak Violations** — timestamp array of windows where the
  4× oversampled true peak exceeds 0.0 dBTP (intersample clipping).
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import pyloudnorm as pyln
from scipy.signal import resample_poly

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Existing public API
# ═══════════════════════════════════════════════════════════════════

def measure_loudness(audio: np.ndarray, sample_rate: int) -> float:
    """Return integrated loudness in LUFS (BS.1770-4 with gating).

    Parameters
    ----------
    audio : np.ndarray
        Audio data, shape ``(samples,)`` or ``(samples, channels)``,
        float32/float64 normalised to [-1, 1].
    sample_rate : int
        Sample rate in Hz.

    Returns
    -------
    float
        Integrated loudness in LUFS.  Returns ``-inf`` for silence.
    """
    meter = pyln.Meter(sample_rate, block_size=0.4)
    loudness: float = meter.integrated_loudness(audio)
    return loudness


def measure_true_peak(audio: np.ndarray) -> float:
    """Return the True Peak level in dBTP (BS.1770-4 Annex 2).

    Uses 4× polyphase FIR oversampling on each channel independently
    and returns the maximum across all channels.

    Parameters
    ----------
    audio : np.ndarray
        Audio data, shape ``(samples,)`` or ``(samples, channels)``.

    Returns
    -------
    float
        True peak in dBTP.  Returns ``-inf`` for silence.
    """
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]

    max_peak = 0.0
    for ch in range(audio.shape[1]):
        # 4× upsample using a polyphase FIR filter
        upsampled = resample_poly(audio[:, ch].astype(np.float64), up=4, down=1)
        channel_peak = float(np.max(np.abs(upsampled)))
        max_peak = max(max_peak, channel_peak)

    if max_peak < 1e-12:
        return float("-inf")

    return 20.0 * np.log10(max_peak)


# ═══════════════════════════════════════════════════════════════════
#  Module 1 — Relative Gate Waveform Map
# ═══════════════════════════════════════════════════════════════════

def compute_gate_map(
    audio: np.ndarray,
    sample_rate: int,
    block_sec: float = 0.4,
    hop_sec: float = 0.1,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Compute which 400 ms blocks pass the BS.1770-4 two-stage gate.

    This mirrors the standard algorithm (without K-weighting for speed)
    which is visually accurate for typical music content.

    Parameters
    ----------
    audio : np.ndarray
        Stereo float32 audio, shape ``(samples, channels)``.
    sample_rate : int
        Sample rate in Hz.
    block_sec : float
        Block duration in seconds (default 0.4 per BS.1770-4).
    hop_sec : float
        Hop / overlap step in seconds (default 0.1 = 75 % overlap).

    Returns
    -------
    block_centers : np.ndarray
        Centre time (seconds) of each block.
    included : np.ndarray[bool]
        ``True`` if the block passes both absolute and relative gates.
    block_lufs : np.ndarray
        Per-block loudness estimate (LUFS-like, without K-weighting).
    rel_threshold : float
        The relative-gate threshold in LUFS.
    """
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]

    block_samples = int(block_sec * sample_rate)
    hop_samples = int(hop_sec * sample_rate)
    n_samples = audio.shape[0]

    # Channel weights per BS.1770: L=R=C=1.0, Ls=Rs=1.41
    weights = np.ones(audio.shape[1])

    # ── Vectorised per-block mean-square ───────────────────────────
    n_blocks = max(1, (n_samples - block_samples) // hop_samples + 1)
    starts = np.arange(n_blocks) * hop_samples
    block_centers = (starts + block_samples / 2) / sample_rate

    block_powers = np.empty(n_blocks, dtype=np.float64)
    for i, s in enumerate(starts):
        blk = audio[s : s + block_samples]
        ms = np.mean(blk.astype(np.float64) ** 2, axis=0)
        block_powers[i] = np.dot(ms, weights)

    # Convert to LUFS-like scale: −0.691 + 10·log₁₀(Σ)
    with np.errstate(divide="ignore"):
        block_lufs = np.where(
            block_powers > 1e-12,
            -0.691 + 10.0 * np.log10(block_powers),
            -np.inf,
        )

    # ── Absolute gate: −70 LUFS ────────────────────────────────────
    abs_mask = block_lufs >= -70.0
    valid_abs = block_lufs[abs_mask]

    if valid_abs.size == 0:
        return block_centers, np.zeros(n_blocks, dtype=bool), block_lufs, -70.0

    # ── Intermediate loudness (mean power of abs-gated blocks) ─────
    intermediate = 10.0 * np.log10(np.mean(10.0 ** (valid_abs / 10.0)))

    # ── Relative gate: −10 LU below intermediate ──────────────────
    rel_threshold = intermediate - 10.0
    included = abs_mask & (block_lufs >= rel_threshold)

    logger.debug(
        "Gate map: %d / %d blocks pass relative gate at %.1f LUFS",
        np.sum(included), n_blocks, rel_threshold,
    )
    return block_centers, included, block_lufs, rel_threshold


# ═══════════════════════════════════════════════════════════════════
#  Module 2 — True-Peak Violation Timeline (ISP Detection)
# ═══════════════════════════════════════════════════════════════════

def compute_true_peak_violations(
    audio: np.ndarray,
    sample_rate: int,
    window_size: int = 4096,
    pre_filter_dbfs: float = -6.0,
) -> list[tuple[float, float]]:
    """Find time positions where the 4× oversampled true peak > 0 dBTP.

    Uses a two-pass approach for speed:
    1. Quick check — only windows whose sample peak is above
       *pre_filter_dbfs* are candidates (most windows are skipped).
    2. Full 4× upsample on candidates to find exact ISPs.

    Parameters
    ----------
    audio : np.ndarray
        Float32 stereo audio, shape ``(samples, channels)``.
    sample_rate : int
        Sample rate in Hz.
    window_size : int
        Analysis window length in samples (default 4096).
    pre_filter_dbfs : float
        Only windows with a sample peak above this (dBFS) are analysed
        for true peak.  Keeps computation fast.

    Returns
    -------
    list[tuple[float, float]]
        Sorted list of ``(time_seconds, peak_dBTP)`` for every window
        that exceeds 0.0 dBTP.
    """
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]

    threshold_linear = 10.0 ** (pre_filter_dbfs / 20.0)
    n_samples = audio.shape[0]
    violations: list[tuple[float, float]] = []

    for start in range(0, n_samples, window_size):
        end = min(start + window_size, n_samples)
        window = audio[start:end]

        # Fast reject: sample peak nowhere near 0 dBFS
        sample_peak = float(np.max(np.abs(window)))
        if sample_peak < threshold_linear:
            continue

        # Full 4× oversampling per channel
        max_tp = 0.0
        for ch in range(window.shape[1]):
            upsampled = resample_poly(
                window[:, ch].astype(np.float64), up=4, down=1,
            )
            max_tp = max(max_tp, float(np.max(np.abs(upsampled))))

        if max_tp > 1.0:  # > 0.0 dBTP
            centre_sec = (start + (end - start) / 2) / sample_rate
            peak_dbtp = 20.0 * np.log10(max_tp)
            violations.append((centre_sec, peak_dbtp))

    logger.debug("ISP violations found: %d", len(violations))
    return violations
