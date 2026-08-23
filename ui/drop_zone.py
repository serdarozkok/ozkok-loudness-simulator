"""
Drag-and-drop zone widget.

Shows a dashed-border region with an invitation to drop WAV/FLAC files.
Provides visual feedback on hover, emits ``fileDropped(str)`` with the
file path, and includes a fallback "Browse" button.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from audio.file_loader import SUPPORTED_EXTENSIONS


class DropZone(QFrame):
    """Drop target for audio files."""

    fileDropped = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cssClass", "drop-zone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        # Icon / emoji
        icon_label = QLabel("🎵")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 40px; background: transparent;")
        layout.addWidget(icon_label)

        # Main text
        self._label = QLabel("Drop WAV or FLAC file here")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setProperty("cssClass", "subheading")
        self._label.setStyleSheet("font-size: 14px; color: #94A3B8;")
        layout.addWidget(self._label)

        # Browse button row
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(120)
        browse_btn.clicked.connect(self._browse)
        btn_row.addWidget(browse_btn)
        layout.addLayout(btn_row)

        # Filename display (hidden initially)
        self._filename_label = QLabel("")
        self._filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filename_label.setProperty("cssClass", "filename")
        self._filename_label.hide()
        layout.addWidget(self._filename_label)

    # ── Drag-and-drop events ────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                _, ext = os.path.splitext(path)
                if ext.lower() in SUPPORTED_EXTENSIONS:
                    event.acceptProposedAction()
                    self.setProperty("cssClass", "drop-zone-hover")
                    self.style().unpolish(self)
                    self.style().polish(self)
                    return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("cssClass", "drop-zone")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event) -> None:
        self.setProperty("cssClass", "drop-zone-loaded")
        self.style().unpolish(self)
        self.style().polish(self)

        for url in event.mimeData().urls():
            path = url.toLocalFile()
            _, ext = os.path.splitext(path)
            if ext.lower() in SUPPORTED_EXTENSIONS:
                self._show_filename(path)
                self.fileDropped.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # ── Browse fallback ─────────────────────────────────────────────

    def _browse(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            f"Audio Files ({exts})",
        )
        if path:
            self._show_filename(path)
            self.setProperty("cssClass", "drop-zone-loaded")
            self.style().unpolish(self)
            self.style().polish(self)
            self.fileDropped.emit(path)

    def _show_filename(self, path: str) -> None:
        name = os.path.basename(path)
        self._label.setText("Loaded:")
        self._label.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self._filename_label.setText(name)
        self._filename_label.show()
