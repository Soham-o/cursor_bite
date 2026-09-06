# Cursor Bite — Consent Dialog
# ============================================================
# Shown when the Privacy Gateway returns PrivacyDecision.WARN: the
# action is permitted, but it sends content off the device and the user
# has asked to be told first.
#
# Design decisions that matter here:
#   - Cancel is the default button. Pressing Enter or Escape by reflex
#     must never leak data.
#   - The preview is REDACTED. The dialog exists to warn about sensitive
#     content, so it must not be the thing that displays it in the clear.
#   - "Don't warn me again" writes privacy.external_processing_warning
#     and saves it, so the choice survives a restart. It does NOT turn
#     off sensitive-data protection — that stays a separate switch.
#
# IMPORTANT: The text under review is never logged.

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config.settings import settings
from ui.theme import CursorBiteColors, DIALOG_STYLE, get_font
from utils.logger import get_logger

logger = get_logger("ui.consent_dialog")


# ── Sensitive-type display names ───────────────────────────────────

_TYPE_LABELS = {
    "email": "Email address",
    "phone": "Phone number",
    "api_key": "API key",
    "password": "Password",
    "access_token": "Access token",
    "credit_card": "Credit card number",
    "private_url": "Private URL",
    "credential_pair": "Credentials",
    "aws_key": "AWS key",
    "github_token": "GitHub token",
    "ip_address": "IP address",
    "unknown": "Sensitive data",
}

_PREVIEW_LIMIT = 600
"""Characters of redacted preview to show. Enough to recognise, not to read."""


# ── Consent Dialog ─────────────────────────────────────────────────

class ConsentDialog(QDialog):
    """Asks the user to confirm sending content to an external service."""

    def __init__(
        self,
        action_title: str,
        message: str,
        sensitive_types: Optional[list[str]] = None,
        preview_text: str = "",
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)

        self._suppress_future = False

        self.setWindowTitle("Cursor Bite — Leaving your device")
        self.setStyleSheet(DIALOG_STYLE)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._build_ui(action_title, message, sensitive_types or [], preview_text)

    # ── Construction ────────────────────────────────────────────

    def _build_ui(
        self,
        action_title: str,
        message: str,
        sensitive_types: list[str],
        preview_text: str,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)

        heading = QLabel(f"{action_title} sends data off your device")
        heading.setProperty("role", "heading")
        heading.setFont(get_font(15, bold=True))
        heading.setWordWrap(True)
        layout.addWidget(heading)

        body = QLabel(message or "This action will send data to an external service.")
        body.setWordWrap(True)
        layout.addWidget(body)

        if sensitive_types:
            found = QLabel(
                "Detected in this text: "
                + ", ".join(_TYPE_LABELS.get(t, t.replace("_", " ")) for t in sensitive_types)
            )
            found.setWordWrap(True)
            found.setStyleSheet(
                f'QLabel {{ color: {CursorBiteColors.WARNING.name()}; '
                f'background: transparent; font-family: "Segoe UI"; '
                f'font-size: 12px; font-weight: 600; }}'
            )
            layout.addWidget(found)

        if preview_text:
            preview_label = QLabel("What would be sent (sensitive parts redacted):")
            preview_label.setProperty("role", "hint")
            layout.addWidget(preview_label)

            preview = QTextBrowser()
            preview.setPlainText(self._trim(preview_text))
            preview.setFont(get_font(11))
            preview.setFixedHeight(96)
            preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            layout.addWidget(preview)

        self._suppress_checkbox = QCheckBox("Don't ask me again for external actions")
        layout.addWidget(self._suppress_checkbox)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 4, 0, 0)
        buttons.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self.reject)
        # Safe choice is the default: Enter and Escape both back out.
        cancel.setDefault(True)
        cancel.setAutoDefault(True)
        buttons.addWidget(cancel)

        send = QPushButton("Send anyway")
        send.setProperty("role", "primary")
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setAutoDefault(False)
        send.clicked.connect(self._on_accept)
        buttons.addWidget(send)

        layout.addLayout(buttons)

    # ── Actions ─────────────────────────────────────────────────

    def _on_accept(self) -> None:
        """User consented — persist the suppression choice if made."""
        self._suppress_future = self._suppress_checkbox.isChecked()

        if self._suppress_future:
            settings.set("privacy.external_processing_warning", False)
            settings.save()
            logger.info("External-processing warnings suppressed by user choice.")

        self.accept()

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _trim(text: str) -> str:
        """Cap the preview length."""
        if len(text) <= _PREVIEW_LIMIT:
            return text
        return text[:_PREVIEW_LIMIT].rstrip() + "…"

    # ── Entry Point ─────────────────────────────────────────────

    @staticmethod
    def ask(
        action_title: str,
        message: str,
        sensitive_types: Optional[list[str]] = None,
        text: str = "",
        parent: QWidget = None,
    ) -> bool:
        """Show the dialog and return whether the user consented.

        Args:
            action_title: Human-readable action name.
            message: The consent question from the Privacy Gateway.
            sensitive_types: Detected sensitive-data type names.
            text: The content under review. Redacted before display.

        Returns:
            True if the user chose to continue.
        """
        preview = ""
        if text:
            from infrastructure.privacy.gateway import privacy_gateway
            preview = privacy_gateway.redact_sensitive(text)

        dialog = ConsentDialog(
            action_title=action_title,
            message=message,
            sensitive_types=sensitive_types,
            preview_text=preview,
            parent=parent,
        )
        granted = dialog.exec() == QDialog.DialogCode.Accepted
        logger.info(f"External processing consent: {'granted' if granted else 'declined'}.")
        return granted
