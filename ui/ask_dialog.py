# Cursor Bite — Ask AI Dialog
# ============================================================
# The question prompt for the Ask AI action. Every other action is
# self-describing ("translate this", "summarize this"); Ask AI needs one
# more piece of input before the pipeline has anything to work with.
#
# The captured text is shown above the input, truncated and read-only,
# so the user can confirm the AI is being asked about what they think
# it is before spending seconds of local inference on it.
#
# IMPORTANT: Neither the context nor the question is ever logged.

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.theme import DIALOG_STYLE, get_font
from utils.logger import get_logger

logger = get_logger("ui.ask_dialog")


_CONTEXT_LIMIT = 500
"""Characters of context to show. The full text still goes to the model."""


# ── Ask Dialog ─────────────────────────────────────────────────────

class AskDialog(QDialog):
    """Collects a question to ask about the captured text."""

    def __init__(self, context_text: str = "", parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Cursor Bite — Ask AI")
        self.setStyleSheet(DIALOG_STYLE)
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._build_ui(context_text)

    # ── Construction ────────────────────────────────────────────

    def _build_ui(self, context_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        heading = QLabel("Ask about the selected text")
        heading.setProperty("role", "heading")
        heading.setFont(get_font(15, bold=True))
        layout.addWidget(heading)

        if context_text:
            context_label = QLabel(f"Context ({len(context_text)} characters):")
            context_label.setProperty("role", "hint")
            layout.addWidget(context_label)

            context = QTextBrowser()
            context.setPlainText(self._trim(context_text))
            context.setFont(get_font(11))
            context.setFixedHeight(88)
            layout.addWidget(context)

        self._input = QLineEdit()
        self._input.setPlaceholderText("What would you like to know?")
        self._input.setFont(get_font(13))
        self._input.setMinimumHeight(34)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 4, 0, 0)
        buttons.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        self._ask_button = QPushButton("Ask")
        self._ask_button.setProperty("role", "primary")
        self._ask_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ask_button.setEnabled(False)
        self._ask_button.setDefault(True)
        self._ask_button.clicked.connect(self._on_submit)
        buttons.addWidget(self._ask_button)

        layout.addLayout(buttons)

        self._input.setFocus()

    # ── Actions ─────────────────────────────────────────────────

    def _on_text_changed(self, text: str) -> None:
        """Only allow submitting a non-blank question."""
        self._ask_button.setEnabled(bool(text.strip()))

    def _on_submit(self) -> None:
        if self._input.text().strip():
            self.accept()

    # ── Results ─────────────────────────────────────────────────

    def question(self) -> str:
        """The question the user typed."""
        return self._input.text().strip()

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _trim(text: str) -> str:
        """Cap the displayed context."""
        if len(text) <= _CONTEXT_LIMIT:
            return text
        return text[:_CONTEXT_LIMIT].rstrip() + "…"

    # ── Entry Point ─────────────────────────────────────────────

    @staticmethod
    def ask(context_text: str = "", parent: QWidget = None) -> Optional[str]:
        """Show the dialog and return the question, or None if cancelled."""
        dialog = AskDialog(context_text=context_text, parent=parent)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            logger.info("Ask AI cancelled at the question prompt.")
            return None

        question = dialog.question()
        logger.info(f"Ask AI question entered ({len(question)} characters).")
        return question or None
