# Cursor Bite — Modern UI Theme & Design System
# ============================================================
# Design Language:
#   - Premium Dark Glassmorphism / Obsidian & Acrylic
#   - Curated, vibrant action accent colors & neon glows
#   - High legibility, modern typography (Segoe UI / Segoe UI Variable)
#   - Micro-interactions, smooth hover transitions
#   - Zero visual clutter, elegant spacing and hierarchy

import logging
from PyQt6.QtCore import Qt, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPalette, QBrush
from PyQt6.QtWidgets import QStyle

from domain.models import ActionKind
from utils.logger import get_logger

logger = get_logger("ui.theme")


# ── Color Palette & Action Tokens ──────────────────────────────────

class CursorBiteColors:
    """Cursor Bite design system color tokens."""

    # Surfaces & Minimal Overlay
    BACKGROUND_PRIMARY   = QColor("#0B0D13")        # Deep obsidian
    BACKGROUND_SECONDARY = QColor("#131622")        # Elevated card surface
    BACKGROUND_TERTIARY  = QColor("#1A1E2D")        # Input / inner container
    SURFACE_GLASS        = QColor(15, 17, 26, 245)  # Compact HUD glass
    SURFACE_HOVER        = QColor(35, 40, 62, 220)  # Subtle hover highlight
    OVERLAY_BACKGROUND   = QColor(11, 13, 19, 245)  # Overlay backdrop

    # Primary Restrained Accent (Soft Purple / Blue-Violet)
    ACCENT_PRIMARY   = QColor("#6366F1")            # Soft purple-violet
    ACCENT_SECONDARY = QColor("#818CF8")            # Light violet highlight
    ACCENT_HOVER     = QColor("#4F46E5")            # Deep violet
    ACCENT_GLOW      = QColor(99, 102, 241, 60)     # Subtle glow ring

    # Subtle Supporting Accent (Subtle Blue)
    ACCENT_SUBTLE    = QColor("#38BDF8")            # Supporting muted blue

    # Typography
    TEXT_PRIMARY   = QColor("#F8FAFC")              # Crisp white
    TEXT_SECONDARY = QColor("#94A3B8")              # Slate grey
    TEXT_TERTIARY  = QColor("#64748B")              # Muted grey
    TEXT_ACCENT    = QColor("#A5B4FC")              # Soft violet-blue text
    TEXT_MUTED     = QColor("#475569")              # Darker subtle

    # Borders & Dividers
    BORDER_SUBTLE  = QColor(255, 255, 255, 18)      # 7% white border
    BORDER_CARD    = QColor("#222738")              # Card border
    BORDER_HOVER   = QColor("#6366F1")              # Accent border on focus
    BORDER_DIVIDER = QColor(255, 255, 255, 12)      # Sector dividers

    # Status Indicators
    SUCCESS = QColor("#10B981")                     # Green for healthy / ready
    WARNING = QColor("#F59E0B")                     # Amber for attention
    ERROR   = QColor("#EF4444")                     # Red ONLY for actual errors
    INFO    = QColor("#38BDF8")                     # Subtle blue

    # Transparency Defaults
    OPACITY_DEFAULT = 0.96
    OPACITY_MIN     = 0.80
    OPACITY_MAX     = 1.0


# Map each action to its clean, unified theme metadata
ACTION_THEME = {
    ActionKind.TRANSLATE: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Translate",
        "desc": "Offline Neural Translation",
        "icon": "🌐",
    },
    ActionKind.SUMMARIZE: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Summarize",
        "desc": "Extract Key Points with AI",
        "icon": "📑",
    },
    ActionKind.EXPLAIN: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Explain",
        "desc": "Context-Aware Local AI Explanation",
        "icon": "💡",
    },
    ActionKind.SEARCH_WEB: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Search Web",
        "desc": "Find Online via DuckDuckGo",
        "icon": "🔍",
    },
    ActionKind.SETTINGS: {
        "color": CursorBiteColors.TEXT_SECONDARY,
        "name": "Settings",
        "desc": "Configure Preferences & Models",
        "icon": "⚙️",
    },
    ActionKind.CAPTURE_TEXT: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Capture OCR",
        "desc": "Drag Region to Read Text",
        "icon": "📷",
    },
    ActionKind.REWRITE: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Rewrite",
        "desc": "Polish Prose with Semantic Preservation",
        "icon": "✍️",
    },
    ActionKind.ASK_AI: {
        "color": CursorBiteColors.ACCENT_SECONDARY,
        "name": "Ask AI",
        "desc": "Ask Custom Questions on Context",
        "icon": "🤖",
    },
}


