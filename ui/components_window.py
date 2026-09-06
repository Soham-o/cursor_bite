# Cursor Bite — Components Window
# ============================================================
# The real dialog behind the tray's "Check Components" item: what is
# installed, what is missing, and what to do about it.
#
# Probing is done OFF the UI thread. Checking web search performs an
# HTTP request with a 5-second timeout and checking AI talks to Ollama
# over HTTP — doing either on the UI thread would freeze the dialog the
# moment it opened.
#
# "Re-check" invalidates each provider's cached availability first, so a
# user who installs Tesseract or pulls a model while Cursor Bite is
# running does not have to restart it.

from typing import Callable, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import CursorBiteColors, DIALOG_STYLE, get_font
from utils.logger import get_logger
from utils.threading import run_async

logger = get_logger("ui.components_window")


# ── Display order and labels ───────────────────────────────────────

_ROWS = [
    ("text", "Text capture"),
    ("translation", "Translation"),
    ("ocr", "Screen text (OCR)"),
    ("ai", "Local AI"),
    ("search", "Web search"),
    ("privacy_gateway", "Privacy Gateway"),
]


def _status_dot(color: QColor, size: int = 10) -> QPixmap:
    """Draw a small filled circle for the status column."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(0, 0, size, size)
    painter.end()

    return pixmap


# ── Components Window ──────────────────────────────────────────────

class ComponentsWindow(QDialog):
    """Shows the availability of every optional component."""

    # ── Signals ─────────────────────────────────────────────────

    rechecked = pyqtSignal(dict)
    """Emitted with the fresh status dict after a re-check."""

    def __init__(
        self,
        status_provider: Callable[[], dict],
        recheck_provider: Optional[Callable[[], dict]] = None,
        parent: QWidget = None,
    ) -> None:
        """Args:
            status_provider: Returns the current status dict. Called on a
                worker thread, so it must not touch the UI.
            recheck_provider: Same, but drops cached results first.
        """
        super().__init__(parent)

        self._status_provider = status_provider
        self._recheck_provider = recheck_provider or status_provider
        self._rows: dict[str, tuple[QLabel, QLabel, QLabel]] = {}
        self._busy = False

        self.setWindowTitle("Cursor Bite — Components")
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._build_ui()
        self._probe(self._status_provider)

    # ── Construction ────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(12)

        heading = QLabel("Components")
        heading.setProperty("role", "heading")
        heading.setFont(get_font(15, bold=True))
        layout.addWidget(heading)

        intro = QLabel(
            "Cursor Bite works with whatever is installed. Anything missing "
            "below simply stays unavailable — the rest keeps working."
        )
        intro.setProperty("role", "hint")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        grid = QGridLayout()
        grid.setContentsMargins(0, 6, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(2, 1)

        for row, (key, label) in enumerate(_ROWS):
            dot = QLabel()
            dot.setFixedWidth(12)
            grid.addWidget(dot, row, 0, Qt.AlignmentFlag.AlignTop)

            name = QLabel(label)
            name.setFont(get_font(12, bold=True))
            name.setFixedWidth(130)
            grid.addWidget(name, row, 1, Qt.AlignmentFlag.AlignTop)

            detail = QLabel("Checking…")
            detail.setProperty("role", "hint")
            detail.setWordWrap(True)
            grid.addWidget(detail, row, 2, Qt.AlignmentFlag.AlignTop)

            self._rows[key] = (dot, name, detail)

        layout.addLayout(grid)

        self._message = QLabel("")
        self._message.setProperty("role", "subtle")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 4, 0, 0)

        self._recheck_button = QPushButton("Re-check")
        self._recheck_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._recheck_button.setAutoDefault(False)
        self._recheck_button.clicked.connect(self._on_recheck)
        buttons.addWidget(self._recheck_button)

        buttons.addStretch(1)

        close = QPushButton("Close")
        close.setProperty("role", "primary")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)

        layout.addLayout(buttons)

    # ── Probing ─────────────────────────────────────────────────

    def _on_recheck(self) -> None:
        """Drop cached availability and probe again."""
        self._probe(self._recheck_provider, emit=True)

    def _probe(self, provider: Callable[[], dict], emit: bool = False) -> None:
        """Run a status probe on a worker thread."""
        if self._busy:
            return

        self._busy = True
        self._recheck_button.setEnabled(False)
        self._message.setText("Checking components…")

        run_async(
            provider,
            on_result=lambda status: self._apply(status, emit),
            on_error=self._on_error,
            on_finished=self._on_finished,
        )

    def _apply(self, status: object, emit: bool) -> None:
        """Render a status dict into the grid."""
        if not isinstance(status, dict):
            self._message.setText("Component check returned no data.")
            return

        available_count = 0

        for key, (dot, _name, detail) in self._rows.items():
            entry = status.get(key)

            if not isinstance(entry, dict):
                dot.setPixmap(_status_dot(CursorBiteColors.TEXT_TERTIARY))
                detail.setText("Not checked.")
                continue

            is_available = bool(entry.get("available"))
            available_count += int(is_available)

            dot.setPixmap(
                _status_dot(
                    CursorBiteColors.SUCCESS if is_available else CursorBiteColors.ERROR
                )
            )

            provider_name = entry.get("name", "")
            if is_available:
                detail.setText(f"Ready — {provider_name}" if provider_name else "Ready")
                detail.setStyleSheet(
                    f'QLabel {{ color: {CursorBiteColors.TEXT_SECONDARY.name()}; '
                    f'background: transparent; font-family: "Segoe UI"; font-size: 11px; }}'
                )
            else:
                hint = entry.get("hint") or "Unavailable."
                detail.setText(hint)
                detail.setStyleSheet(
                    f'QLabel {{ color: {CursorBiteColors.WARNING.name()}; '
                    f'background: transparent; font-family: "Segoe UI"; font-size: 11px; }}'
                )

        self._message.setText(
            f"{available_count} of {len(self._rows)} components ready."
        )

        if emit:
            self.rechecked.emit(status)

    def _on_error(self, error: Exception) -> None:
        """Report a probe that raised."""
        logger.error(f"Component check failed: {type(error).__name__}")
        self._message.setText("The component check failed. See the log for details.")

    def _on_finished(self) -> None:
        """Re-enable the button once the probe is done."""
        self._busy = False
        self._recheck_button.setEnabled(True)
