"""
Callback-based audio player using ``sounddevice``.

Provides gapless, click-free A/B switching between two time-aligned
buffers (Buffer A = gain-matched original, Buffer B = stream-simulated).

A/B mechanism
─────────────
Both buffers share a single playhead.  When the user toggles A↔B a flag
is set; the audio callback performs a 512-sample (~11 ms at 44.1 kHz)
equal-power crossfade from the outgoing buffer to the incoming buffer.
Because the buffers are gain-matched and phase-aligned, the transition
is inaudible — the user hears *only* codec artefacts, not a volume jump.
"""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioPlayer:
    """Low-latency PortAudio player with real-time A/B switching."""

    CROSSFADE_SAMPLES = 512  # ~11 ms @ 44.1 kHz

    def __init__(self) -> None:
        self._lock = threading.Lock()

        self.buffer_a: Optional[np.ndarray] = None   # (samples, 2) float32
        self.buffer_b: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self._total_frames: int = 0
        self.penalty_gain: float = 1.0   # Linear gain multiplier for Normalize mode

        self._position: int = 0          # current playhead (sample index)
        self._playing: bool = False
        self._active: str = "A"           # 'A' or 'B'

        # New V2 Toggles
        self.normalize_enabled: bool = True
        self.delta_enabled: bool = False

        # Crossfade state
        self._crossfade_remaining: int = 0
        self._fading_from: Optional[str] = None

        self._stream: Optional[sd.OutputStream] = None

    # ── Public API ──────────────────────────────────────────────────

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def active_buffer(self) -> str:
        return self._active

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        return self._total_frames / self.sample_rate if self._total_frames else 0.0

    def load(
        self,
        buffer_a: np.ndarray,
        buffer_b: np.ndarray,
        sample_rate: int,
        penalty_db: float,
    ) -> None:
        """Load two phase-aligned stereo buffers for A/B comparison."""
        self.stop()

        with self._lock:
            # Ensure 2-D stereo
            if buffer_a.ndim == 1:
                buffer_a = np.column_stack((buffer_a, buffer_a))
            if buffer_b.ndim == 1:
                buffer_b = np.column_stack((buffer_b, buffer_b))

            # Pad to equal length (should already be equal after pipeline)
            max_len = max(len(buffer_a), len(buffer_b))
            if len(buffer_a) < max_len:
                buffer_a = np.pad(buffer_a, ((0, max_len - len(buffer_a)), (0, 0)))
            if len(buffer_b) < max_len:
                buffer_b = np.pad(buffer_b, ((0, max_len - len(buffer_b)), (0, 0)))

            self.buffer_a = buffer_a.astype(np.float32)
            self.buffer_b = buffer_b.astype(np.float32)
            self.sample_rate = sample_rate
            self.penalty_gain = 10.0 ** (penalty_db / 20.0)
            self._total_frames = max_len
            self._position = 0
            self._active = "A"
            self._crossfade_remaining = 0
            self._fading_from = None

    def play(self) -> None:
        """Start or resume playback."""
        if self.buffer_a is None:
            return

        if self._stream is None:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                dtype="float32",
                callback=self._callback,
                blocksize=1024,
                latency="low",
            )
            self._stream.start()

        self._playing = True

    def pause(self) -> None:
        """Pause without resetting position."""
        self._playing = False

    def stop(self) -> None:
        """Stop playback and reset position to zero."""
        self._playing = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        with self._lock:
            self._position = 0

    def seek(self, seconds: float) -> None:
        """Seek to a position (in seconds) in both buffers."""
        with self._lock:
            target = int(seconds * self.sample_rate)
            self._position = max(0, min(target, self._total_frames))

    def get_position(self) -> float:
        """Current playback position in seconds."""
        with self._lock:
            return self._position / self.sample_rate

    def toggle_ab(self) -> None:
        """Toggle between A and B with an equal-power crossfade."""
        with self._lock:
            new = "B" if self._active == "A" else "A"
            self._fading_from = self._active
            self._active = new
            self._crossfade_remaining = self.CROSSFADE_SAMPLES

    def set_active(self, which: str) -> None:
        """Switch to a specific buffer ('A' or 'B')."""
        if which not in ("A", "B"):
            return
        with self._lock:
            if which != self._active:
                self._fading_from = self._active
                self._active = which
                self._crossfade_remaining = self.CROSSFADE_SAMPLES

    # ── Audio callback (runs on PortAudio thread) ───────────────────

    def _callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info,           # noqa: ANN001 (c-level struct)
        status: sd.CallbackFlags,
    ) -> None:
        with self._lock:
            if (
                not self._playing
                or self.buffer_a is None
                or self.buffer_b is None
            ):
                outdata.fill(0)
                return

            start = self._position
            total = self._total_frames

            if start >= total:
                outdata.fill(0)
                self._playing = False
                return

            chunk_len = min(frames, total - start)

            # Select primary buffer (or Delta difference)
            if self.delta_enabled:
                # Delta mode: Original - Codec (absolute difference)
                primary = self.buffer_a[start : start + chunk_len] - self.buffer_b[start : start + chunk_len]
            else:
                primary = (
                    self.buffer_a if self._active == "A" else self.buffer_b
                )
                primary = primary[start : start + chunk_len]
                
            out = primary.copy()

            # ── Crossfade logic (Only applicable if Delta is OFF) ───
            if not self.delta_enabled and self._crossfade_remaining > 0 and self._fading_from is not None:
                secondary = (
                    self.buffer_a
                    if self._fading_from == "A"
                    else self.buffer_b
                )
                fade_len = min(chunk_len, self._crossfade_remaining)

                # Equal-power weights
                progress_start = 1.0 - (
                    self._crossfade_remaining / self.CROSSFADE_SAMPLES
                )
                progress_end = 1.0 - (
                    (self._crossfade_remaining - fade_len)
                    / self.CROSSFADE_SAMPLES
                )
                alpha = np.linspace(
                    progress_start, progress_end, fade_len, dtype=np.float32
                )[:, np.newaxis]

                w_new = np.sin(alpha * (np.pi / 2.0))
                w_old = np.cos(alpha * (np.pi / 2.0))

                out[:fade_len] = (
                    w_new * out[:fade_len]
                    + w_old * secondary[start : start + fade_len]
                )

                self._crossfade_remaining -= fade_len
                if self._crossfade_remaining <= 0:
                    self._fading_from = None

            # ── Auto-Gain (Normalize) Bypass Logic ──────────────────
            if self.normalize_enabled:
                out *= self.penalty_gain

            # Write to output
            outdata[:chunk_len] = out
            if chunk_len < frames:
                outdata[chunk_len:] = 0

            self._position += chunk_len