# ── Sizing & Dimensions ────────────────────────────────────────────

class Sizing:
    """UI dimension tokens for compact, lightweight native utility."""

    # Compact Radial menu (target: 180-220px)
    MENU_RADIUS_DEFAULT = 100
    MENU_INNER_RADIUS   = 40
    MENU_CENTER_SIZE    = 36
    MENU_TOTAL_SIZE     = 220

    # Fonts
    FONT_SIZE_TINY   = 9
    FONT_SIZE_SMALL  = 11
    FONT_SIZE_NORMAL = 13
    FONT_SIZE_MEDIUM = 14
    FONT_SIZE_LARGE  = 16
    FONT_SIZE_XLARGE = 18
    FONT_SIZE_SMALL  = 11
    FONT_SIZE_NORMAL = 13
    FONT_SIZE_LARGE  = 15
    FONT_SIZE_TITLE  = 18
    FONT_SIZE_CENTER = 12

    # Animation
    ANIMATION_DURATION_DEFAULT = 160
    ANIMATION_DURATION_FAST    = 80
    ANIMATION_EASING = QEasingCurve.Type.OutCubic

    # Overlay
    OVERLAY_OPACITY = 0.96


# ── Typography ─────────────────────────────────────────────────────

def get_font(size: int = Sizing.FONT_SIZE_NORMAL, bold: bool = False) -> QFont:
    """Get standard typography with modern fallbacks."""
    font = QFont("Segoe UI Variable Text", size)
    if not font.exactMatch():
        font = QFont("Segoe UI", size)
    font.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def get_heading_font(size: int = 15, bold: bool = True) -> QFont:
    """Get heading font."""
    font = QFont("Segoe UI Variable Display", size)
    if not font.exactMatch():
        font = QFont("Segoe UI", size)
    font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.DemiBold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def get_mono_font(size: int = 11) -> QFont:
    """Get monospace font for keyboard shortcuts & code."""
    font = QFont("Cascadia Code", size)
    if not font.exactMatch():
        font = QFont("Consolas", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


# ── Global Stylesheet for Framed Windows & Dialogs ─────────────────

DIALOG_STYLE = f"""
    QDialog, QWidget#CursorBitePanel {{
        background-color: {CursorBiteColors.BACKGROUND_PRIMARY.name()};
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        border-radius: 12px;
    }}
    QLabel {{
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        background: transparent;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 13px;
    }}
    QLabel[role="heading"] {{
        font-family: "Segoe UI Variable Display", "Segoe UI", sans-serif;
        font-size: 17px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.2px;
    }}
    QLabel[role="hint"] {{
        color: {CursorBiteColors.TEXT_SECONDARY.name()};
        font-size: 12px;
    }}
    QLabel[role="subtle"] {{
        color: {CursorBiteColors.TEXT_TERTIARY.name()};
        font-size: 11px;
    }}
    QGroupBox {{
        color: {CursorBiteColors.TEXT_SECONDARY.name()};
        background-color: {CursorBiteColors.BACKGROUND_SECONDARY.name()};
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        border-radius: 10px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 12px;
        font-weight: 600;
        margin-top: 14px;
        padding: 16px 14px 14px 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        padding: 0 6px;
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
    }}
    QPushButton {{
        background-color: {CursorBiteColors.BACKGROUND_TERTIARY.name()};
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        border-radius: 8px;
        padding: 7px 18px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 12px;
        font-weight: 500;
        min-width: 76px;
    }}
    QPushButton:hover {{
        border-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
        background-color: {CursorBiteColors.SURFACE_HOVER.name()};
    }}
    QPushButton:pressed {{
        background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
        color: #FFFFFF;
    }}
    QPushButton:disabled {{
        color: {CursorBiteColors.TEXT_MUTED.name()};
        border-color: {CursorBiteColors.BORDER_SUBTLE.name()};
    }}
    QPushButton[role="primary"] {{
        background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
        border: 1px solid {CursorBiteColors.ACCENT_SECONDARY.name()};
        color: #FFFFFF;
        font-weight: 600;
    }}
    QPushButton[role="primary"]:hover {{
        background-color: {CursorBiteColors.ACCENT_SECONDARY.name()};
        border-color: #A5B4FC;
    }}
    QPushButton[role="danger"] {{
        border-color: {CursorBiteColors.ERROR.name()};
        color: {CursorBiteColors.ERROR.name()};
    }}
    QPushButton[role="danger"]:hover {{
        background-color: rgba(239, 68, 68, 0.15);
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {CursorBiteColors.BACKGROUND_TERTIARY.name()};
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        border-radius: 8px;
        padding: 6px 10px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 12px;
        selection-background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
        background-color: #1F2338;
    }}
    QComboBox QAbstractItemView {{
        background-color: {CursorBiteColors.BACKGROUND_SECONDARY.name()};
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        selection-background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
        border-radius: 6px;
        outline: none;
        padding: 4px;
    }}
    QCheckBox {{
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        background: transparent;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 13px;
        spacing: 10px;
    }}
    QCheckBox::indicator {{
        width: 17px;
        height: 17px;
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        border-radius: 5px;
        background-color: {CursorBiteColors.BACKGROUND_TERTIARY.name()};
    }}
    QCheckBox::indicator:hover {{
        border-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
    }}
    QCheckBox::indicator:checked {{
        background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
        border-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
    }}
    QTabWidget::pane {{
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        border-radius: 10px;
        background-color: {CursorBiteColors.BACKGROUND_SECONDARY.name()};
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {CursorBiteColors.TEXT_SECONDARY.name()};
        border: 1px solid transparent;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 8px 16px;
        margin-right: 4px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 12px;
        font-weight: 500;
    }}
    QTabBar::tab:selected {{
        background-color: {CursorBiteColors.BACKGROUND_SECONDARY.name()};
        color: #FFFFFF;
        font-weight: 600;
        border-color: {CursorBiteColors.BORDER_CARD.name()};
        border-bottom-color: {CursorBiteColors.BACKGROUND_SECONDARY.name()};
    }}
    QTabBar::tab:hover:!selected {{
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        background-color: rgba(255, 255, 255, 0.03);
    }}
    QTextBrowser, QPlainTextEdit {{
        background-color: {CursorBiteColors.BACKGROUND_TERTIARY.name()};
        color: {CursorBiteColors.TEXT_PRIMARY.name()};
        border: 1px solid {CursorBiteColors.BORDER_CARD.name()};
        border-radius: 8px;
        padding: 8px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 13px;
        line-height: 1.5;
        selection-background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background-color: rgba(255, 255, 255, 0.15);
        border-radius: 4px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {CursorBiteColors.ACCENT_PRIMARY.name()};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QFrame[role="separator"] {{
        background-color: {CursorBiteColors.BORDER_CARD.name()};
        border: none;
        max-height: 1px;
    }}
"""


# ── Dark Palette Factory ───────────────────────────────────────────

def create_palette() -> QPalette:
    """Create a refined dark QPalette for the application."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, CursorBiteColors.BACKGROUND_PRIMARY)
    palette.setColor(QPalette.ColorRole.WindowText, CursorBiteColors.TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Base, CursorBiteColors.BACKGROUND_PRIMARY)
    palette.setColor(QPalette.ColorRole.AlternateBase, CursorBiteColors.BACKGROUND_SECONDARY)
    palette.setColor(QPalette.ColorRole.ToolTipBase, CursorBiteColors.BACKGROUND_TERTIARY)
    palette.setColor(QPalette.ColorRole.ToolTipText, CursorBiteColors.TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Text, CursorBiteColors.TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Button, CursorBiteColors.BACKGROUND_TERTIARY)
    palette.setColor(QPalette.ColorRole.ButtonText, CursorBiteColors.TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.BrightText, CursorBiteColors.ERROR)
    palette.setColor(QPalette.ColorRole.Link, CursorBiteColors.ACCENT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Highlight, CursorBiteColors.ACCENT_PRIMARY)
    palette.setColor(QPalette.ColorRole.HighlightedText, CursorBiteColors.TEXT_PRIMARY)
    return palette
