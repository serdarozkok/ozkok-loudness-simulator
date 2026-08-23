"""
Audio file I/O using ``soundfile`` (libsndfile).

Reads WAV and FLAC files into float32 NumPy arrays normalised to
``[-1, 1]`` and ensures stereo output (mono files are duplicated
to two channels).
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np
import soundfile as sf


SUPPORTED_EXTENSIONS = {".wav", ".flac"}


def is_supported(filepath: str) -> bool:
    """Return ``True`` if the file extension is WAV or FLAC."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in SUPPORTED_EXTENSIONS


def load_audio(filepath: str) -> Tuple[np.ndarray, int]:
    """Load an audio file and return ``(data, sample_rate)``.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to a WAV or FLAC file.

    Returns
    -------
    data : np.ndarray
        Float32 audio, shape ``(samples, 2)`` (always stereo).
    sample_rate : int
        Sample rate in Hz.

    Raises
    ------
    ValueError
        If the file extension is not supported.
    FileNotFoundError
        If the file does not exist.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    if not is_supported(filepath):
        _, ext = os.path.splitext(filepath)
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # always_2d guarantees (samples, channels) even for mono
    data, sample_rate = sf.read(filepath, dtype="float32", always_2d=True)

    # Ensure stereo
    if data.shape[1] == 1:
        data = np.column_stack((data, data))
    elif data.shape[1] > 2:
        # Down-mix to stereo: take first two channels
        data = data[:, :2]

    return data, int(sample_rate)


def get_file_info(filepath: str) -> dict:
    """Return metadata about an audio file without reading the samples.

    Returns
    -------
    dict
        Keys: ``sample_rate``, ``channels``, ``frames``, ``duration``,
        ``format_name``, ``subtype``.
    """
    info = sf.info(filepath)
    return {
        "sample_rate": info.samplerate,
        "channels": info.channels,
        "frames": info.frames,
        "duration": info.duration,
        "format_name": info.format,
        "subtype": info.subtype,
    }
