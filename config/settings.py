# Cursor Bite — Runtime Settings
# ============================================================
# Loads configuration from config.json and falls back to defaults.
# Provides typed access to all settings.

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("cursor_bite.config.settings")

from config.defaults import (  # noqa: E402
    HOTKEY_MAIN,
    TRANSLATION_DEFAULT_TARGET,
    TRANSLATION_AUTO_DETECT_SOURCE,
    TRANSLATION_OFFLINE_ONLY,
    AI_ENABLED,
    AI_MODEL,
    AI_TEMPERATURE,
    AI_TIMEOUT_SECONDS,
    PRIVACY_OFFLINE_MODE,
    PRIVACY_NO_DATA_RETENTION,
    PRIVACY_CLIPBOARD_PROTECTION,
    PRIVACY_SCREENSHOT_RETENTION,
    PRIVACY_SENSITIVE_DATA_PROTECTION,
    PRIVACY_EXTERNAL_PROCESSING_WARNING,
    UI_MENU_SIZE,
    UI_ANIMATION_SPEED,
    UI_OPACITY,
    UI_POSITION_BEHAVIOR,
    GENERAL_START_WITH_WINDOWS,
    GENERAL_ENABLED,
    GENERAL_ANIMATIONS,
)


class Settings:
    """Singleton application settings.

    Loads from config.json (if present) and falls back to defaults
    defined in config/defaults.py.
    """

    _instance: Optional["Settings"] = None

    def __new__(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self) -> None:
        if self._loaded:
            return
        self._config: dict[str, Any] = {}
        self._load()
        self._loaded = True

    # ── Loading ──────────────────────────────────────────────────

    def _load(self) -> None:
        """Load config from config.json, falling back to defaults."""
        config_path = self._find_config()
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load config.json: {e}. Using defaults.")
                self._config = {}
        else:
            logger.info("No config.json found. Using defaults.")
            self._config = {}

    def _find_config(self) -> Optional[str]:
        """Find config.json in the application directory."""
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json"),
            "config.json",
            os.path.join(os.path.expanduser("~"), ".cursor_bite", "config.json"),
        ]
        for path in candidates:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
        return None

    def _get(self, key: str, default: Any) -> Any:
        """Get a nested config value by dot-separated key."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    # ── Hotkey ───────────────────────────────────────────────────

    @property
    def hotkey_main(self) -> str:
        return self._get("hotkey.main", HOTKEY_MAIN)

    # ── Translation ──────────────────────────────────────────────

    @property
    def translation_default_target(self) -> str:
        return self._get("translation.default_target_language", TRANSLATION_DEFAULT_TARGET)

    @property
    def translation_auto_detect(self) -> bool:
        return self._get("translation.auto_detect_source", TRANSLATION_AUTO_DETECT_SOURCE)

    @property
    def translation_offline_only(self) -> bool:
        return self._get("translation.offline_only", TRANSLATION_OFFLINE_ONLY)

    # ── AI ───────────────────────────────────────────────────────

    @property
    def ai_enabled(self) -> bool:
        return self._get("ai.enabled", AI_ENABLED)

    @property
    def ai_model(self) -> str:
        return self._get("ai.model", AI_MODEL)

    @property
    def ai_temperature(self) -> float:
        return float(self._get("ai.temperature", AI_TEMPERATURE))

    @property
    def ai_timeout_seconds(self) -> int:
        return int(self._get("ai.timeout_seconds", AI_TIMEOUT_SECONDS))

    # ── Privacy ──────────────────────────────────────────────────

    @property
    def privacy_offline_mode(self) -> bool:
        return self._get("privacy.offline_mode", PRIVACY_OFFLINE_MODE)

    @property
    def privacy_no_data_retention(self) -> bool:
        return self._get("privacy.no_data_retention", PRIVACY_NO_DATA_RETENTION)

    @property
    def privacy_clipboard_protection(self) -> bool:
        return self._get("privacy.clipboard_protection", PRIVACY_CLIPBOARD_PROTECTION)

    @property
    def privacy_screenshot_retention(self) -> bool:
        return self._get("privacy.screenshot_retention", PRIVACY_SCREENSHOT_RETENTION)

    @property
    def privacy_sensitive_data_protection(self) -> bool:
        return self._get("privacy.sensitive_data_protection", PRIVACY_SENSITIVE_DATA_PROTECTION)

    @property
    def privacy_external_warning(self) -> bool:
        return self._get("privacy.external_processing_warning", PRIVACY_EXTERNAL_PROCESSING_WARNING)

    # ── UI ───────────────────────────────────────────────────────

    @property
    def ui_menu_size(self) -> int:
        return int(self._get("ui.menu_size", UI_MENU_SIZE))

    @property
    def ui_animation_speed(self) -> int:
        return int(self._get("ui.animation_speed", UI_ANIMATION_SPEED))

    @property
    def ui_opacity(self) -> float:
        return float(self._get("ui.opacity", UI_OPACITY))

    @property
    def ui_position_behavior(self) -> str:
        return self._get("ui.position_behavior", UI_POSITION_BEHAVIOR)

    # ── General ──────────────────────────────────────────────────

    @property
    def general_start_with_windows(self) -> bool:
        return self._get("general.start_with_windows", GENERAL_START_WITH_WINDOWS)

    @property
    def general_enabled(self) -> bool:
        return self._get("general.enabled", GENERAL_ENABLED)

    @property
    def general_animations(self) -> bool:
        return self._get("general.animations", GENERAL_ANIMATIONS)

    # ── Persistence ──────────────────────────────────────────────

    def save(self, path: Optional[str] = None) -> None:
        """Save current settings to config.json."""
        if path is None:
            path = self._find_config() or "config.json"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def set(self, key: str, value: Any) -> None:
        """Set a nested config value by dot-separated key."""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value


# ── Module-level singleton ──────────────────────────────────────────

settings = Settings()
"""Global settings instance. Import and use directly:

    from config.settings import settings
    print(settings.hotkey_main)
"""



