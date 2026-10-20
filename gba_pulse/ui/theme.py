from gba_pulse.config import COLORS

GLOBAL_STYLE = f"""
QWidget {{
    background: {COLORS['background']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 10pt;
}}
QDialog {{ background: {COLORS['background']}; }}
QLabel {{ background: transparent; border: none; }}
QFrame#surfaceCard {{ background: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 15px; }}
QFrame#raisedCard {{ background: {COLORS['surface_raised']}; border: 1px solid {COLORS['border']}; border-radius: 14px; }}
QPushButton {{
    background: {COLORS['surface_raised']}; color: {COLORS['text']};
    border: 1px solid {COLORS['border']}; border-radius: 9px;
    padding: 8px 12px; font-weight: 600;
}}
QPushButton:hover {{ background: {COLORS['surface_hover']}; border-color: {COLORS['accent']}; }}
QPushButton:pressed {{ background: {COLORS['accent_soft']}; }}
QPushButton#primaryButton {{ background: {COLORS['accent']}; color: #15100A; border: none; }}
QPushButton#primaryButton:hover {{ background: #FFAB4D; }}
QPushButton#quietButton {{ background: transparent; border: 1px solid transparent; padding: 6px; color: {COLORS['muted']}; }}
QPushButton#quietButton:hover {{ background: {COLORS['surface_hover']}; color: {COLORS['text']}; border-color: {COLORS['border']}; }}
QLineEdit, QComboBox {{
    background: {COLORS['surface_raised']}; color: {COLORS['text']};
    border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 8px 10px;
    selection-background-color: {COLORS['accent']}; selection-color: #111;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {COLORS['accent']}; }}
QCheckBox {{ spacing: 8px; color: {COLORS['text']}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {COLORS['muted_2']}; background: {COLORS['surface_raised']}; }}
QCheckBox::indicator:checked {{ background: {COLORS['accent']}; border-color: {COLORS['accent']}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ width: 5px; background: transparent; margin: 3px 0; }}
QScrollBar::handle:vertical {{ background: {COLORS['muted_2']}; border-radius: 2px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""
