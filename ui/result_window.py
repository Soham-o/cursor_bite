# Cursor Bite — Modern Result Window Card
# ============================================================
# Floating frosted-glass card that appears near the cursor to show
# action outcomes: translation, AI answers, OCR text, search results,
# or errors.
#
# Design:
#   - Dark compact obsidian acrylic card (14px radius, subtle border glow)
#   - Header: Action badge + live status pill + Pin (📌) + Open in Window (↗) + Close (✕)
#   - Body: Scrollable markdown/rich-text with progressive token streaming & cursor (▌)
#   - Footer: Metadata pills + interactive animated Copy button
#   - Focus-safe: does NOT steal keyboard focus while loading/streaming
#   - Persistent: "Open in Window" detaches to a standalone normal window

from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QLinearGradient,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.overlay_window import OverlayWindow
from ui.theme import (
    CursorBiteColors,
    get_font,
    get_heading_font,
    get_mono_font,
)
from utils.logger import get_logger

logger = get_logger("ui.result_window")


# ── Sizing Constants ───────────────────────────────────────────────

_WIDTH = 460
_PADDING_H = 16
_PADDING_V = 14
_MIN_BODY_H = 50
_MAX_BODY_H = 380
_LOADING_BODY_H = 46
_RADIUS = 14


# ── Stylesheets ────────────────────────────────────────────────────

_BODY_STYLE = """
    QTextBrowser {
        background-color: transparent;
        border: none;
        color: #F1F5F9;
        font-family: "Segoe UI Variable Text", "Segoe UI", -apple-system, sans-serif;
        font-size: 13px;
        line-height: 1.55;
        selection-background-color: #4F46E5;
        selection-color: #FFFFFF;
        padding: 4px 2px;
    }
    QScrollBar:vertical {
        background: transparent;
        width: 6px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background-color: rgba(255, 255, 255, 0.18);
        border-radius: 3px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #818CF8;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: transparent;
    }
"""

_COPY_BTN_DEFAULT = """
    QPushButton {
        background-color: #1E2338;
        color: #F8FAFC;
        border: 1px solid #2F3550;
        border-radius: 7px;
        padding: 4px 14px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 11px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #2D3452;
        border-color: #6366F1;
    }
    QPushButton:pressed {
        background-color: #4F46E5;
        color: #FFFFFF;
    }
    QPushButton:disabled {
        color: #475569;
        border-color: #1E2338;
    }
"""

_COPY_BTN_SUCCESS = """
    QPushButton {
        background-color: #065F46;
        color: #A7F3D0;
        border: 1px solid #10B981;
        border-radius: 7px;
        padding: 4px 14px;
        font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        font-size: 11px;
        font-weight: 600;
    }
"""

_ICON_BTN_STYLE = """
    QPushButton {
        background: transparent;
        color: #64748B;
        border: none;
        border-radius: 5px;
        font-family: "Segoe UI Emoji", "Segoe UI", sans-serif;
        font-size: 12px;
        padding: 3px 6px;
    }
    QPushButton:hover {
        color: #F8FAFC;
        background-color: rgba(255, 255, 255, 0.1);
    }
"""

_PIN_BTN_ACTIVE_STYLE = """
    QPushButton {
        background-color: #312E81;
        color: #C7D2FE;
        border: 1px solid #6366F1;
        border-radius: 5px;
        font-family: "Segoe UI Emoji", "Segoe UI", sans-serif;
        font-size: 12px;
        padding: 3px 6px;
    }
    QPushButton:hover {
        background-color: #3730A3;
        border-color: #818CF8;
    }
"""


# ── Detached Standalone Window ─────────────────────────────────────

