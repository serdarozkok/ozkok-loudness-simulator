"""
Global QSS stylesheet — Teal & Peach brand identity (v2).

Background: deep slate #1A202C — makes Teal, Peach and Red pop.

Typography:
- **Montserrat** — headings, titles, button labels
- **Poppins** — body text, metric readouts, status
"""

# ── Palette ─────────────────────────────────────────────────────────

COLORS = {
    # Backgrounds (dark → light)
    "bg_primary":       "#1A202C",   # Main window
    "bg_secondary":     "#1E293B",   # Panels, drop zone
    "bg_card":          "#2D3748",   # Cards, inactive buttons
    "bg_input":         "#1E293B",   # Input fields
    "bg_hover":         "#374151",   # Hover state on muted elements

    # Brand Teal
    "teal":             "#0D9488",   # Primary accent
    "teal_hover":       "#14B8A6",   # Hover
    "teal_pressed":     "#0F766E",   # Pressed / active

    # Brand Peach
    "peach":            "#FFB6A1",   # Secondary accent
    "peach_hover":      "#FFC8B8",   # Hover peach
    "peach_text":       "#3D1A0E",   # Dark text on peach

    # ISP / Clipping Red
    "isp_red":          "#FF4C4C",   # True-peak violation markers

    # Text
    "text_primary":     "#F0EFEB",   # Warm white
    "text_secondary":   "#94A3B8",   # Slate grey
    "text_on_teal":     "#0B1F1E",   # Dark on teal buttons

    # Chrome
    "border":           "#2D3748",   # Subtle borders
    "border_hover":     "#0D9488",
    "separator":        "#2D3748",

    # Gate map waveform
    "gate_included":    "#0D9488",   # Passes relative gate
    "gate_excluded":    "#4A5568",   # Below threshold
}

# ── Font stacks ─────────────────────────────────────────────────────

FONT_HEADING = '"Montserrat", "Segoe UI", "Helvetica Neue", Arial, sans-serif'
FONT_BODY    = '"Poppins", "Segoe UI", "Helvetica Neue", Arial, sans-serif'
FONT_MONO    = '"Poppins", "Consolas", "SF Mono", monospace'

# ── Stylesheet ──────────────────────────────────────────────────

