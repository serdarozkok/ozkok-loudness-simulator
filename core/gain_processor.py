"""
Loudness penalty calculation and linear gain application.

Streaming platforms apply a simple digital gain offset (no limiter)
to match their loudness target.  The gain is computed as the delta
between the measured integrated LUFS and the platform target.

Most platforms only turn *down* tracks louder than the target.
Apple Music also turns *up* quieter tracks.
"""

from __future__ import annotations

import numpy as np


def calculate_penalty(
    original_lufs: float,
    target_lufs: float,
    turns_up: bool = False,
) -> float:
    """Return the gain adjustment in dB that the platform would apply.

    Parameters
    ----------
    original_lufs : float
        Integrated loudness of the original master (LUFS).
    target_lufs : float
        Platform's loudness target (LUFS).
    turns_up : bool
        If ``True``, the platform boosts quiet tracks (Apple Music).
        If ``False``, only negative gain is applied (Spotify, YouTube, Tidal).

    Returns
    -------
    float
        Gain delta in dB (negative = turn down, positive = turn up,
        ``0.0`` if the track is at or below the target on a
        turn-down-only platform).
    """
    if original_lufs == float("-inf"):
        return 0.0

    delta = target_lufs - original_lufs  # negative when master is hotter

    if not turns_up and delta > 0.0:
        # Platform does not boost quiet tracks → no gain change
        return 0.0

    return delta


def apply_gain_db(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """Apply a linear gain (in dB) to an audio buffer.

    No clipping is performed — the output may exceed ±1.0.  This is
    intentional: we want to preserve intersample peaks for measurement.

    Parameters
    ----------
    audio : np.ndarray
        Audio data, any shape, float32.
    gain_db : float
        Gain to apply in decibels.

    Returns
    -------
    np.ndarray
        Gained audio (same shape, float32).
    """
    if gain_db == 0.0:
        return audio.copy()

    linear_gain = 10.0 ** (gain_db / 20.0)
    return (audio * linear_gain).astype(np.float32)
