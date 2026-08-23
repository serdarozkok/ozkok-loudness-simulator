"""
Font loader — registers bundled Montserrat and Poppins .ttf files
with the Qt font database so they work identically on any PC,
regardless of whether the user has these fonts installed system-wide.

Call ``load_fonts()`` **before** applying the global stylesheet.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtGui import QFontDatabase

logger = logging.getLogger(__name__)

# Directory containing the .ttf files (relative to this module)
_FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# Expected font files
_FONT_FILES = [
    "Montserrat-Regular.ttf",
    "Montserrat-SemiBold.ttf",
    "Montserrat-Bold.ttf",
    "Poppins-Regular.ttf",
    "Poppins-SemiBold.ttf",
    "Poppins-Bold.ttf",
]


def load_fonts() -> list[str]:
    """Register all bundled .ttf fonts and return the family names loaded.

    Returns
    -------
    list[str]
        Unique font family names that were successfully registered
        (e.g. ``['Montserrat', 'Poppins']``).
    """
    loaded_families: set[str] = set()

    for filename in _FONT_FILES:
        filepath = os.path.join(_FONTS_DIR, filename)
        if not os.path.isfile(filepath):
            logger.warning("Font file not found: %s", filepath)
            continue

        font_id = QFontDatabase.addApplicationFont(filepath)
        if font_id < 0:
            logger.error("Failed to load font: %s", filepath)
            continue

        families = QFontDatabase.applicationFontFamilies(font_id)
        for family in families:
            loaded_families.add(family)
        logger.info("Loaded font: %s → %s", filename, ", ".join(families))

    result = sorted(loaded_families)
    logger.info("Font families available: %s", result)
    return result
