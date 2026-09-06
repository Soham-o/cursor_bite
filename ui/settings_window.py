# Cursor Bite — Settings Window
# ============================================================
# The real Settings window behind the tray's "Settings…" item.
#
# Structure mirrors config.json: one tab per top-level section, so
# what you see maps one-to-one onto what gets written.
#
# Two behaviours worth calling out:
#   - The hotkey field is validated with the SAME parser the listener
#     uses (parse_hotkey). A combination the listener can't register is
#     rejected here rather than silently failing at startup.
#   - "Start with Windows" reads and writes the registry, not just
#     config.json. See infrastructure/os/startup.py for why.
#
# Nothing is applied until Save is pressed. Cancel discards everything.

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings import settings
from infrastructure.os import startup
from infrastructure.os.hotkey_listener import parse_hotkey
from ui.theme import CursorBiteColors, DIALOG_STYLE, get_font
from utils.logger import get_logger

logger = get_logger("ui.settings_window")


# ── Language choices ───────────────────────────────────────────────

_COMMON_LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("ru", "Russian"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("tr", "Turkish"),
]

_POSITION_BEHAVIORS = [
    ("smart", "Smart — avoid screen edges"),
    ("cursor", "At the cursor"),
    ("center", "Centre of the screen"),
]


# ── Settings Window ────────────────────────────────────────────────

