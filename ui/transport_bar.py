"""
Transport bar — playback controls, seek slider, and A/B toggle.

Layout::

    [ ▶ Play ] [ ⏹ Stop ]  ═══●══════  01:23 / 03:45
              [ A (Original) | B (Stream) ]      [ Export WAV ]
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from audio.player import AudioPlayer


class TransportBar(QWidget):
    """Playback transport with A/B switching and export button."""

    exportRequested = Signal()  # emitted when Export button is clicked

    def __init__(self, player: AudioPlayer, parent=None) -> None:
        super().__init__(parent)
        self._player = player

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(8)

        # ── Row 1: Transport controls + seek ────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        # Play / Pause
        self._play_btn = QPushButton("▶")
        self._play_btn.setProperty("cssClass", "transport-btn")
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.clicked.connect(self._toggle_play)
        row1.addWidget(self._play_btn)

        # Stop
        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setProperty("cssClass", "transport-btn")
        self._stop_btn.setToolTip("Stop")
        self._stop_btn.clicked.connect(self._stop)
        row1.addWidget(self._stop_btn)

        # Seek slider
        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 0)
        self._seek.setTracking(True)
        self._seek.sliderPressed.connect(self._seek_pressed)
        self._seek.sliderReleased.connect(self._seek_released)
        row1.addWidget(self._seek, stretch=1)

        # Time label
        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setProperty("cssClass", "time-label")
        self._time_label.setFixedWidth(110)
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self._time_label)

        root.addLayout(row1)

        # ── Row 2: Toggles & Export ─────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        # Normalize (Auto-Gain) toggle
        self._btn_normalize = QPushButton("Normalize: ON")
        self._btn_normalize.setProperty("cssClass", "toggle-active")
        self._btn_normalize.setFixedWidth(130)
        self._btn_normalize.setToolTip("Toggle loudness penalty (gain reduction)")
        self._btn_normalize.clicked.connect(self._toggle_normalize)
        row2.addWidget(self._btn_normalize)

        row2.addStretch()

        # A/B switches
        self._btn_a = QPushButton("A  (Original)")
        self._btn_a.setProperty("cssClass", "ab-active")
        self._btn_a.setFixedWidth(150)
        self._btn_a.clicked.connect(lambda: self._set_ab("A"))
        row2.addWidget(self._btn_a)

        self._btn_b = QPushButton("B  (Stream)")
        self._btn_b.setProperty("cssClass", "ab-inactive")
        self._btn_b.setFixedWidth(150)
        self._btn_b.clicked.connect(lambda: self._set_ab("B"))
        row2.addWidget(self._btn_b)

        row2.addStretch()

        # Delta Mode toggle
        self._btn_delta = QPushButton("Delta (Δ): OFF")
        self._btn_delta.setProperty("cssClass", "toggle-inactive")
        self._btn_delta.setFixedWidth(130)
        self._btn_delta.setToolTip("Listen to the difference (Original - Stream)")
        self._btn_delta.clicked.connect(self._toggle_delta)
        row2.addWidget(self._btn_delta)

        # Export
        self._export_btn = QPushButton("Export WAV")
        self._export_btn.setProperty("cssClass", "export-btn")
        self._export_btn.setFixedWidth(110)
        self._export_btn.clicked.connect(self.exportRequested.emit)
        row2.addWidget(self._export_btn)

        root.addLayout(row2)

        # ── Seek-bar update timer ───────────────────────────────────
        self._seeking = False
        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 fps
        self._timer.timeout.connect(self._update_position)
        self._timer.start()

    # ── Public ──────────────────────────────────────────────────────

    def set_duration(self, seconds: float) -> None:
        """Set the total duration (called when a file is loaded)."""
        self._seek.setRange(0, int(seconds * 1000))
        self._update_time_label(0.0, seconds)

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable or disable all transport controls."""
        self._play_btn.setEnabled(enabled)
        self._stop_btn.setEnabled(enabled)
        self._seek.setEnabled(enabled)
        self._btn_a.setEnabled(enabled)
        self._btn_b.setEnabled(enabled)
        self._btn_normalize.setEnabled(enabled)
        self._btn_delta.setEnabled(enabled)
        self._export_btn.setEnabled(enabled)

    # ── Internal ────────────────────────────────────────────────────

    normalizeToggled = Signal(bool)

    def _toggle_normalize(self) -> None:
        self._player.normalize_enabled = not self._player.normalize_enabled
        if self._player.normalize_enabled:
            self._btn_normalize.setText("Normalize: ON")
            self._btn_normalize.setProperty("cssClass", "toggle-active")
        else:
            self._btn_normalize.setText("Normalize: OFF")
            self._btn_normalize.setProperty("cssClass", "toggle-inactive")
        
        self._btn_normalize.style().unpolish(self._btn_normalize)
        self._btn_normalize.style().polish(self._btn_normalize)
        self.normalizeToggled.emit(self._player.normalize_enabled)

    def _toggle_delta(self) -> None:
        self._player.delta_enabled = not self._player.delta_enabled
        if self._player.delta_enabled:
            self._btn_delta.setText("Delta (Δ): ON")
            self._btn_delta.setProperty("cssClass", "toggle-active")
            # Disable A/B buttons since Delta overrides them
            self._btn_a.setEnabled(False)
            self._btn_b.setEnabled(False)
        else:
            self._btn_delta.setText("Delta (Δ): OFF")
            self._btn_delta.setProperty("cssClass", "toggle-inactive")
            # Re-enable A/B buttons
            self._btn_a.setEnabled(True)
            self._btn_b.setEnabled(True)
            
        self._btn_delta.style().unpolish(self._btn_delta)
        self._btn_delta.style().polish(self._btn_delta)

    def _toggle_play(self) -> None:
        if self._player.is_playing:
            self._player.pause()
            self._play_btn.setText("▶")
        else:
            self._player.play()
            self._play_btn.setText("⏸")

    def _stop(self) -> None:
        self._player.stop()
        self._play_btn.setText("▶")
        self._seek.setValue(0)

    def _set_ab(self, which: str) -> None:
        self._player.set_active(which)
        if which == "A":
            self._btn_a.setProperty("cssClass", "ab-active")
            self._btn_b.setProperty("cssClass", "ab-inactive")
        else:
            self._btn_a.setProperty("cssClass", "ab-inactive")
            self._btn_b.setProperty("cssClass", "ab-active")
        # Force style refresh
        for btn in (self._btn_a, self._btn_b):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _seek_pressed(self) -> None:
        self._seeking = True

    def _seek_released(self) -> None:
        self._seeking = False
        ms = self._seek.value()
        self._player.seek(ms / 1000.0)

    def _update_position(self) -> None:
        if self._seeking:
            return

        pos = self._player.get_position()
        dur = self._player.duration

        self._seek.blockSignals(True)
        self._seek.setValue(int(pos * 1000))
        self._seek.blockSignals(False)

        self._update_time_label(pos, dur)

        # Auto-reset play button when playback finishes
        if not self._player.is_playing and self._play_btn.text() == "⏸":
            self._play_btn.setText("▶")

    def _update_time_label(self, pos: float, dur: float) -> None:
        def fmt(s: float) -> str:
            m = int(s) // 60
            sec = int(s) % 60
            return f"{m:02d}:{sec:02d}"

        self._time_label.setText(f"{fmt(pos)} / {fmt(dur)}")
