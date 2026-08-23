"""
Platform selector dropdown.

Presents a ``QComboBox`` listing every streaming platform preset in
display order.  Emits ``platformChanged(PlatformPreset)`` when the
user selects a different platform.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from core.platforms import PLATFORM_ORDER, PLATFORM_PRESETS, PlatformPreset


class PlatformSelector(QWidget):
    """Dropdown for choosing a streaming platform simulation."""

    platformChanged = Signal(object)  # PlatformPreset

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel("Platform:")
        label.setProperty("cssClass", "metric-label")
        layout.addWidget(label)

        self._combo = QComboBox()
        for key in PLATFORM_ORDER:
            preset = PLATFORM_PRESETS[key]
            self._combo.addItem(preset.display_name, userData=key)
        layout.addWidget(self._combo, stretch=1)

        self._combo.currentIndexChanged.connect(self._on_index_changed)

    # ── Public API ──────────────────────────────────────────────────

    def current_preset(self) -> PlatformPreset:
        """Return the currently selected preset."""
        key = self._combo.currentData()
        return PLATFORM_PRESETS[key]

    def set_preset_by_name(self, name: str) -> None:
        """Programmatically select a preset by its key name."""
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == name:
                self._combo.setCurrentIndex(i)
                return

    # ── Internal ────────────────────────────────────────────────────

    def _on_index_changed(self, index: int) -> None:
        key = self._combo.itemData(index)
        if key is not None:
            preset = PLATFORM_PRESETS[key]
            self.platformChanged.emit(preset)
