"""
Waveform Visualiser — pyqtgraph-based widget that displays:

1. **Gate Map waveform**: Original audio envelope coloured by BS.1770-4
   relative-gate status.  Regions included in the LUFS measurement
   are drawn in Teal (#0D9488); gated-out (quiet) regions in dark
   grey (#4A5568).

2. **ISP Markers**: Bright red (#FF4C4C) vertical lines at every
   timestamp where the codec-decoded buffer's true peak exceeds
   0.0 dBTP, acting as a forensic distortion timeline.

3. **Playhead**: A peach vertical line tracking the current playback
   position, synchronised with the transport seek bar.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.styles import COLORS


class TimeAxisItem(pg.AxisItem):
    """Custom X-axis that formats seconds → mm:ss."""

    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            v = max(0, v)
            m = int(v) // 60
            s = int(v) % 60
            strings.append(f"{m:02d}:{s:02d}")
        return strings


class WaveformVisualizer(QWidget):
    """Compound widget containing the gate-map waveform + ISP markers."""

    # Display resolution — number of points in the decimated envelope.
    DISPLAY_POINTS = 2000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(170)
        self.setMaximumHeight(210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── pyqtgraph PlotWidget ────────────────────────────────────
        time_axis = TimeAxisItem(orientation="bottom")
        self._plot = pg.PlotWidget(axisItems={"bottom": time_axis})
        self._plot.setBackground(COLORS["bg_primary"])
        self._plot.setLabel("bottom", "")
        self._plot.hideAxis("left")          # amplitude axis not needed
        self._plot.setYRange(-1.05, 1.05, padding=0)
        self._plot.setMouseEnabled(x=True, y=False)   # pan X only
        self._plot.showGrid(x=False, y=False)
        self._plot.setMenuEnabled(False)

        # Remove default padding / auto-range on Y
        self._plot.getViewBox().setDefaultPadding(0)

        layout.addWidget(self._plot)

        # ── Persistent plot items ───────────────────────────────────
        # Grey (gated-out) waveform — always rendered as background
        self._curve_upper_grey = pg.PlotCurveItem(pen=None)
        self._curve_lower_grey = pg.PlotCurveItem(pen=None)
        self._fill_grey = pg.FillBetweenItem(
            self._curve_upper_grey,
            self._curve_lower_grey,
            brush=pg.mkBrush(COLORS["gate_excluded"]),
        )
        self._plot.addItem(self._fill_grey)

        # Teal (included) waveform — overlay on top
        self._curve_upper_teal = pg.PlotCurveItem(pen=None)
        self._curve_lower_teal = pg.PlotCurveItem(pen=None)
        self._fill_teal = pg.FillBetweenItem(
            self._curve_upper_teal,
            self._curve_lower_teal,
            brush=pg.mkBrush(COLORS["gate_included"]),
        )
        self._plot.addItem(self._fill_teal)

        # ISP marker lines (created dynamically)
        self._isp_lines: list[pg.InfiniteLine] = []

        # Playhead
        self._playhead = pg.InfiniteLine(
            pos=0, angle=90,
            pen=pg.mkPen(COLORS["peach"], width=2, style=Qt.PenStyle.SolidLine),
            movable=False,
        )
        self._plot.addItem(self._playhead)
        self._playhead.hide()

        self._duration = 0.0

    # ── Public API ──────────────────────────────────────────────────

    def update_data(
        self,
        audio: np.ndarray,
        sample_rate: int,
        gate_centers: np.ndarray,
        gate_included: np.ndarray,
        isp_violations: list[tuple[float, float]],
    ) -> None:
        """Re-draw the waveform with new analysis data.

        Parameters
        ----------
        audio : np.ndarray
            Original stereo audio (samples, channels).
        sample_rate : int
            Sample rate in Hz.
        gate_centers : np.ndarray
            Centre times (seconds) for each 400 ms gating block.
        gate_included : np.ndarray[bool]
            True if the block passes the relative gate.
        isp_violations : list
            List of ``(time_sec, peak_dBTP)`` from ISP detection.
        """
        if audio.ndim == 1:
            audio = audio[:, np.newaxis]

        n_samples = audio.shape[0]
        self._duration = n_samples / sample_rate

        # ── 1. Compute decimated envelope ──────────────────────────
        display_pts = min(self.DISPLAY_POINTS, n_samples)
        times, env_upper, env_lower = self._compute_envelope(
            audio, sample_rate, display_pts,
        )

        # ── 2. Map gate status onto display points ─────────────────
        included_mask = self._map_gate_to_display(
            times, gate_centers, gate_included,
        )

        # ── 3. Update grey (all) and teal (included) waveforms ────
        self._curve_upper_grey.setData(times, env_upper)
        self._curve_lower_grey.setData(times, env_lower)

        # Teal overlay: zero-out excluded regions so grey shows through
        upper_teal = np.where(included_mask, env_upper, 0.0)
        lower_teal = np.where(included_mask, env_lower, 0.0)
        self._curve_upper_teal.setData(times, upper_teal)
        self._curve_lower_teal.setData(times, lower_teal)

        # ── 4. ISP markers ──────────────────────────────────────────
        self.update_isp_lines(isp_violations)

        # ── 5. Set X range to full duration ─────────────────────────
        self._plot.setXRange(0, self._duration, padding=0.01)
        self._playhead.show()
        self._playhead.setValue(0)

    def update_isp_lines(self, isp_violations: list) -> None:
        """Update just the red True Peak violation markers dynamically."""
        import pyqtgraph as pg
        from ui.styles import COLORS
        from PySide6.QtCore import Qt

        for line in self._isp_lines:
            self._plot.removeItem(line)
        self._isp_lines.clear()

        isp_pen = pg.mkPen(COLORS["isp_red"], width=1.5)
        for violation in isp_violations:
            # Handle both formats (t_sec, peak) or just t_sec if structure changes
            t_sec = violation[0] if isinstance(violation, (tuple, list)) else violation
            line = pg.InfiniteLine(
                pos=t_sec, angle=90, pen=isp_pen, movable=False,
            )
            self._plot.addItem(line)
            self._isp_lines.append(line)

    def set_playhead(self, seconds: float) -> None:
        """Move the playhead to the given time position."""
        self._playhead.setValue(seconds)

    def reset(self) -> None:
        """Clear the visualiser."""
        empty = np.array([0, 1], dtype=np.float64)
        zeros = np.array([0, 0], dtype=np.float64)
        self._curve_upper_grey.setData(empty, zeros)
        self._curve_lower_grey.setData(empty, zeros)
        self._curve_upper_teal.setData(empty, zeros)
        self._curve_lower_teal.setData(empty, zeros)
        for line in self._isp_lines:
            self._plot.removeItem(line)
        self._isp_lines.clear()
        self._playhead.hide()

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _compute_envelope(
        audio: np.ndarray, sample_rate: int, display_pts: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Downsample audio to an upper/lower envelope for display."""
        # Mix to mono for the envelope
        mono = np.mean(audio, axis=1) if audio.ndim > 1 else audio

        n = len(mono)
        chunk = max(1, n // display_pts)
        # Trim to an even multiple of chunk size
        trimmed = mono[: chunk * display_pts] if chunk * display_pts <= n else mono
        actual_pts = len(trimmed) // chunk

        reshaped = trimmed[: actual_pts * chunk].reshape(actual_pts, chunk)
        env_upper = np.max(reshaped, axis=1)
        env_lower = np.min(reshaped, axis=1)

        times = (np.arange(actual_pts) * chunk + chunk / 2) / sample_rate
        return times, env_upper.astype(np.float64), env_lower.astype(np.float64)

    @staticmethod
    def _map_gate_to_display(
        display_times: np.ndarray,
        gate_centers: np.ndarray,
        gate_included: np.ndarray,
    ) -> np.ndarray:
        """Map per-block gate status onto the display time axis."""
        if gate_centers.size == 0:
            return np.ones(len(display_times), dtype=bool)

        # For each display point, find the nearest gate block
        indices = np.searchsorted(gate_centers, display_times, side="right") - 1
        indices = np.clip(indices, 0, len(gate_included) - 1)
        return gate_included[indices]
