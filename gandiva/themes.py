"""
Color themes for gandiva.

Each theme is a dict of named colors (as RGB tuples).
Use get_theme() to retrieve one by name, or THEMES for the full registry.

To add a new theme: define a dict following the same keys, add it to THEMES.
"""

from PyQt6.QtGui import QColor


def _c(r, g, b):
    return QColor(r, g, b)


# ── Cosmic (inspired by nhs/images/home.png) ────────────────────────────────
# Deep purple-black background, electric cyan lines, golden accents
COSMIC = {
    "name": "Cosmic",

    # backgrounds
    "bg":              _c(12, 8, 30),        # deep indigo-black
    "bg_inner":        _c(18, 14, 42),       # slightly lighter inner circle
    "bg_ring":         _c(22, 16, 50),       # zodiac ring base

    # element segment fills (semi-transparent, alpha set in code)
    "fire":            _c(200, 60, 200),     # magenta-purple
    "earth":           _c(40, 180, 120),     # teal-green
    "air":             _c(80, 60, 200),      # deep blue-violet
    "water":           _c(30, 160, 220),     # electric cyan

    # lines and borders
    "line":            _c(60, 200, 200),     # cyan
    "line_light":      _c(40, 120, 140),     # muted cyan
    "line_angular":    _c(100, 240, 240),    # bright cyan for 1/4/7/10
    "ring_border":     _c(80, 60, 180),      # purple border

    # text and glyphs
    "glyph":           _c(220, 200, 80),     # golden yellow
    "glyph_retro":     _c(255, 100, 60),     # orange-red
    "glyph_selected":  _c(255, 220, 100),    # bright gold
    "sign_label":      _c(180, 140, 255),    # lavender
    "cusp_label":      _c(100, 200, 255),    # light cyan
    "house_label":     _c(80, 220, 180),     # mint

    # UI chrome (for input panel, tables, etc.)
    "ui_bg":           _c(18, 14, 38),
    "ui_text":         _c(200, 190, 240),
    "ui_border":       _c(60, 50, 120),
    "ui_accent":       _c(120, 80, 255),
    "ui_button_bg":    _c(40, 30, 80),
    "ui_input_bg":     _c(25, 20, 55),
}


# ── Forest ───────────────────────────────────────────────────────────────────
# Deep green-gray background, muted gold accents, earthy warmth
FOREST = {
    "name": "Forest",

    "bg":              _c(22, 32, 26),
    "bg_inner":        _c(28, 40, 32),
    "bg_ring":         _c(32, 45, 35),

    "fire":            _c(180, 100, 50),     # amber
    "earth":           _c(80, 140, 70),      # moss green
    "air":             _c(160, 170, 120),    # sage
    "water":           _c(60, 110, 130),     # deep teal

    "line":            _c(140, 130, 90),     # muted gold
    "line_light":      _c(90, 85, 65),       # dark gold
    "line_angular":    _c(190, 170, 100),    # bright gold
    "ring_border":     _c(80, 90, 60),

    "glyph":           _c(210, 190, 120),    # warm gold
    "glyph_retro":     _c(200, 100, 50),     # burnt orange
    "glyph_selected":  _c(255, 220, 120),    # bright gold
    "sign_label":      _c(180, 170, 130),    # parchment
    "cusp_label":      _c(140, 160, 110),    # sage
    "house_label":     _c(160, 150, 110),    # khaki

    "ui_bg":           _c(25, 35, 28),
    "ui_text":         _c(200, 195, 170),
    "ui_border":       _c(70, 80, 55),
    "ui_accent":       _c(160, 140, 70),
    "ui_button_bg":    _c(35, 48, 38),
    "ui_input_bg":     _c(30, 42, 33),
}


# ── Light (current default, cleaned up) ──────────────────────────────────────
LIGHT = {
    "name": "Light",

    "bg":              _c(255, 255, 255),
    "bg_inner":        _c(250, 248, 245),
    "bg_ring":         _c(255, 255, 255),

    "fire":            _c(220, 80, 80),
    "earth":           _c(80, 160, 80),
    "air":             _c(220, 200, 60),
    "water":           _c(80, 130, 200),

    "line":            _c(30, 30, 30),
    "line_light":      _c(90, 90, 90),
    "line_angular":    _c(30, 30, 30),
    "ring_border":     _c(30, 30, 30),

    "glyph":           _c(20, 20, 20),
    "glyph_retro":     _c(160, 60, 20),
    "glyph_selected":  _c(200, 60, 60),
    "sign_label":      _c(60, 60, 60),
    "cusp_label":      _c(40, 40, 130),
    "house_label":     _c(20, 20, 20),

    "ui_bg":           _c(245, 245, 245),
    "ui_text":         _c(20, 20, 20),
    "ui_border":       _c(200, 200, 200),
    "ui_accent":       _c(60, 100, 200),
    "ui_button_bg":    _c(230, 230, 230),
    "ui_input_bg":     _c(255, 255, 255),
}


