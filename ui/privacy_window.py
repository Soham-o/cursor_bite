# Cursor Bite — Privacy Dashboard
# ============================================================
# The real dialog behind the tray's "Privacy…" item.
#
# Its job is to answer one question honestly: right now, can anything
# I select leave this machine? Everything else on the panel supports
# that answer.
#
# Unlike Settings, the two switches here apply IMMEDIATELY and are
# saved on the spot. A privacy control that needs a Save button is a
# privacy control people forget to press.
#
# IMPORTANT: This window displays policy state only. It never shows,
# stores, or logs captured content.

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.settings import settings
from infrastructure.privacy.gateway import privacy_gateway
from ui.theme import CursorBiteColors, DIALOG_STYLE, get_font
from utils.logger import get_logger

logger = get_logger("ui.privacy_window")


# ── Policy rows ────────────────────────────────────────────────────

_POLICY_ROWS = [
    ("offline_mode", "Offline mode", "Nothing leaves the device, for any action."),
    ("no_data_retention", "No data retention", "Captured text is never kept after use."),
    ("clipboard_protection", "Clipboard protection", "Your clipboard is restored after every capture."),
    ("screenshot_retention", "Screenshot retention", "Captured images are written to disk."),
    ("sensitive_data_protection", "Sensitive data protection", "External actions are blocked when secrets are detected."),
    ("external_processing_warning", "External warning", "You are asked before anything leaves the device."),
]

_GOOD_WHEN_OFF = {"screenshot_retention"}
"""Policies where OFF is the privacy-preserving state.

Every other row reads "on = more protected". Screenshot retention is the
exception: keeping images on disk is the less private choice, so it must
not be painted green when enabled.
"""


