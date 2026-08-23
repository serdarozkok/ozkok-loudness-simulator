"""
Metrics display panel.

Two-column layout showing:
  • **Original Master** — LUFS and True Peak before processing
  • **Simulated Stream** — LUFS and True Peak after codec + gain

The True Peak value turns **red** when it exceeds 0.0 dBTP,
warning the user of digital clipping.
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


class MetricsPanel(QFrame):
    """Side-by-side metrics for original vs. simulated audio."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cssClass", "metrics-panel")

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)

        # ── Left column: Original ───────────────────────────────────
        left = QFrame()
        left.setProperty("cssClass", "metrics-column")
        ll = QVBoxLayout(left)
        ll.setSpacing(6)

        left_title = QLabel("ORIGINAL MASTER")
        left_title.setProperty("cssClass", "metric-label")
        left_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(left_title)

        self._orig_lufs = QLabel("— LUFS")
        self._orig_lufs.setProperty("cssClass", "metric-value")
        self._orig_lufs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self._orig_lufs)

        self._orig_tp = QLabel("— dBTP")
        self._orig_tp.setProperty("cssClass", "metric-value")
        self._orig_tp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self._orig_tp)

        self._penalty_label = QLabel("Penalty: — dB")
        self._penalty_label.setProperty("cssClass", "metric-label")
        self._penalty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self._penalty_label)

        root.addWidget(left, stretch=1)

        # ── Separator ───────────────────────────────────────────────
        sep = QFrame()
        sep.setProperty("cssClass", "separator")
        sep.setFixedWidth(1)
        root.addWidget(sep)

        # ── Right column: Simulated ─────────────────────────────────
        right = QFrame()
        right.setProperty("cssClass", "metrics-column")
        rl = QVBoxLayout(right)
        rl.setSpacing(6)

        right_title = QLabel("SIMULATED STREAM")
        right_title.setProperty("cssClass", "metric-label")
        right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(right_title)

        self._sim_lufs = QLabel("— LUFS")
        self._sim_lufs.setProperty("cssClass", "metric-value")
        self._sim_lufs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self._sim_lufs)

        self._sim_tp = QLabel("— dBTP")
        self._sim_tp.setProperty("cssClass", "metric-value")
        self._sim_tp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self._sim_tp)

        self._clipping_label = QLabel("")
        self._clipping_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._clipping_label.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #FFB6A1; background: transparent;"
        )
        self._clipping_label.hide()
        rl.addWidget(self._clipping_label)

        root.addWidget(right, stretch=1)

    # ── Public update method ────────────────────────────────────────

    def update_metrics(
        self,
        original_lufs: float,
        original_tp: float,
        simulated_lufs: float,
        simulated_tp: float,
        penalty_db: float,
    ) -> None:
        """Refresh all displayed values."""
        # Format helpers
        def fmt_lufs(v: float) -> str:
            if math.isinf(v):
                return "−∞ LUFS"
            return f"{v:+.1f} LUFS"

        def fmt_tp(v: float) -> str:
            if math.isinf(v):
                return "−∞ dBTP"
            return f"{v:+.1f} dBTP"

        # Original
        self._orig_lufs.setText(fmt_lufs(original_lufs))
        self._orig_tp.setText(fmt_tp(original_tp))
        self._penalty_label.setText(f"Penalty: {penalty_db:+.2f} dB")

        # Simulated
        self._sim_lufs.setText(fmt_lufs(simulated_lufs))
        self._sim_tp.setText(fmt_tp(simulated_tp))

        # Clipping warning: True Peak > 0.0 dBTP → RED
        is_clipping = not math.isinf(simulated_tp) and simulated_tp > 0.0

        if is_clipping:
            self._sim_tp.setProperty("cssClass", "metric-clipping")
            self._clipping_label.setText("⚠ CLIPPING DETECTED")
            self._clipping_label.show()
        else:
            self._sim_tp.setProperty("cssClass", "metric-value")
            self._clipping_label.hide()

        # Force style refresh for dynamic property changes
        self._sim_tp.style().unpolish(self._sim_tp)
        self._sim_tp.style().polish(self._sim_tp)

    def update_simulated(self, simulated_lufs: float, simulated_tp: float) -> None:
        """Update just the simulated side dynamically."""
        import math
        def fmt_lufs(v: float) -> str:
            if math.isinf(v):
                return "-∞ LUFS"
            return f"{v:+.1f} LUFS"

        def fmt_tp(v: float) -> str:
            if math.isinf(v):
                return "-∞ dBTP"
            return f"{v:+.1f} dBTP"

        self._sim_lufs.setText(fmt_lufs(simulated_lufs))
        self._sim_tp.setText(fmt_tp(simulated_tp))

        is_clipping = not math.isinf(simulated_tp) and simulated_tp > 0.0
        if is_clipping:
            self._sim_tp.setProperty("cssClass", "metric-clipping")
            self._clipping_label.setText("⚠ CLIPPING DETECTED")
            self._clipping_label.show()
        else:
            self._sim_tp.setProperty("cssClass", "metric-value")
            self._clipping_label.hide()

        self._sim_tp.style().unpolish(self._sim_tp)
        self._sim_tp.style().polish(self._sim_tp)

    def reset(self) -> None:
        """Reset to placeholder dashes."""
        self._orig_lufs.setText("— LUFS")
        self._orig_tp.setText("— dBTP")
        self._penalty_label.setText("Penalty: — dB")
        self._sim_lufs.setText("— LUFS")
        self._sim_tp.setText("— dBTP")
        self._sim_tp.setProperty("cssClass", "metric-value")
        self._sim_tp.style().unpolish(self._sim_tp)
        self._sim_tp.style().polish(self._sim_tp)
        self._clipping_label.hide()