# ── Registry ─────────────────────────────────────────────────────────────────

THEMES = {
    "Light": LIGHT,
    "Forest": FOREST,
    "Cosmic": COSMIC,
}

DEFAULT_THEME = "Cosmic"


def get_theme(name: str) -> dict:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def theme_names() -> list[str]:
    return list(THEMES.keys())


def _rgb(c) -> str:
    return f"rgb({c.red()},{c.green()},{c.blue()})"


def make_app_stylesheet(theme: dict) -> str:
    bg       = _rgb(theme["ui_bg"])
    text     = _rgb(theme["ui_text"])
    border   = _rgb(theme["ui_border"])
    accent   = _rgb(theme["ui_accent"])
    btn      = _rgb(theme["ui_button_bg"])
    inp      = _rgb(theme["ui_input_bg"])
    line     = _rgb(theme["line"])
    line_l   = _rgb(theme["line_light"])

    return f"""
    /* ── base ── */
    QWidget {{
        background-color: {bg};
        color: {text};
        border: none;
        outline: none;
    }}

    /* ── main window & splitter ── */
    QMainWindow, QSplitter {{
        background-color: {bg};
    }}
    QSplitter::handle {{
        background-color: {border};
        width: 2px;
        height: 2px;
    }}

    /* ── scroll area ── */
    QScrollArea, QScrollArea > QWidget > QWidget {{
        background-color: {bg};
    }}

    /* ── inputs ── */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit {{
        background-color: {inp};
        color: {text};
        border: 1px solid {border};
        border-radius: 3px;
        padding: 1px 3px;
        selection-background-color: {accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {inp};
        color: {text};
        border: 1px solid {border};
        selection-background-color: {accent};
    }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
    QDateTimeEdit::up-button, QDateTimeEdit::down-button {{
        background-color: {btn};
        border: 1px solid {border};
        width: 14px;
    }}

    /* ── buttons ── */
    QPushButton {{
        background-color: {btn};
        color: {text};
        border: 1px solid {border};
        border-radius: 3px;
        padding: 3px 8px;
    }}
    QPushButton:hover {{
        border-color: {accent};
        color: {_rgb(theme["ui_accent"])};
    }}
    QPushButton:pressed {{
        background-color: {accent};
        color: {bg};
    }}

    /* ── group box ── */
    QGroupBox {{
        border: 1px solid {border};
        border-radius: 4px;
        margin-top: 10px;
        padding-top: 4px;
    }}
    QGroupBox::title {{
        color: {_rgb(theme["ui_accent"])};
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 4px;
    }}

    /* ── labels ── */
    QLabel {{
        background-color: transparent;
        color: {text};
    }}

    /* ── checkboxes ── */
    QCheckBox {{
        color: {text};
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 13px;
        height: 13px;
        border: 1px solid {border};
        border-radius: 2px;
        background-color: {inp};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}

    /* ── tab bar ── */
    QTabBar {{
        background-color: {bg};
    }}
    QTabBar::tab {{
        background-color: {btn};
        color: {text};
        border: 1px solid {border};
        padding: 4px 8px;
        margin: 1px;
    }}
    QTabBar::tab:selected {{
        background-color: {accent};
        color: {bg};
    }}

    /* ── tables ── */
    QTableWidget {{
        background-color: {inp};
        color: {text};
        gridline-color: {border};
        border: 1px solid {border};
    }}
    QTableWidget::item:selected {{
        background-color: {accent};
        color: {bg};
    }}
    QHeaderView::section {{
        background-color: {btn};
        color: {text};
        border: 1px solid {border};
        padding: 2px 4px;
    }}

    /* ── scrollbars ── */
    QScrollBar:vertical, QScrollBar:horizontal {{
        background-color: {bg};
        border: none;
        width: 8px;
        height: 8px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background-color: {border};
        border-radius: 4px;
        min-height: 20px;
        min-width: 20px;
    }}
    QScrollBar::handle:hover {{
        background-color: {accent};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
    }}

    /* ── tooltip ── */
    QToolTip {{
        background-color: {inp};
        color: {text};
        border: 1px solid {accent};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 16px;
    }}
    """