def _dot(color: QColor, size: int = 9) -> QPixmap:
    """Draw a small filled circle."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(0, 0, size, size)
    painter.end()

    return pixmap


# ── Privacy Dashboard ──────────────────────────────────────────────

class PrivacyDashboard(QDialog):
    """Shows and controls the current privacy posture."""

    # ── Signals ─────────────────────────────────────────────────

    privacy_changed = pyqtSignal()
    """Emitted when a policy is toggled, so the tray can resync."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._loading = True

        self.setWindowTitle("Cursor Bite — Privacy")
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._policy_labels: dict[str, tuple[QLabel, QLabel]] = {}

        self._build_ui()
        self._refresh()

        self._loading = False

    # ── Construction ────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(12)

        heading = QLabel("Privacy")
        heading.setProperty("role", "heading")
        heading.setFont(get_font(15, bold=True))
        layout.addWidget(heading)

        # ── Posture banner ──
        self._posture = QLabel("")
        self._posture.setWordWrap(True)
        self._posture.setFont(get_font(12, bold=True))
        layout.addWidget(self._posture)

        self._posture_detail = QLabel("")
        self._posture_detail.setProperty("role", "hint")
        self._posture_detail.setWordWrap(True)
        layout.addWidget(self._posture_detail)

        layout.addWidget(self._separator())

        # ── Live controls ──
        controls = QLabel("Controls")
        controls.setFont(get_font(12, bold=True))
        layout.addWidget(controls)

        self._offline_mode = QCheckBox("Offline mode — block everything that leaves the device")
        self._offline_mode.toggled.connect(self._on_offline_toggled)
        layout.addWidget(self._offline_mode)

        self._sensitive_protection = QCheckBox(
            "Block external actions when sensitive data is detected"
        )
        self._sensitive_protection.toggled.connect(self._on_sensitive_toggled)
        layout.addWidget(self._sensitive_protection)

        applied = QLabel("These two apply immediately and are saved straight away.")
        applied.setProperty("role", "subtle")
        layout.addWidget(applied)

        layout.addWidget(self._separator())

        # ── Policy state ──
        state = QLabel("Current policies")
        state.setFont(get_font(12, bold=True))
        layout.addWidget(state)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        grid.setColumnStretch(2, 1)

        for row, (key, label, description) in enumerate(_POLICY_ROWS):
            dot = QLabel()
            dot.setFixedWidth(11)
            grid.addWidget(dot, row, 0, Qt.AlignmentFlag.AlignTop)

            name = QLabel(label)
            name.setFixedWidth(160)
            grid.addWidget(name, row, 1, Qt.AlignmentFlag.AlignTop)

            detail = QLabel(description)
            detail.setProperty("role", "hint")
            detail.setWordWrap(True)
            grid.addWidget(detail, row, 2, Qt.AlignmentFlag.AlignTop)

            self._policy_labels[key] = (dot, detail)

        layout.addLayout(grid)

        layout.addWidget(self._separator())

        # ── Guarantees ──
        guarantees = QLabel("What Cursor Bite never does")
        guarantees.setFont(get_font(12, bold=True))
        layout.addWidget(guarantees)

        never = QLabel(
            "•  No telemetry, analytics, or crash reporting\n"
            "•  No cloud AI — translation and AI run on this machine\n"
            "•  No clipboard history is kept\n"
            "•  No captured text, prompt, or result is ever written to the log"
        )
        never.setProperty("role", "hint")
        layout.addWidget(never)

        layout.addWidget(self._separator())

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 2, 0, 0)

        clear = QPushButton("Clear cached data")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.setAutoDefault(False)
        clear.clicked.connect(self._on_clear_cache)
        buttons.addWidget(clear)

        self._message = QLabel("")
        self._message.setProperty("role", "subtle")
        buttons.addWidget(self._message)

        buttons.addStretch(1)

        close = QPushButton("Close")
        close.setProperty("role", "primary")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setDefault(True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)

        layout.addLayout(buttons)

    @staticmethod
    def _separator() -> QFrame:
        """A one-pixel divider line."""
        line = QFrame()
        line.setProperty("role", "separator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        return line

    # ── State ───────────────────────────────────────────────────

    def refresh(self) -> None:
        """Re-read the policy state after a change made elsewhere.

        The tray has its own offline-mode toggle, so this window can go
        stale while it is open.
        """
        self._refresh()

    def _refresh(self) -> None:
        """Re-read the policy summary and repaint every indicator."""
        # Setting a checkbox emits toggled(), which is indistinguishable
        # from a click. Suppressing the handlers here keeps a programmatic
        # refresh from being written back as if the user had done it.
        was_loading = self._loading
        self._loading = True
        try:
            summary = privacy_gateway.policies.get_policy_summary()

            self._offline_mode.setChecked(bool(summary["offline_mode"]))
            self._sensitive_protection.setChecked(
                bool(summary["sensitive_data_protection"])
            )

            for key, (dot, _detail) in self._policy_labels.items():
                enabled = bool(summary.get(key))
                protective = (not enabled) if key in _GOOD_WHEN_OFF else enabled
                dot.setPixmap(
                    _dot(
                        CursorBiteColors.SUCCESS if protective
                        else CursorBiteColors.WARNING
                    )
                )

            self._refresh_posture(summary)
        finally:
            self._loading = was_loading

    def _refresh_posture(self, summary: dict) -> None:
        """Update the headline answer to 'can anything leave right now?'."""
        if summary["offline_mode"]:
            self._posture.setText("Nothing can leave this device")
            self._posture.setStyleSheet(
                f'QLabel {{ color: {CursorBiteColors.SUCCESS.name()}; '
                f'background: transparent; font-family: "Segoe UI"; '
                f'font-size: 12px; font-weight: 600; }}'
            )
            self._posture_detail.setText(
                "Offline mode is on. Web search is blocked. Translation, OCR, and "
                "AI keep working — they run locally."
            )
            return

        self._posture.setText("Only Search Web can leave this device")
        self._posture.setStyleSheet(
            f'QLabel {{ color: {CursorBiteColors.INFO.name()}; '
            f'background: transparent; font-family: "Segoe UI"; '
            f'font-size: 12px; font-weight: 600; }}'
        )

        guard = []
        if summary["sensitive_data_protection"]:
            guard.append("blocked outright when sensitive data is detected")
        if summary["external_processing_warning"]:
            guard.append("confirmed with you first")
        detail = (
            "Search Web sends your query to DuckDuckGo; it is "
            + " and ".join(guard)
            + "."
            if guard
            else "Search Web sends your query to DuckDuckGo without further checks."
        )
        self._posture_detail.setText(
            f"{detail} Translation, OCR, and AI run entirely on this machine."
        )

    # ── Actions ─────────────────────────────────────────────────

    def _on_offline_toggled(self, checked: bool) -> None:
        """Apply and persist offline mode immediately."""
        if self._loading:
            return
        self._persist("privacy.offline_mode", checked, "Offline mode")

    def _on_sensitive_toggled(self, checked: bool) -> None:
        """Apply and persist sensitive-data protection immediately."""
        if self._loading:
            return
        self._persist(
            "privacy.sensitive_data_protection", checked, "Sensitive data protection"
        )

    def _persist(self, key: str, value: bool, label: str) -> None:
        """Write one policy value and refresh the display."""
        settings.set(key, value)

        try:
            settings.save()
        except OSError as e:
            logger.error(f"Failed to persist {key}: {e}")
            self._message.setText(f"{label} changed for this session only — save failed.")
            self._refresh()
            self.privacy_changed.emit()
            return

        logger.info(f"Privacy policy updated: {key}={value}")
        self._message.setText(f"{label} {'on' if value else 'off'}.")
        self._refresh()
        self.privacy_changed.emit()

    def _on_clear_cache(self) -> None:
        """Drop everything held in the in-memory cache."""
        from infrastructure.storage.cache import cache

        count = cache.clear()
        self._message.setText(
            "Cache was already empty." if count == 0
            else f"Cleared {count} cached {'entry' if count == 1 else 'entries'}."
        )
