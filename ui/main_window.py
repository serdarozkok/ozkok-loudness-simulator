"""
Main application window — assembles all UI components and orchestrates
the signal flow between the drop zone, processing pipeline, metrics
panel, platform selector, waveform visualiser, and audio transport.

Signal wiring
─────────────
DropZone.fileDropped → _on_file_dropped → launch ProcessingPipeline
PlatformSelector.platformChanged → _on_platform_changed → re-launch pipeline
ProcessingPipeline.finished → _on_pipeline_finished → update metrics + visualiser + load player
TransportBar.exportRequested → _export_simulated_wav
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
import soundfile as sf
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from audio.player import AudioPlayer
from core.pipeline import PipelineResult, ProcessingPipeline
from core.platforms import PlatformPreset
from ui.drop_zone import DropZone
from ui.metrics_panel import MetricsPanel
from ui.platform_grid import PlatformGrid
from ui.transport_bar import TransportBar
from ui.visualizer import WaveformVisualizer

logger = logging.getLogger(__name__)

from PySide6.QtCore import QThread, Signal

class LufsScanner(QThread):
    """Fast background thread to measure Master LUFS and populate the Grid."""
    finished = Signal(float, object, int) # lufs, audio_array, sample_rate
    error = Signal(str)

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath

    def run(self):
        try:
            from audio.file_loader import load_audio
            from core.analyzer import measure_loudness
            audio, sr = load_audio(self.filepath)
            lufs = measure_loudness(audio, sr)
            self.finished.emit(lufs, audio, sr)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Top-level window for the OZKOK Loudness & Codec Simulator."""

    MIN_WIDTH = 700
    MIN_HEIGHT = 700

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OZKOK Loudness & Codec Simulator")
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resize(780, 760)

        # ── State ───────────────────────────────────────────────────
        self._player = AudioPlayer()
        self._current_filepath: Optional[str] = None
        self._cached_audio: Optional[np.ndarray] = None
        self._cached_sr: Optional[int] = None
        self._pipeline: Optional[ProcessingPipeline] = None
        self._last_result: Optional[PipelineResult] = None

        # ── Build UI ────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        # Title
        title = QLabel("OZKOK LOUDNESS & CODEC SIMULATOR")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("cssClass", "heading")
        root.addWidget(title)

        subtitle = QLabel(
            "Hear how streaming platforms degrade your master"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("cssClass", "subheading")
        root.addWidget(subtitle)

        # Drop zone
        self._drop_zone = DropZone()
        root.addWidget(self._drop_zone)

        # Status label
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setProperty("cssClass", "status-processing")
        root.addWidget(self._status)

        # ── 2. Platform Grid (V2 Dashboard) ─────────────────────────
        self._grid = PlatformGrid()
        root.addWidget(self._grid)

        # ── 3. Metrics Panel ────────────────────────────────────────
        self._metrics = MetricsPanel()
        root.addWidget(self._metrics)

        # ── 4. Waveform & Visualiser ────────────────────────────────
        self._visualizer = WaveformVisualizer()
        root.addWidget(self._visualizer)

        # ── 5. Status Bar ───────────────────────────────────────────
        self._status = QLabel("Ready. Drop an audio file to begin.")
        self._status.setProperty("cssClass", "status-ready")
        self._status.setAlignment(Qt.AlignCenter)
        root.addWidget(self._status)

        # ── Separator ───────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setProperty("cssClass", "separator")
        root.addWidget(sep)

        # ── 6. Transport Bar ────────────────────────────────────────
        self._transport = TransportBar(self._player)
        self._transport.set_enabled_state(False)
        root.addWidget(self._transport)

        # ── Playhead sync timer ─────────────────────────────────────
        self._playhead_timer = QTimer(self)
        self._playhead_timer.setInterval(66)  # ~15 fps (reduced to prevent audio glitching)
        self._playhead_timer.timeout.connect(self._sync_playhead)
        self._playhead_timer.start()

        # ── Wire signals ────────────────────────────────────────────
        self._drop_zone.fileDropped.connect(self._on_file_dropped)
        self._grid.platformChanged.connect(self._on_platform_changed)
        self._transport.exportRequested.connect(self._export_simulated_wav)
        self._transport.normalizeToggled.connect(self._on_normalize_toggled)

    def _on_normalize_toggled(self, enabled: bool) -> None:
        if self._last_result is None:
            return
            
        res = self._last_result
        if enabled:
            self._metrics.update_simulated(res.simulated_lufs_norm, res.simulated_true_peak_norm)
            self._visualizer.update_isp_lines(res.isp_violations_norm)
        else:
            self._metrics.update_simulated(res.simulated_lufs_raw, res.simulated_true_peak_raw)
            self._visualizer.update_isp_lines(res.isp_violations_raw)

    # ── Playhead sync ───────────────────────────────────────────────

    def _sync_playhead(self) -> None:
        """Sync the visualiser playhead with the audio player position."""
        if self._last_result is not None and self._player.is_playing:
            pos = self._player.get_position()
            self._visualizer.set_playhead(pos)

    # ── File drop handler ───────────────────────────────────────────

    def _on_file_dropped(self, filepath: str) -> None:
        """Called when the user drops a file or browses."""
        logger.info("File dropped: %s", filepath)
        self._current_filepath = filepath
        self._cached_audio = None      # Force reload
        self._cached_sr = None
        self._player.stop()
        self._metrics.reset()
        self._visualizer.reset()
        self._transport.set_enabled_state(False)
        self._grid.reset_penalties()
        
        # Kill existing scanner/pipeline
        if getattr(self, '_lufs_scanner', None) is not None and self._lufs_scanner.isRunning():
            self._lufs_scanner.terminate()
            self._lufs_scanner.wait()
        if self._pipeline is not None and self._pipeline.isRunning():
            self._pipeline.terminate()
            self._pipeline.wait()
            
        self._status.setText("Scanning Master LUFS...")
        self._status.setProperty("cssClass", "status-processing")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        
        self._lufs_scanner = LufsScanner(filepath)
        self._lufs_scanner.finished.connect(self._on_lufs_scanned)
        self._lufs_scanner.error.connect(self._on_pipeline_error)
        self._lufs_scanner.start()

    def _on_lufs_scanned(self, master_lufs: float, audio: object, sr: int) -> None:
        """Called when initial fast LUFS scan is complete."""
        self._cached_audio = audio
        self._cached_sr = sr
        self._grid.update_penalties(master_lufs)
        self._run_pipeline()

    # ── Platform change handler ─────────────────────────────────────

    def _on_platform_changed(self, preset: PlatformPreset) -> None:
        """Re-process with the new platform preset."""
        if self._current_filepath is None:
            return
        logger.info("Platform changed: %s", preset.name)
        self._player.stop()
        self._run_pipeline()

    # ── Pipeline execution ──────────────────────────────────────────

    def _run_pipeline(self) -> None:
        """Launch the processing pipeline on a background thread."""
        if self._current_filepath is None:
            return

        # Kill any existing pipeline
        if self._pipeline is not None and self._pipeline.isRunning():
            self._pipeline.terminate()
            self._pipeline.wait()

        preset = self._grid.current_preset()
        self._status.setText(f"Processing Codec ({preset.name})...")
        self._status.setProperty("cssClass", "status-processing")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

        self._pipeline = ProcessingPipeline(self._current_filepath, preset)

        # If audio is already cached (platform change, not new file), skip reload
        if self._cached_audio is not None and self._cached_sr is not None:
            self._pipeline.set_preloaded(self._cached_audio, self._cached_sr)

        self._pipeline.progress.connect(self._on_progress)
        self._pipeline.finished.connect(self._on_pipeline_finished)
        self._pipeline.error.connect(self._on_pipeline_error)
        self._pipeline.start()

    def _on_progress(self, msg: str) -> None:
        self._status.setText(msg)

    def _on_pipeline_finished(self, result: PipelineResult) -> None:
        """Pipeline completed — update UI, visualiser, and load player."""
        self._last_result = result

        # Cache the raw audio for platform re-processing
        if self._cached_audio is None:
            from audio.file_loader import load_audio
            try:
                self._cached_audio, self._cached_sr = load_audio(
                    self._current_filepath
                )
            except Exception:
                pass  # Will reload next time

        # Determine which metrics to display based on current Normalize state
        is_norm = self._player.normalize_enabled
        sim_lufs = result.simulated_lufs_norm if is_norm else result.simulated_lufs_raw
        sim_tp = result.simulated_true_peak_norm if is_norm else result.simulated_true_peak_raw
        isp_v = result.isp_violations_norm if is_norm else result.isp_violations_raw

        # Update metrics
        self._metrics.update_metrics(
            original_lufs=result.original_lufs,
            original_tp=result.original_true_peak,
            simulated_lufs=sim_lufs,
            simulated_tp=sim_tp,
            penalty_db=result.penalty_db,
        )

        # Update waveform visualiser
        self._visualizer.update_data(
            audio=result.original_audio,
            sample_rate=result.sample_rate,
            gate_centers=result.gate_block_centers,
            gate_included=result.gate_block_included,
            isp_violations=isp_v,
        )

        # Load player
        self._player.load(result.buffer_a, result.buffer_b, result.sample_rate, result.penalty_db)
        self._transport.set_duration(self._player.duration)
        self._transport.set_enabled_state(True)

        # Status with ISP count
        isp_count = len(isp_v)
        isp_note = f" — {isp_count} ISP violation{'s' if isp_count != 1 else ''}" if isp_count else ""
        self._status.setText(
            f"✓ {result.filename} — {result.platform_name} — "
            f"processed in {result.elapsed_seconds:.1f}s{isp_note}"
        )

    def _on_pipeline_error(self, msg: str) -> None:
        self._status.setText(f"Error: {msg}")
        self._status.setProperty("cssClass", "status-error")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        logger.error("Pipeline error: %s", msg)

    # ── Export ──────────────────────────────────────────────────────

    def _export_simulated_wav(self) -> None:
        """Export the simulated (Buffer B) audio as a 32-bit float WAV."""
        if self._last_result is None:
            QMessageBox.information(self, "Export", "No processed audio to export.")
            return

        result = self._last_result
        default_name = os.path.splitext(result.filename)[0]
        safe_platform = result.platform_name.split("(")[0].strip().replace(" ", "_")
        suggested = f"{default_name}_simulated_{safe_platform}.wav"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Simulated WAV",
            suggested,
            "WAV Files (*.wav)",
        )
        if not path:
            return

        try:
            sf.write(path, result.buffer_b, result.sample_rate, subtype="FLOAT")
            self._status.setText(f"Exported → {os.path.basename(path)}")
            logger.info("Exported to %s", path)
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    # ── Window close ────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._player.stop()
        self._playhead_timer.stop()
        if self._pipeline is not None and self._pipeline.isRunning():
            self._pipeline.terminate()
            self._pipeline.wait()
        event.accept()
