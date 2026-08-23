"""
OZKOK Loudness & Codec Simulator — Application entry point.

Usage::

    python main.py
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from resources.font_loader import load_fonts
from ui.main_window import MainWindow
from ui.styles import GLOBAL_STYLESHEET


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = QApplication(sys.argv)
    app.setApplicationName("OZKOK Loudness & Codec Simulator")
    app.setOrganizationName("OZKOK")

    # Register bundled Montserrat + Poppins fonts BEFORE stylesheet
    loaded = load_fonts()
    logging.getLogger(__name__).info("Registered font families: %s", loaded)

    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