GLOBAL_STYLESHEET = f"""

/* ────────────────────────────────────────────────────────────────────────────
   GLOBAL
   ──────────────────────────────────────────────────────────────────────────── */

QMainWindow, QWidget {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-family: {FONT_BODY};
    font-size: 13px;
}}

/* ────────────────────────────────────────────────────────────────────────────
   LABELS
   ──────────────────────────────────────────────────────────────────────────── */

QLabel {{
    color: {COLORS['text_primary']};
    background: transparent;
    font-family: {FONT_BODY};
}}

QLabel[cssClass="heading"] {{
    font-family: {FONT_HEADING};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 3px;
    color: {COLORS['peach']};
}}

QLabel[cssClass="subheading"] {{
    font-family: {FONT_BODY};
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

QLabel[cssClass="metric-value"] {{
    font-family: {FONT_MONO};
    font-size: 28px;
    font-weight: 600;
    color: {COLORS['text_primary']};
}}

QLabel[cssClass="metric-label"] {{
    font-family: {FONT_HEADING};
    font-size: 11px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
    letter-spacing: 1.5px;
}}

QLabel[cssClass="metric-clipping"] {{
    font-family: {FONT_MONO};
    font-size: 28px;
    font-weight: 700;
    color: {COLORS['peach']};
}}

QLabel[cssClass="filename"] {{
    font-family: {FONT_BODY};
    font-size: 13px;
    color: {COLORS['peach']};
    font-weight: 600;
}}

QLabel[cssClass="time-label"] {{
    font-family: {FONT_MONO};
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

/* ═══════════════════════════════════════════════════════
   DROP ZONE
   ═══════════════════════════════════════════════════════ */

QFrame[cssClass="drop-zone"] {{
    border: 2px dashed {COLORS['border']};
    border-radius: 12px;
    background-color: {COLORS['bg_secondary']};
    min-height: 130px;
}}

QFrame[cssClass="drop-zone-hover"] {{
    border: 2.5px dashed {COLORS['peach']};
    border-radius: 12px;
    background-color: rgba(255, 182, 161, 0.06);
    min-height: 130px;
}}

QFrame[cssClass="drop-zone-loaded"] {{
    border: 2px solid {COLORS['teal']};
    border-radius: 12px;
    background-color: {COLORS['bg_secondary']};
    min-height: 90px;
}}

/* ═══════════════════════════════════════════════════════
   METRICS PANEL
   ═══════════════════════════════════════════════════════ */

QFrame[cssClass="metrics-panel"] {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 14px;
}}

QFrame[cssClass="metrics-column"] {{
    background: transparent;
    border: none;
    padding: 8px;
}}

QFrame[cssClass="separator"] {{
    background-color: {COLORS['separator']};
    max-width: 1px;
    min-width: 1px;
}}

/* ═══════════════════════════════════════════════════════
   COMBO BOX (Platform selector)
   ═══════════════════════════════════════════════════════ */

QComboBox {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 9px 14px;
    font-family: {FONT_BODY};
    font-size: 13px;
    font-weight: 600;
    min-width: 280px;
}}

QComboBox:hover {{
    border-color: {COLORS['teal']};
}}

QComboBox:focus {{
    border-color: {COLORS['peach']};
}}

QComboBox::drop-down {{
    border: none;
    width: 32px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['peach']};
    margin-right: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['teal']};
    selection-color: {COLORS['text_on_teal']};
    outline: none;
    border-radius: 4px;
    padding: 4px;
}}

/* ═══════════════════════════════════════════════════════
   BUTTONS — flat, modern, no 3D borders
   ═══════════════════════════════════════════════════════ */

QPushButton {{
    background-color: {COLORS['teal']};
    color: {COLORS['text_primary']};
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: {FONT_HEADING};
    font-size: 13px;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: {COLORS['teal_hover']};
    color: {COLORS['text_on_teal']};
}}

QPushButton:pressed {{
    background-color: {COLORS['teal_pressed']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['border']};
}}

/* ── Transport (circular play/stop) ─────────────────── */

QPushButton[cssClass="transport-btn"] {{
    min-width: 48px;
    min-height: 48px;
    max-width: 48px;
    max-height: 48px;
    border-radius: 24px;
    font-size: 20px;
    padding: 0px;
    background-color: {COLORS['teal']};
    color: {COLORS['text_on_teal']};
    border: none;
}}

QPushButton[cssClass="transport-btn"]:hover {{
    background-color: {COLORS['teal_hover']};
}}

QPushButton[cssClass="transport-btn"]:pressed {{
    background-color: {COLORS['teal_pressed']};
}}

/* ── A/B Toggle ─────────────────────────────────────── */

QPushButton[cssClass="ab-active"] {{
    background-color: {COLORS['peach']};
    color: {COLORS['peach_text']};
    border: none;
    border-radius: 8px;
    font-weight: 700;
}}

QPushButton[cssClass="ab-active"]:hover {{
    background-color: {COLORS['peach_hover']};
}}

QPushButton[cssClass="ab-inactive"] {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_secondary']};
    border: none;
    border-radius: 8px;
    font-weight: 600;
}}

QPushButton[cssClass="ab-inactive"]:hover {{
    background-color: {COLORS['bg_hover']};
    color: {COLORS['text_primary']};
}}

/* ── Export button — outlined peach ─────────────────── */

QPushButton[cssClass="export-btn"] {{
    background-color: transparent;
    border: 1.5px solid {COLORS['peach']};
    border-radius: 8px;
    color: {COLORS['peach']};
    font-weight: 700;
}}

QPushButton[cssClass="export-btn"]:hover {{
    background-color: {COLORS['peach']};
    color: {COLORS['peach_text']};
}}

QPushButton[cssClass="export-btn"]:pressed {{
    background-color: {COLORS['peach_hover']};
    color: {COLORS['peach_text']};
}}

/* ═══════════════════════════════════════════════════════
   SLIDER (Seek bar)
   ═══════════════════════════════════════════════════════ */

QSlider::groove:horizontal {{
    height: 5px;
    background: {COLORS['bg_card']};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['peach']};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS['peach_hover']};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::sub-page:horizontal {{
    background: {COLORS['teal']};
    border-radius: 2px;
}}

/* ═══════════════════════════════════════════════════════
   STATUS LABELS
   ═══════════════════════════════════════════════════════ */

QLabel[cssClass="status-processing"] {{
    font-family: {FONT_BODY};
    color: {COLORS['teal_hover']};
    font-size: 13px;
    font-weight: 600;
}}

QLabel[cssClass="status-error"] {{
    font-family: {FONT_BODY};
    color: {COLORS['isp_red']};
    font-size: 13px;
    font-weight: 600;
}}

/* ═══════════════════════════════════════════════════════
   SCROLL AREA (for pyqtgraph container if needed)
   ═══════════════════════════════════════════════════════ */

QScrollArea {{
    border: none;
    background: transparent;
}}

/* Platform Cards (V2 Dashboard) */
QFrame[cssClass="platform-card"] {{
    background-color: #1E293B;
    border-radius: 10px;
    border: 1px solid #2D3748;
}}
QFrame[cssClass="platform-card"]:hover {{
    border: 1px solid #0D9488;
}}
QFrame[cssClass="platform-card active"] {{
    background-color: #1A202C;
    border: 2px solid #0D9488;
}}

QLabel[cssClass="platform-card-title"] {{
    font-family: "Montserrat";
    font-size: 14px;
    font-weight: bold;
    color: #F0EFEB;
}}
QLabel[cssClass="platform-card-lufs"] {{
    font-size: 11px;
    color: #94A3B8;
}}
QLabel[cssClass="platform-card-penalty"] {{
    font-family: "Poppins";
    font-size: 20px;
    font-weight: bold;
    color: #94A3B8;
}}
QLabel[cssClass~="penalty-neg"] {{
    color: #FFB6A1;
}}
QLabel[cssClass~="penalty-pos"] {{
    color: #0D9488;
}}

/* V2 Toggle Buttons (Normalize & Delta) */
QPushButton[cssClass="toggle-active"] {{
    background-color: #0D9488;
    color: #0B1F1E;
    border-radius: 8px;
    font-family: "Montserrat";
    font-weight: bold;
    font-size: 11px;
    border: none;
}}
QPushButton[cssClass="toggle-active"]:hover {{
    background-color: #14B8A6;
}}
QPushButton[cssClass="toggle-inactive"] {{
    background-color: #2D3748;
    color: #94A3B8;
    border-radius: 8px;
    font-family: "Montserrat";
    font-weight: bold;
    font-size: 11px;
    border: 1px solid #374151;
}}
QPushButton[cssClass="toggle-inactive"]:hover {{
    background-color: #374151;
    color: #F0EFEB;
}}"""
