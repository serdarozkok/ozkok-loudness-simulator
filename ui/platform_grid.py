from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from core.platforms import PLATFORM_PRESETS, PlatformPreset

logger = logging.getLogger(__name__)


class PlatformCard(QFrame):
    """A single card representing a streaming platform."""

    clicked = Signal(str)  # Emits the platform preset name

    def __init__(self, preset_name: str, preset: PlatformPreset, parent=None):
        super().__init__(parent)
        self.preset_name = preset_name
        self.preset = preset
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty("cssClass", "platform-card")

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)

        # Title
        title_text = preset.display_name.split("(")[0].strip()
        self.lbl_title = QLabel(title_text)
        self.lbl_title.setProperty("cssClass", "platform-card-title")
        self.lbl_title.setAlignment(Qt.AlignCenter)

        # Target LUFS
        lufs_str = f"{preset.target_lufs} LUFS" if preset.target_lufs else "No Target"
        self.lbl_lufs = QLabel(lufs_str)
        self.lbl_lufs.setProperty("cssClass", "platform-card-lufs")
        self.lbl_lufs.setAlignment(Qt.AlignCenter)

        # Penalty / Boost Value
        self.lbl_penalty = QLabel("-")
        self.lbl_penalty.setProperty("cssClass", "platform-card-penalty")
        self.lbl_penalty.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.lbl_title)
        self.layout.addWidget(self.lbl_lufs)
        self.layout.addSpacing(5)
        self.layout.addWidget(self.lbl_penalty)

    def set_penalty(self, penalty_db: Optional[float]):
        """Update the displayed penalty value."""
        if penalty_db is None:
            self.lbl_penalty.setText("-")
            self.lbl_penalty.setProperty("cssClass", "platform-card-penalty")
        else:
            self.lbl_penalty.setText(f"{penalty_db:+.2f} dB")
            if penalty_db < -0.05:
                self.lbl_penalty.setProperty("cssClass", "platform-card-penalty penalty-neg")
            elif penalty_db > 0.05:
                self.lbl_penalty.setProperty("cssClass", "platform-card-penalty penalty-pos")
            else:
                self.lbl_penalty.setProperty("cssClass", "platform-card-penalty penalty-zero")
                self.lbl_penalty.setText("0.00 dB")
        
        self.lbl_penalty.style().unpolish(self.lbl_penalty)
        self.lbl_penalty.style().polish(self.lbl_penalty)

    def set_active(self, active: bool):
        """Highlight the card if active."""
        cls = "platform-card active" if active else "platform-card"
        self.setProperty("cssClass", cls)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.preset_name)
        super().mousePressEvent(event)


class PlatformGrid(QWidget):
    """Grid dashboard displaying all platforms and their loudness penalties."""

    platformChanged = Signal(object)  # Emits PlatformPreset

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.cards: dict[str, PlatformCard] = {}
        self.current_active_name: str = "spotify_normal"

        # Special Spotify dropdown container
        self.spotify_combo = QComboBox()
        self.spotify_combo.addItem("Normal (-14)", "spotify_normal")
        self.spotify_combo.addItem("Loud (-11)", "spotify_loud")
        self.spotify_combo.addItem("Quiet (-19)", "spotify_quiet")
        self.spotify_combo.currentIndexChanged.connect(self._on_spotify_combo_changed)

        self._build_grid()
        self._set_active_card(self.current_active_name)

    def _build_grid(self):
        positions = [
            ("spotify", 0, 0),
            ("apple_music", 0, 1),
            ("youtube_music", 0, 2),
            ("tidal", 1, 0),
            ("amazon", 1, 1),
            ("deezer", 1, 2),
        ]

        for key, row, col in positions:
            if key == "spotify":
                preset_name = self.spotify_combo.currentData()
                card = PlatformCard(preset_name, PLATFORM_PRESETS[preset_name])
                
                # Replace the title label with the combo box
                card.layout.removeWidget(card.lbl_title)
                card.lbl_title.hide()
                
                combo_layout = QHBoxLayout()
                combo_label = QLabel("Spotify")
                combo_label.setProperty("cssClass", "platform-card-title")
                combo_layout.addWidget(combo_label)
                combo_layout.addWidget(self.spotify_combo)
                card.layout.insertLayout(0, combo_layout)
                
                self.cards["spotify"] = card
                card.clicked.connect(lambda _, k="spotify": self._on_card_clicked(k))
            else:
                card = PlatformCard(key, PLATFORM_PRESETS[key])
                self.cards[key] = card
                card.clicked.connect(lambda name, k=key: self._on_card_clicked(k))
                
            self.layout.addWidget(card, row, col)

    def _on_spotify_combo_changed(self):
        new_preset_name = self.spotify_combo.currentData()
        preset = PLATFORM_PRESETS[new_preset_name]
        
        card = self.cards["spotify"]
        card.preset_name = new_preset_name
        card.preset = preset
        card.lbl_lufs.setText(f"{preset.target_lufs} LUFS")
        
        # If Spotify was active, trigger platform change
        if self.current_active_name in ("spotify_normal", "spotify_loud", "spotify_quiet"):
            self.current_active_name = new_preset_name
            self.platformChanged.emit(preset)

    def _on_card_clicked(self, grid_key: str):
        card = self.cards[grid_key]
        preset_name = card.preset_name
        if preset_name != self.current_active_name:
            self._set_active_card(preset_name)
            self.platformChanged.emit(card.preset)

    def _set_active_card(self, active_preset_name: str):
        self.current_active_name = active_preset_name
        for key, card in self.cards.items():
            # Check if this card's current preset name matches
            if key == "spotify":
                is_active = (active_preset_name in ["spotify_normal", "spotify_loud", "spotify_quiet"])
            else:
                is_active = (card.preset_name == active_preset_name)
            card.set_active(is_active)

    def current_preset(self) -> PlatformPreset:
        return PLATFORM_PRESETS[self.current_active_name]

    def update_penalties(self, master_lufs: float):
        """Instantly calculate and display penalties for all grid cards."""
        from core.gain_processor import calculate_penalty
        
        for key, card in self.cards.items():
            preset = card.preset
            if preset.target_lufs is not None:
                penalty = calculate_penalty(master_lufs, preset.target_lufs, preset.turns_up)
                card.set_penalty(penalty)
            else:
                card.set_penalty(0.0)

    def reset_penalties(self):
        for card in self.cards.values():
            card.set_penalty(None)
