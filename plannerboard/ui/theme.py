# Catppuccin Mocha palette
BG       = "#1e1e2e"
SURFACE  = "#313244"
SURFACE2 = "#45475a"
OVERLAY  = "#6c7086"
TEXT     = "#cdd6f4"
SUBTEXT  = "#a6adc8"
BLUE     = "#89b4fa"
GREEN    = "#a6e3a1"
RED      = "#f38ba8"
YELLOW   = "#f9e2af"
MAUVE    = "#cba6f7"
PEACH    = "#fab387"
TEAL     = "#94e2d5"
PINK     = "#f5c2e7"
BORDER   = "#585b70"

EVENT_COLORS = [BLUE, GREEN, MAUVE, PEACH, TEAL, PINK, RED, YELLOW]

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Noto Sans", "Segoe UI", sans-serif;
    font-size: 10pt;
}}
QPushButton {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 10px;
}}
QPushButton:hover {{
    background-color: {SURFACE2};
}}
QPushButton:pressed {{
    background-color: {OVERLAY};
}}
QPushButton:checked {{
    background-color: {BLUE};
    color: {BG};
    border-color: {BLUE};
}}
QScrollBar:vertical {{
    background: {SURFACE};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {OVERLAY};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {SURFACE};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {OVERLAY};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QTimeEdit, QDateEdit {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px;
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {TEXT};
    selection-background-color: {BLUE};
    selection-color: {BG};
}}
QLabel {{ color: {TEXT}; }}
QDialog {{
    background-color: {BG};
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
}}
QGroupBox::title {{
    color: {SUBTEXT};
    subcontrol-origin: margin;
    left: 10px;
}}
QCheckBox {{
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {SURFACE};
}}
QCheckBox::indicator:checked {{
    background: {BLUE};
    border-color: {BLUE};
}}
QSplitter::handle {{
    background: {BORDER};
    width: 1px;
}}
"""