class DetachedResultWindow(QWidget):
    """Standalone, persistent normal window for reading results alongside work."""

    def __init__(
        self,
        title: str,
        text: str,
        meta: str = "",
        html: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(f"Cursor Bite — {title}")
        self.setMinimumSize(480, 360)
        self.resize(560, 440)
        self.setStyleSheet("background-color: #0B0D13; color: #F1F5F9;")

        self._text = text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        header_lbl = QLabel(title)
        header_lbl.setFont(get_heading_font(14, bold=True))
        header_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700;")
        header.addWidget(header_lbl)

        header.addStretch(1)
        if meta:
            meta_lbl = QLabel(meta)
            meta_lbl.setFont(get_font(10))
            meta_lbl.setStyleSheet("color: #64748B;")
            header.addWidget(meta_lbl)
        layout.addLayout(header)

        # Body
        body = QTextBrowser()
        body.setStyleSheet(_BODY_STYLE)
        body.setFont(get_font(13))
        body.setOpenExternalLinks(True)
        if html:
            body.setHtml(html)
        else:
            body.setPlainText(text)
        layout.addWidget(body)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch(1)

        copy_btn = QPushButton("Copy")
        copy_btn.setStyleSheet(_COPY_BTN_DEFAULT)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(lambda: self._copy_to_clip(copy_btn))
        footer.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(_COPY_BTN_DEFAULT)
        close_btn.clicked.connect(self.close)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _copy_to_clip(self, btn: QPushButton) -> None:
        from infrastructure.os.clipboard import clipboard
        if clipboard.write(self._text):
            btn.setText("Copied ✓")
            btn.setStyleSheet(_COPY_BTN_SUCCESS)
            QTimer.singleShot(1500, lambda: self._reset_btn(btn))

    @staticmethod
    def _reset_btn(btn: QPushButton) -> None:
        btn.setText("Copy")
        btn.setStyleSheet(_COPY_BTN_DEFAULT)


# ── ResultWindow Class ─────────────────────────────────────────────

class ResultWindow(OverlayWindow):
    """Modern compact floating card displaying action outcomes and token streaming."""

    dismissed = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(
            parent,
            flags=(
                Qt.WindowType.Tool
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            ),
        )

        self._click_outside_to_close = False
        self._is_pinned: bool = False
        self._anchor: Optional[QPoint] = None
        self._action_title: str = "Result"
        self._raw_text: str = ""
        self._stream_text: str = ""
        self._is_streaming: bool = False
        self._html: Optional[str] = None
        self._loading_frame: int = 0
        self._action_color: QColor = CursorBiteColors.ACCENT_PRIMARY

        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(280)
        self._loading_timer.timeout.connect(self._tick_loading)

        self._detached_window: Optional[DetachedResultWindow] = None

        self._build_ui()

        self._copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        self._copy_shortcut.activated.connect(self._on_copy)

        logger.debug("ResultWindow created with modern compact styling.")

    # ── UI Construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        self._layout.setContentsMargins(_PADDING_H, _PADDING_V - 2, _PADDING_H, _PADDING_V - 2)
        self._layout.setSpacing(8)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        # Action Badge Pill
        self._badge = QLabel("• AI")
        self._badge.setFont(get_font(10, bold=True))
        self._badge.setStyleSheet(
            f"QLabel {{ background: {CursorBiteColors.BACKGROUND_SECONDARY.name()}; "
            f"color: {CursorBiteColors.ACCENT_SECONDARY.name()}; border-radius: 4px; padding: 2px 7px; }}"
        )
        header.addWidget(self._badge)

        # Action Title
        self._title = QLabel("Result")
        self._title.setFont(get_heading_font(12, bold=True))
        self._title.setStyleSheet(f"QLabel {{ color: {CursorBiteColors.TEXT_PRIMARY.name()}; font-weight: 700; }}")
        header.addWidget(self._title)

        header.addStretch(1)

        # Live Status Chip
        self._status = QLabel("Working...")
        self._status.setFont(get_font(10))
        self._status.setStyleSheet(f"QLabel {{ color: {CursorBiteColors.TEXT_SECONDARY.name()}; }}")
        header.addWidget(self._status)

        # Pin Button
        self._pin_btn = QPushButton("📌")
        self._pin_btn.setStyleSheet(_ICON_BTN_STYLE)
        self._pin_btn.setToolTip("Pin card to keep open")
        self._pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_btn.clicked.connect(self._toggle_pin)
        header.addWidget(self._pin_btn)

        # Open in Window Button (Detach)
        self._detach_btn = QPushButton("↗")
        self._detach_btn.setStyleSheet(_ICON_BTN_STYLE)
        self._detach_btn.setToolTip("Open in standalone window")
        self._detach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._detach_btn.clicked.connect(self._on_detach)
        header.addWidget(self._detach_btn)

        # Close Button
        self._close_x = QPushButton("✕")
        self._close_x.setStyleSheet(_ICON_BTN_STYLE)
        self._close_x.setToolTip("Close (Esc)")
        self._close_x.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_x.clicked.connect(self.dismiss)
        header.addWidget(self._close_x)

        self._layout.addLayout(header)

        # ── Body (Content Area) ─────────────────────────────────
        self._body = QTextBrowser()
        self._body.setStyleSheet(_BODY_STYLE)
        self._body.setFont(get_font(13))
        self._body.setOpenExternalLinks(True)
        self._body.setFrameShape(QTextBrowser.Shape.NoFrame)
        self._body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._body.viewport().setAutoFillBackground(False)
        self._layout.addWidget(self._body)

        # ── Footer ──────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 2, 0, 0)
        footer.setSpacing(8)

        self._meta_chip = QLabel("")
        self._meta_chip.setFont(get_font(10))
        self._meta_chip.setStyleSheet(f"QLabel {{ color: {CursorBiteColors.TEXT_TERTIARY.name()}; }}")
        footer.addWidget(self._meta_chip)

        footer.addStretch(1)

        # Hint pill
        self._hint = QLabel("Esc to close")
        self._hint.setFont(get_mono_font(9))
        self._hint.setStyleSheet(f"QLabel {{ color: {CursorBiteColors.TEXT_MUTED.name()}; }}")
        footer.addWidget(self._hint)

        # Copy button
        self._copy_button = QPushButton("Copy")
        self._copy_button.setStyleSheet(_COPY_BTN_DEFAULT)
        self._copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_button.clicked.connect(self._on_copy)
        footer.addWidget(self._copy_button)

        self._layout.addLayout(footer)
        self.setFixedWidth(_WIDTH)

    # ── Public API ──────────────────────────────────────────────

    def show_loading(self, action_title: str, cursor_pos: Optional[QPoint] = None) -> None:
        """Display the panel in sleek loading state without stealing focus."""
        if cursor_pos is not None:
            self._anchor = QPoint(cursor_pos)

        self._action_title = action_title
        self._raw_text = ""
        self._stream_text = ""
        self._is_streaming = False
        self._html = None
        self._title.setText(action_title)
        self._badge.setText(f"• {action_title.split()[0]}")
        self._set_status("● Preparing...", CursorBiteColors.ACCENT_SECONDARY)
        self._meta_chip.setText("")
        self._body.setPlainText("")
        self._copy_button.setEnabled(False)
        self._copy_button.setStyleSheet(_COPY_BTN_DEFAULT)
        self._copy_button.setText("Copy")

        self._loading_frame = 0
        self._loading_timer.start()

        self._apply_body_height(_LOADING_BODY_H)

        # Position and display without stealing active keyboard focus
        self._present(activate=False)

    def set_status(self, status_text: str, color: Optional[QColor] = None) -> None:
        """Update live status chip text and color."""
        if not color:
            color = CursorBiteColors.ACCENT_SECONDARY
            if "ready" in status_text.lower():
                color = CursorBiteColors.SUCCESS
            elif "error" in status_text.lower() or "fail" in status_text.lower():
                color = CursorBiteColors.ERROR
            elif "generating" in status_text.lower():
                color = CursorBiteColors.ACCENT_SUBTLE

        self._set_status(status_text, color)

    def append_stream_token(self, token: str) -> None:
        """Progressively render incoming tokens from Ollama/streaming pipeline."""
        if not self._is_streaming:
            self._is_streaming = True
            self._loading_timer.stop()
            self._set_status("● Generating...", CursorBiteColors.ACCENT_SUBTLE)

        self._stream_text += token
        self._raw_text = self._stream_text

        # Display text with typing cursor block
        self._body.setPlainText(self._stream_text + " ▌")

        # Scroll to bottom
        sb = self._body.verticalScrollBar()
        sb.setValue(sb.maximum())

        # Adjust height smoothly up to max
        doc = self._body.document()
        doc.setTextWidth(_WIDTH - (_PADDING_H * 2) - 10)
        needed = int(doc.size().height()) + 8
        self._apply_body_height(max(_MIN_BODY_H, min(needed, _MAX_BODY_H)))

    def finish_stream(self, text: Optional[str] = None, meta: str = "") -> None:
        """Finalize streamed response, remove cursor, and enable copy."""
        self._loading_timer.stop()
        self._is_streaming = False

        if text is not None:
            self._raw_text = text
        else:
            self._raw_text = self._stream_text

        self._body.setPlainText(self._raw_text)
        self._badge.setText(f"✓ {self._action_title.split()[0]}")
        self._set_status("Ready", CursorBiteColors.SUCCESS)
        self._meta_chip.setText(meta)

        self._copy_button.setEnabled(bool(self._raw_text.strip()))
        self._copy_button.setStyleSheet(_COPY_BTN_DEFAULT)
        self._copy_button.setText("Copy")

        self._fit_to_content()

    def show_result(
        self,
        action_title: str,
        text: str,
        meta: str = "",
        html: Optional[str] = None,
    ) -> None:
        """Display successful outcome and activate for user interaction."""
        self._loading_timer.stop()
        self._is_streaming = False
        self._action_title = action_title
        self._raw_text = text or ""
        self._html = html

        self._title.setText(action_title)
        self._badge.setText(f"✓ {action_title.split()[0]}")
        self._set_status("Ready", CursorBiteColors.SUCCESS)
        self._meta_chip.setText(meta)

        if html:
            self._body.setHtml(html)
        else:
            self._body.setPlainText(self._raw_text)

        self._copy_button.setEnabled(bool(self._raw_text.strip()))
        self._copy_button.setStyleSheet(_COPY_BTN_DEFAULT)
        self._copy_button.setText("Copy")

        logger.info(f"Result displayed: {len(self._raw_text)} chars.")
        self._fit_to_content()
        self._present(activate=True)

    def show_error(self, action_title: str, message: str, meta: str = "") -> None:
        """Display formatted failure explanation."""
        self._loading_timer.stop()
        self._is_streaming = False
        self._action_title = action_title
        self._raw_text = message or "Something went wrong."
        self._html = None

        self._title.setText(action_title)
        self._badge.setText(f"✕ {action_title.split()[0]}")
        self._set_status("Notice", CursorBiteColors.ERROR)
        self._meta_chip.setText(meta)
        self._body.setHtml(
            f'<div style="color:#CBD5E1; font-size:13px; line-height:1.5;">'
            f'{self._escape(self._raw_text)}</div>'
        )
        self._copy_button.setEnabled(False)
        self._copy_button.setStyleSheet(_COPY_BTN_DEFAULT)
        self._copy_button.setText("Copy")

        logger.info("Notice displayed in result window.")
        self._fit_to_content()
        self._present(activate=True)

    def dismiss(self, force: bool = False) -> None:
        """Dismiss the answer card, respecting pin state unless forced."""
        if self._is_pinned and not force:
            logger.debug("Dismiss skipped: ResultWindow is pinned.")
            return

        self._loading_timer.stop()
        if force:
            self.hide()
        elif self.is_visible:
            self.hide_with_animation()
        self.dismissed.emit()


    # ── Window Detach & Pin ──────────────────────────────────────

    def _toggle_pin(self) -> None:
        """Toggle pinned state so window stays open on outside focus loss."""
        self._is_pinned = not self._is_pinned
        if self._is_pinned:
            self._pin_btn.setStyleSheet(_PIN_BTN_ACTIVE_STYLE)
            self._pin_btn.setToolTip("Pinned — click to unpin")
            self._hint.setText("📌 Pinned")
            logger.debug("ResultWindow pinned.")
        else:
            self._pin_btn.setStyleSheet(_ICON_BTN_STYLE)
            self._pin_btn.setToolTip("Pin card to keep open")
            self._hint.setText("Esc to close")
            logger.debug("ResultWindow unpinned.")

    def _on_detach(self) -> None:
        """Detach current result into a standalone normal window."""
        if not self._raw_text and not self._html:
            return

        self._detached_window = DetachedResultWindow(
            title=self._action_title,
            text=self._raw_text,
            meta=self._meta_chip.text(),
            html=self._html,
        )
        self._detached_window.show()
        self._detached_window.raise_()
        self._detached_window.activateWindow()

        # Dismiss this floating overlay
        self.dismiss(force=True)
        logger.info("Result card detached to standalone window.")

    # ── Presentation ────────────────────────────────────────────

    def _present(self, activate: bool = True) -> None:
        """Position at the anchor and show."""
        if self._anchor is not None:
            self.move(self.smart_position(self._anchor, self.size()))
            self._clamp_to_screen()

        if not self.is_visible:
            self.show_at_cursor(cursor_pos=None, reposition=False)

        self.raise_()
        if activate:
            self.activateWindow()
            self._body.setFocus()

    def _fit_to_content(self) -> None:
        """Adjust body height smoothly based on content."""
        doc = self._body.document()
        doc.setTextWidth(_WIDTH - (_PADDING_H * 2) - 10)
        needed = int(doc.size().height()) + 8
        self._apply_body_height(max(_MIN_BODY_H, min(needed, _MAX_BODY_H)))

    def _apply_body_height(self, height: int) -> None:
        self._body.setFixedHeight(height)
        self.adjustSize()
        self.setFixedWidth(_WIDTH)

    def _set_status(self, text: str, color: QColor) -> None:
        self._status.setText(text)
        self._status.setStyleSheet(
            f'QLabel {{ color: {color.name()}; font-size: 10px; font-weight: 500; }}'
        )

    def _tick_loading(self) -> None:
        dots = ["●  Analyzing", "●● Analyzing.", "●●● Analyzing..", "●●●● Analyzing..."]
        self._loading_frame = (self._loading_frame + 1) % len(dots)
        self._status.setText(dots[self._loading_frame])

    # ── Copy Action ─────────────────────────────────────────────

    def _on_copy(self) -> None:
        if not self._raw_text.strip():
            return

        from infrastructure.os.clipboard import clipboard

        if clipboard.write(self._raw_text):
            self._copy_button.setText("Copied ✓")
            self._copy_button.setStyleSheet(_COPY_BTN_SUCCESS)
            QTimer.singleShot(1500, self._reset_copy_button)
            logger.info("Result copied to clipboard.")
        else:
            self._copy_button.setText("Failed")
            QTimer.singleShot(1500, self._reset_copy_button)

    def _reset_copy_button(self) -> None:
        self._copy_button.setText("Copy")
        self._copy_button.setStyleSheet(_COPY_BTN_DEFAULT)

    # ── Painting (Obsidian Glass Card) ──────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(
            float(rect.x()), float(rect.y()),
            float(rect.width()), float(rect.height()),
            _RADIUS, _RADIUS,
        )

        # Deep obsidian acrylic glass fill
        painter.fillPath(path, QColor(11, 13, 20, 246))

        # Soft subtle border
        border_pen = QPen(QColor(255, 255, 255, 22), 1.0)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # Top Highlight Line (restrained violet glow)
        highlight_pen = QPen(QColor(99, 102, 241, 70), 1.2)
        painter.setPen(highlight_pen)
        painter.drawLine(
            rect.x() + _RADIUS, rect.y(),
            rect.x() + rect.width() - _RADIUS, rect.y(),
        )

    # ── Keyboard & Escape ───────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss(force=True)
            event.accept()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )


# ── Search Result HTML Formatter ───────────────────────────────────

def format_search_html(results: list[dict]) -> str:
    """Render web search results as modern dark cards with clickable links."""
    blocks = []
    for r in results:
        title = ResultWindow._escape((r.get("title") or "Untitled").strip())
        url = (r.get("url") or "").strip()
        snippet = ResultWindow._escape((r.get("snippet") or "").strip()[:240])

        host = ResultWindow._escape(url.split("//")[-1].split("/")[0]) if url else ""

        link = (
            f'<a href="{url}" style="color:#38BDF8; font-weight:600; text-decoration:none; font-size:13px;">'
            f'{title}</a>'
            if url
            else f'<b style="color:#F1F5F9; font-size:13px;">{title}</b>'
        )

        blocks.append(
            f'<div style="background-color:#141724; border:1px solid #24293D; border-radius:8px; '
            f'padding:10px 12px; margin-bottom:8px;">'
            f'  <div style="margin-bottom:3px;">{link}</div>'
            f'  <div style="color:#64748B; font-size:10px; margin-bottom:4px;">{host}</div>'
            f'  <div style="color:#94A3B8; font-size:12px; line-height:1.45;">{snippet}</div>'
            f'</div>'
        )

    return "".join(blocks)