class SettingsWindow(QDialog):
    """Edits every value in config.json."""

    # ── Signals ─────────────────────────────────────────────────

    settings_saved = pyqtSignal()
    """Emitted after settings are written. The app re-reads what it needs."""

    hotkey_changed = pyqtSignal(str)
    """Emitted with the new hotkey string when it changed on save."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Cursor Bite — Settings")
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumSize(520, 520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._original_hotkey = settings.hotkey_main

        self._build_ui()
        self._load_values()

    # ── Construction ────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        heading = QLabel("Settings")
        heading.setProperty("role", "heading")
        heading.setFont(get_font(15, bold=True))
        layout.addWidget(heading)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_translation_tab(), "Translation")
        tabs.addTab(self._build_ai_tab(), "AI")
        tabs.addTab(self._build_privacy_tab(), "Privacy")
        tabs.addTab(self._build_appearance_tab(), "Appearance")
        layout.addWidget(tabs, 1)

        self._message = QLabel("")
        self._message.setProperty("role", "hint")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)

        save = QPushButton("Save")
        save.setProperty("role", "primary")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setDefault(True)
        save.clicked.connect(self._on_save)
        buttons.addWidget(save)

        layout.addLayout(buttons)

    def _build_general_tab(self) -> QWidget:
        page, form = self._new_form_page()

        self._enabled = QCheckBox("Cursor Bite is active")
        form.addRow("", self._enabled)

        self._hotkey = QLineEdit()
        self._hotkey.setPlaceholderText("Ctrl+Alt+B")
        self._hotkey.textChanged.connect(self._validate_hotkey)
        form.addRow("Hotkey", self._hotkey)

        self._hotkey_hint = QLabel(
            "Modifiers: Ctrl, Alt, Shift, Win. Key: A–Z, 0–9, F1–F12, "
            "Space, Enter, Escape, Tab, Backspace."
        )
        self._hotkey_hint.setProperty("role", "subtle")
        self._hotkey_hint.setWordWrap(True)
        form.addRow("", self._hotkey_hint)

        self._start_with_windows = QCheckBox("Start Cursor Bite when Windows starts")
        form.addRow("", self._start_with_windows)

        self._animations = QCheckBox("Animate the menu and panels")
        form.addRow("", self._animations)

        return page

    def _build_translation_tab(self) -> QWidget:
        page, form = self._new_form_page()

        self._target_language = QComboBox()
        for code, label in self._language_choices():
            self._target_language.addItem(f"{label}  ({code})", code)
        form.addRow("Translate into", self._target_language)

        self._auto_detect = QCheckBox("Detect the source language automatically")
        form.addRow("", self._auto_detect)

        self._offline_only = QCheckBox("Only ever use offline translation")
        form.addRow("", self._offline_only)

        note = QLabel(
            "Translation runs entirely on this machine through Argos Translate. "
            "Each language pair needs its pack installed — see SETUP_GUIDE.md."
        )
        note.setProperty("role", "subtle")
        note.setWordWrap(True)
        form.addRow("", note)

        return page

    def _build_ai_tab(self) -> QWidget:
        page, form = self._new_form_page()

        self._ai_enabled = QCheckBox("Enable AI features (Explain, Summarize, Rewrite, Ask)")
        form.addRow("", self._ai_enabled)

        self._ai_model = QComboBox()
        self._ai_model.setEditable(True)
        form.addRow("Model", self._ai_model)

        self._ai_temperature = QDoubleSpinBox()
        self._ai_temperature.setRange(0.0, 2.0)
        self._ai_temperature.setSingleStep(0.1)
        self._ai_temperature.setDecimals(2)
        form.addRow("Temperature", self._ai_temperature)

        self._ai_timeout = QSpinBox()
        self._ai_timeout.setRange(5, 600)
        self._ai_timeout.setSuffix(" s")
        form.addRow("Timeout", self._ai_timeout)

        note = QLabel(
            "AI runs locally through Ollama — nothing is sent to a cloud service. "
            "Larger models need a longer timeout."
        )
        note.setProperty("role", "subtle")
        note.setWordWrap(True)
        form.addRow("", note)

        return page

    def _build_privacy_tab(self) -> QWidget:
        page, form = self._new_form_page()

        self._offline_mode = QCheckBox("Offline mode — block everything that leaves the device")
        form.addRow("", self._offline_mode)

        self._no_retention = QCheckBox("Never retain captured text")
        form.addRow("", self._no_retention)

        self._clipboard_protection = QCheckBox("Restore the clipboard after reading a selection")
        form.addRow("", self._clipboard_protection)

        self._screenshot_retention = QCheckBox("Keep captured screenshots on disk")
        form.addRow("", self._screenshot_retention)

        self._sensitive_protection = QCheckBox(
            "Block external actions when sensitive data is detected"
        )
        form.addRow("", self._sensitive_protection)

        self._external_warning = QCheckBox("Ask before any action leaves the device")
        form.addRow("", self._external_warning)

        note = QLabel(
            "Local processing is never blocked, whatever these say — the Privacy "
            "Gateway only governs data that would leave your machine."
        )
        note.setProperty("role", "subtle")
        note.setWordWrap(True)
        form.addRow("", note)

        return page

    def _build_appearance_tab(self) -> QWidget:
        page, form = self._new_form_page()

        self._menu_size = QSpinBox()
        self._menu_size.setRange(120, 320)
        self._menu_size.setSuffix(" px")
        form.addRow("Menu size", self._menu_size)

        self._animation_speed = QSpinBox()
        self._animation_speed.setRange(0, 1000)
        self._animation_speed.setSuffix(" ms")
        form.addRow("Animation speed", self._animation_speed)

        self._opacity = QDoubleSpinBox()
        self._opacity.setRange(0.5, 1.0)
        self._opacity.setSingleStep(0.05)
        self._opacity.setDecimals(2)
        form.addRow("Opacity", self._opacity)

        self._position_behavior = QComboBox()
        for value, label in _POSITION_BEHAVIORS:
            self._position_behavior.addItem(label, value)
        form.addRow("Menu position", self._position_behavior)

        note = QLabel("Menu size takes effect the next time the menu opens.")
        note.setProperty("role", "subtle")
        note.setWordWrap(True)
        form.addRow("", note)

        return page

    @staticmethod
    def _new_form_page() -> tuple[QWidget, QFormLayout]:
        """Create a tab page with a consistent form layout."""
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        return page, form

    # ── Loading ─────────────────────────────────────────────────

    def _load_values(self) -> None:
        """Populate every control from the current settings."""
        # General
        self._enabled.setChecked(settings.general_enabled)
        self._hotkey.setText(settings.hotkey_main)
        self._animations.setChecked(settings.general_animations)

        # The registry wins over config.json — the user may have removed
        # the entry outside Cursor Bite.
        self._start_with_windows.setChecked(
            startup.is_registered() or settings.general_start_with_windows
        )

        # Translation
        self._select_by_data(self._target_language, settings.translation_default_target)
        self._auto_detect.setChecked(settings.translation_auto_detect)
        self._offline_only.setChecked(settings.translation_offline_only)

        # AI
        self._ai_enabled.setChecked(settings.ai_enabled)
        self._populate_models(settings.ai_model)
        self._ai_temperature.setValue(settings.ai_temperature)
        self._ai_timeout.setValue(settings.ai_timeout_seconds)

        # Privacy
        self._offline_mode.setChecked(settings.privacy_offline_mode)
        self._no_retention.setChecked(settings.privacy_no_data_retention)
        self._clipboard_protection.setChecked(settings.privacy_clipboard_protection)
        self._screenshot_retention.setChecked(settings.privacy_screenshot_retention)
        self._sensitive_protection.setChecked(settings.privacy_sensitive_data_protection)
        self._external_warning.setChecked(settings.privacy_external_warning)

        # Appearance
        self._menu_size.setValue(settings.ui_menu_size)
        self._animation_speed.setValue(settings.ui_animation_speed)
        self._opacity.setValue(settings.ui_opacity)
        self._select_by_data(self._position_behavior, settings.ui_position_behavior)

        self._validate_hotkey(self._hotkey.text())

    def _language_choices(self) -> list[tuple[str, str]]:
        """Common languages, with anything installed listed first.

        Installed packs are what actually work, so they lead. The rest
        stay selectable — a user may configure a target before installing
        its pack.
        """
        names = dict(_COMMON_LANGUAGES)
        installed: list[str] = []

        try:
            from infrastructure.translation.argos import argos_translator
            if argos_translator.is_available():
                installed = argos_translator.supported_languages()
        except Exception as e:
            logger.debug(f"Could not list installed languages: {e}")

        ordered = [(code, f"{names.get(code, code.upper())} — installed") for code in installed]
        ordered += [(code, label) for code, label in _COMMON_LANGUAGES if code not in installed]
        return ordered

    def _populate_models(self, configured: str) -> None:
        """Offer the installed Ollama models, keeping the configured one."""
        self._ai_model.clear()

        models: list[str] = []
        try:
            from infrastructure.ai.ollama import ollama_ai
            if ollama_ai.is_available():
                models = ollama_ai.list_models()
        except Exception as e:
            logger.debug(f"Could not list Ollama models: {e}")

        for model in models:
            self._ai_model.addItem(model)

        if configured and configured not in models:
            self._ai_model.addItem(configured)

        self._ai_model.setCurrentText(configured or (models[0] if models else ""))

        if not models:
            self._ai_model.lineEdit().setPlaceholderText("llama3.2")

    @staticmethod
    def _select_by_data(combo: QComboBox, value: str) -> None:
        """Select the entry whose userData matches `value`."""
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif combo.count():
            combo.setCurrentIndex(0)

    # ── Validation ──────────────────────────────────────────────

    def _validate_hotkey(self, text: str) -> None:
        """Colour the hotkey field by whether the listener can register it."""
        valid = parse_hotkey(text.strip()) is not None

        border = (
            CursorBiteColors.BORDER_SUBTLE.name()
            if valid
            else CursorBiteColors.ERROR.name()
        )
        self._hotkey.setStyleSheet(
            f"QLineEdit {{ background: {CursorBiteColors.BACKGROUND_TERTIARY.name()}; "
            f"color: {CursorBiteColors.TEXT_PRIMARY.name()}; "
            f"border: 1px solid {border}; border-radius: 6px; padding: 5px 8px; "
            f'font-family: "Segoe UI"; font-size: 12px; }}'
        )
        return None

    # ── Saving ──────────────────────────────────────────────────

    def _on_save(self) -> None:
        """Validate, write config.json, and report what happened."""
        hotkey = self._hotkey.text().strip()

        if parse_hotkey(hotkey) is None:
            self._show_message(
                "That hotkey can't be registered. Use something like Ctrl+Alt+B.",
                error=True,
            )
            return

        settings.set("hotkey.main", hotkey)

        settings.set("general.enabled", self._enabled.isChecked())
        settings.set("general.animations", self._animations.isChecked())
        settings.set("general.start_with_windows", self._start_with_windows.isChecked())

        settings.set("translation.default_target_language", self._target_language.currentData())
        settings.set("translation.auto_detect_source", self._auto_detect.isChecked())
        settings.set("translation.offline_only", self._offline_only.isChecked())

        settings.set("ai.enabled", self._ai_enabled.isChecked())
        settings.set("ai.model", self._ai_model.currentText().strip())
        settings.set("ai.temperature", round(self._ai_temperature.value(), 2))
        settings.set("ai.timeout_seconds", self._ai_timeout.value())

        settings.set("privacy.offline_mode", self._offline_mode.isChecked())
        settings.set("privacy.no_data_retention", self._no_retention.isChecked())
        settings.set("privacy.clipboard_protection", self._clipboard_protection.isChecked())
        settings.set("privacy.screenshot_retention", self._screenshot_retention.isChecked())
        settings.set("privacy.sensitive_data_protection", self._sensitive_protection.isChecked())
        settings.set("privacy.external_processing_warning", self._external_warning.isChecked())

        settings.set("ui.menu_size", self._menu_size.value())
        settings.set("ui.animation_speed", self._animation_speed.value())
        settings.set("ui.opacity", round(self._opacity.value(), 2))
        settings.set("ui.position_behavior", self._position_behavior.currentData())

        try:
            settings.save()
        except OSError as e:
            logger.error(f"Failed to write config.json: {e}")
            self._show_message(
                "Settings could not be written to config.json. "
                "Check that the file is writable.",
                error=True,
            )
            return

        # The registry write can fail independently of config.json, so it
        # is reported separately rather than failing the whole save.
        startup_ok = startup.apply(self._start_with_windows.isChecked())

        logger.info("Settings saved.")

        if hotkey != self._original_hotkey:
            self.hotkey_changed.emit(hotkey)

        self.settings_saved.emit()

        if not startup_ok:
            self._show_message(
                "Settings saved, but the Windows startup entry could not be "
                "updated. You can add Cursor Bite manually in Task Manager → Startup.",
                error=True,
            )
            return

        self.accept()

    def _show_message(self, text: str, error: bool = False) -> None:
        """Show an inline message under the tabs."""
        color = (
            CursorBiteColors.ERROR.name() if error else CursorBiteColors.SUCCESS.name()
        )
        self._message.setStyleSheet(
            f'QLabel {{ color: {color}; background: transparent; '
            f'font-family: "Segoe UI"; font-size: 11px; }}'
        )
        self._message.setText(text)
