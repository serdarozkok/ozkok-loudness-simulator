"""
Processing pipeline — orchestrates the full simulation chain on a
background ``QThread`` so the UI never freezes.

Pipeline steps
──────────────
1. Load audio file (WAV / FLAC → float32 stereo NumPy array)
2. Measure original Integrated LUFS and True Peak
3. Encode → Decode through the selected platform's lossy codec
4. Calculate the loudness penalty (dB)
5. Apply the penalty to the codec-decoded buffer  → **Buffer B** (stream sim)
6. Apply the same penalty to the original buffer   → **Buffer A** (gain-matched)
7. Measure post-codec LUFS and True Peak on Buffer B
8. Compute gate map (which blocks pass the relative gate) on original audio
9. Compute true-peak violation timeline on Buffer B
10. Emit all results via a Qt signal
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PySide6.QtCore import QThread, Signal

from audio.file_loader import load_audio
from core.analyzer import (
    compute_gate_map,
    compute_true_peak_violations,
    measure_loudness,
    measure_true_peak,
)
from core.codec_simulator import encode_decode
from core.gain_processor import apply_gain_db, calculate_penalty
from core.platforms import PlatformPreset

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Holds everything the UI needs after processing completes."""

    # Metrics
    original_lufs: float
    original_true_peak: float
    
    # Penalized Metrics (Normalize ON)
    simulated_lufs_norm: float
    simulated_true_peak_norm: float
    isp_violations_norm: list

    # Raw Metrics (Normalize OFF)
    simulated_lufs_raw: float
    simulated_true_peak_raw: float
    isp_violations_raw: list

    penalty_db: float

    # Audio buffers (float32, stereo) - Both are 0dB penalty!
    buffer_a: np.ndarray       
    buffer_b: np.ndarray       

    sample_rate: int
    filename: str
    platform_name: str
    elapsed_seconds: float

    # ── Visualisation data ──────────────────────────────────────────
    original_audio: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))

    # Gate map (Module 1)
    gate_block_centers: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))
    gate_block_included: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0, dtype=bool))
    gate_threshold_lufs: float = -70.0


class ProcessingPipeline(QThread):
    """Runs the complete simulation on a background thread.

    Signals
    -------
    progress(str)
        Status messages for the UI.
    finished(PipelineResult)
        Emitted with the full result when processing completes.
    error(str)
        Emitted if an unrecoverable error occurs.
    """

    progress = Signal(str)
    finished = Signal(object)      # PipelineResult
    error = Signal(str)

    def __init__(
        self,
        filepath: str,
        preset: PlatformPreset,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._filepath = filepath
        self._preset = preset

    # Optionally allow re-processing an already-loaded buffer
    _preloaded_audio: Optional[np.ndarray] = None
    _preloaded_sr: Optional[int] = None

    def set_preloaded(self, audio: np.ndarray, sr: int) -> None:
        """Skip the file-load step if audio is already in memory."""
        self._preloaded_audio = audio
        self._preloaded_sr = sr

    # ── Thread entry point ──────────────────────────────────────────

    def run(self) -> None:  # noqa: C901 — deliberate long method for clarity
        t0 = time.perf_counter()
        try:
            # ① Load audio
            if self._preloaded_audio is not None and self._preloaded_sr is not None:
                audio = self._preloaded_audio
                sr = self._preloaded_sr
                self.progress.emit("Audio loaded from cache")
            else:
                self.progress.emit("Loading audio file...")
                audio, sr = load_audio(self._filepath)

            # ② Measure original
            self.progress.emit("Measuring original loudness...")
            original_lufs = measure_loudness(audio, sr)
            original_tp = measure_true_peak(audio)
            
            # ③ Codec encode/decode (skip for "Unnormalized")
            preset = self._preset
            if preset.codec is not None:
                self.progress.emit(f"Encoding → {preset.codec} @ {preset.bitrate // 1000}k...")
                codec_audio = encode_decode(
                    audio, sr, preset.codec, preset.bitrate, preset.container
                )
            else:
                codec_audio = audio.copy()

            # 4️⃣ Gain penalty (Calculated, but NOT burned into the buffers)
            if preset.target_lufs is not None:
                penalty_db = calculate_penalty(
                    original_lufs, preset.target_lufs, preset.turns_up
                )
            else:
                penalty_db = 0.0
            
            self.progress.emit(f"Calculated {penalty_db:+.1f} dB penalty...")

            # 5️⃣/6️⃣ Set up buffers
            buffer_b = codec_audio
            buffer_a = audio
            
            # Create a temporary penalized buffer for Normalize: ON metrics
            buffer_b_norm = apply_gain_db(buffer_b, penalty_db)
            buffer_a_norm = apply_gain_db(buffer_a, penalty_db)

            # ── Measure NORMALIZED (Penalized) metrics ──
            self.progress.emit("Measuring simulated loudness (Normalized)...")
            sim_lufs_norm = measure_loudness(buffer_b_norm, sr)
            sim_tp_norm = measure_true_peak(buffer_b_norm)
            
            self.progress.emit("Scanning for ISP violations (Normalized)...")
            isp_violations_norm = compute_true_peak_violations(buffer_b_norm, sr)
            
            # ── Measure RAW (Unpenalized) metrics ──
            self.progress.emit("Measuring simulated loudness (Raw Codec)...")
            sim_lufs_raw = measure_loudness(buffer_b, sr)
            sim_tp_raw = measure_true_peak(buffer_b)
            
            self.progress.emit("Scanning for ISP violations (Raw Codec)...")
            isp_violations_raw = compute_true_peak_violations(buffer_b, sr)

            self.progress.emit("Computing gate map...")
            gate_centers, gate_included, _block_lufs, gate_thresh = (
                compute_gate_map(buffer_a_norm, sr)
            )

            elapsed = time.perf_counter() - t0

            result = PipelineResult(
                original_lufs=original_lufs,
                original_true_peak=original_tp,
                
                simulated_lufs_norm=sim_lufs_norm,
                simulated_true_peak_norm=sim_tp_norm,
                isp_violations_norm=isp_violations_norm,
                
                simulated_lufs_raw=sim_lufs_raw,
                simulated_true_peak_raw=sim_tp_raw,
                isp_violations_raw=isp_violations_raw,
                
                penalty_db=penalty_db,
                buffer_a=buffer_a,
                buffer_b=buffer_b,
                sample_rate=sr,
                filename=self._filepath.rsplit("\\", 1)[-1].rsplit("/", 1)[-1],
                platform_name=preset.display_name,
                elapsed_seconds=elapsed,
                original_audio=audio,
                gate_block_centers=gate_centers,
                gate_block_included=gate_included,
                gate_threshold_lufs=gate_thresh,
            )

            self.progress.emit(f"Done in {elapsed:.1f}s")
            self.finished.emit(result)

        except Exception as exc:
            logger.exception("Pipeline error")
            self.error.emit(str(exc))
