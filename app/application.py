# Cursor Bite — Application
# ============================================================
# Application lifecycle manager: process startup, the tray, the global
# hotkey, and the windows the tray opens.
#
# Startup sequence:
#   1. Structured logging (no user content is ever logged)
#   2. QApplication (exactly once)
#   3. Controller (owns the menu, the pipeline, and the result panel)
#   4. Native event filter for WM_HOTKEY (exactly once)
#   5. System tray, synced to the saved settings
#   6. Global hotkey via RegisterHotKey
#   7. Event loop
#
# WHAT STARTUP DOES NOT TOUCH:
#   OCR, translation, AI, web search, the clipboard, and the network are
#   all resolved lazily by the pipeline on first use. Launching Cursor
#   Bite performs ZERO network requests, reads ZERO clipboard content,
#   and loads ZERO optional components — a fresh install with none of
#   them present starts and runs exactly the same.
#
# The tray reports intent; this class owns the windows. Nothing here
# knows how an action is carried out — that is the controller's job.

import os
import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication, QDialog

from app.events import event_bus, AppEvent
from config.settings import settings
from ui.tray import SystemTray
from utils.logger import setup_logging, get_logger, silence_third_party_logs

logger = get_logger("app.application")


# ── Application ────────────────────────────────────────────────────

class Application:
    """Cursor Bite application lifecycle manager.

    Guarantees:
    - QApplication created exactly once
    - Native hotkey filter installed exactly once, removed on shutdown
    - Hotkey unregistered on shutdown
    - One instance of each window, reused rather than duplicated
    - No optional component initialized at startup
    """

    def __init__(self) -> None:
        """Initialize state only — does not start the app."""
        self._app: Optional[QApplication] = None
        self._tray: Optional[SystemTray] = None
        self._controller = None

        self._hotkey_listener = None
        self._native_filter = None
        self._native_filter_installed = False

        self._settings_window: Optional[QDialog] = None
        self._privacy_window: Optional[QDialog] = None
        self._components_window: Optional[QDialog] = None

        self._running = False

    # ── Initialization ──────────────────────────────────────────

    def initialize(self) -> bool:
        """Initialize every subsystem needed to run.

        Returns:
            True if initialization succeeded.
        """
        logger.info("=" * 60)
        logger.info("Cursor Bite — Initializing")
        logger.info("=" * 60)

        # 1. Structured logging (no user content ever logged)
        log_dir = os.path.expanduser("~/.cursor_bite")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "cursor_bite.log")
        setup_logging(log_file=log_file)
        silence_third_party_logs()
        logger.info("Logging initialized.")

        # 2. QApplication (exactly once)
        if self._app is not None:
            logger.error("QApplication already created — refusing to create second instance.")
            return False

        self._app = QApplication(sys.argv)
        self._app.setApplicationName("Cursor Bite")
        self._app.setApplicationVersion("1.0.0")
        self._app.setOrganizationName("Cursor Bite")

        # Without this, closing the Settings dialog would be "the last
        # window closed" and Qt would quit the whole app. A tray app has
        # to outlive its windows.
        self._app.setQuitOnLastWindowClosed(False)
        logger.info("QApplication created.")

        # 3. Controller — owns the radial menu, pipeline, and results
        from app.controller import Controller

        self._controller = Controller()
        self._controller.settings_requested.connect(self._show_settings)

        # 4. Native event filter for WM_HOTKEY (exactly once)
        if not self._install_native_filter():
            logger.error("Failed to install native hotkey filter.")
            return False

        # 5. System tray
        self._tray = SystemTray()
        self._tray.open_requested.connect(self._on_open)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.privacy_requested.connect(self._show_privacy)
        self._tray.about_requested.connect(self._on_about)
        self._tray.check_components.connect(self._show_components)
        self._tray.exit_requested.connect(self._on_exit)
        self._tray.toggled.connect(self._on_toggled)
        self._tray.offline_toggled.connect(self._on_offline_toggled)
        self._sync_tray()
        self._tray.show()
        logger.info("System tray created.")

        # 6. Global hotkey
        hotkey = settings.hotkey_main

        if not self._register_hotkey():
            logger.error("Failed to register global hotkey.")
            self._tray.show_notification(
                "Hotkey Error",
                f"Could not register {hotkey}. Another application may already "
                f"be using it — pick a different one in Settings.",
                timeout_ms=6000,
            )
            # Keep running: the tray menu still works, and Settings can
            # be used to choose a hotkey that is actually free.
        else:
            logger.info(f"Global hotkey registered: {hotkey}")

        # 7. Ready
        logger.info("Cursor Bite initialized successfully.")
        event_bus.emit(AppEvent.READY)

        self._tray.show_notification(
            "Cursor Bite Ready",
            f"Press {hotkey} to open the menu.\nRight-click the tray icon for options.",
            timeout_ms=4000,
        )

        self._running = True
        return True

    # ── Native Event Filter (WM_HOTKEY) ─────────────────────────

    def _install_native_filter(self) -> bool:
        """Install the native event filter that receives WM_HOTKEY.

        Installed exactly once on the QApplication instance.
        """
        try:
            from infrastructure.os.hotkey_listener import (
                HotkeyNativeEventFilter,
                HOTKEY_ID,
            )

            if self._native_filter_installed:
                logger.warning("Native filter already installed — skipping duplicate install.")
                return True

            self._native_filter = HotkeyNativeEventFilter(hotkey_id=HOTKEY_ID)
            self._native_filter.set_callback(self._on_hotkey_pressed)

            app = self._app
            if app is None:
                logger.error("QApplication not available — cannot install filter.")
                return False

            app.installNativeEventFilter(self._native_filter)
            self._native_filter_installed = True
            logger.info("Native event filter installed (WM_HOTKEY receiver).")
            return True

        except Exception as e:
            logger.error(f"Failed to install native filter: {e}", exc_info=True)
            return False

    def _uninstall_native_filter(self) -> None:
        """Remove the native event filter on shutdown."""
        if not self._native_filter_installed:
            return

        try:
            app = self._app
            if app is not None and self._native_filter is not None:
                app.removeNativeEventFilter(self._native_filter)
                logger.info("Native event filter removed.")
        except Exception as e:
            logger.warning(f"Error removing native filter: {e}")
        finally:
            self._native_filter_installed = False
            self._native_filter = None

    def _on_hotkey_pressed(self) -> None:
        """Called on the UI thread when WM_HOTKEY arrives.

        Announced on the event bus rather than called through directly,
        so the hotkey has exactly one path into the app and anything
        else that cares can listen in.
        """
        event_bus.emit(AppEvent.HOTKEY_ACTIVATED)

    # ── Hotkey Registration ─────────────────────────────────────

    def _register_hotkey(self) -> bool:
        """Register the configured global hotkey via RegisterHotKey."""
        try:
            from infrastructure.os.hotkey_listener import HotkeyListener

            if self._hotkey_listener is None:
                self._hotkey_listener = HotkeyListener()

            success = self._hotkey_listener.register(settings.hotkey_main)

            if not success:
                logger.error(f"Hotkey registration failed for: {settings.hotkey_main}")

            return success

        except Exception as e:
            logger.error(f"Hotkey registration error: {e}", exc_info=True)
            return False

    def _unregister_hotkey(self) -> None:
        """Unregister the global hotkey."""
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.unregister()
            except Exception as e:
                logger.warning(f"Error unregistering hotkey: {e}")

    def _rebind_hotkey(self, hotkey: str) -> None:
        """Move the registration to a new combination after a save."""
        logger.info(f"Rebinding hotkey to: {hotkey}")

        self._unregister_hotkey()

        if self._register_hotkey():
            self._notify("Hotkey Updated", f"Cursor Bite now opens with {hotkey}.")
            return

        self._notify(
            "Hotkey Error",
            f"{hotkey} could not be registered — another application may be "
            f"using it. Cursor Bite has no hotkey until you pick another.",
            timeout_ms=6000,
        )

    # ── Windows ─────────────────────────────────────────────────
    #
    # Every window is non-modal and kept as a single instance: opening
    # one that is already open raises it instead of stacking a copy.

    def _show_settings(self) -> None:
        """Open the Settings window."""
        if self._settings_window is not None:
            self._raise(self._settings_window)
            return

        from ui.settings_window import SettingsWindow

        window = SettingsWindow()
        window.hotkey_changed.connect(self._rebind_hotkey)
        window.settings_saved.connect(self._on_settings_saved)
        window.finished.connect(
            lambda _code: self._release_window("_settings_window")
        )

        self._settings_window = window
        self._raise(window)
        logger.info("Settings window opened.")

    def _show_privacy(self) -> None:
        """Open the Privacy dashboard."""
        if self._privacy_window is not None:
            self._raise(self._privacy_window)
            return

        from ui.privacy_window import PrivacyDashboard

        window = PrivacyDashboard()
        window.privacy_changed.connect(self._sync_tray)
        window.finished.connect(
            lambda _code: self._release_window("_privacy_window")
        )

        self._privacy_window = window
        self._raise(window)
        logger.info("Privacy dashboard opened.")

    def _show_components(self) -> None:
        """Open the Components window."""
        if self._components_window is not None:
            self._raise(self._components_window)
            return

        from ui.components_window import ComponentsWindow

        window = ComponentsWindow(
            status_provider=self._controller.component_status,
            recheck_provider=self._controller.recheck_components,
        )
        window.finished.connect(
            lambda _code: self._release_window("_components_window")
        )

        self._components_window = window
        self._raise(window)
        logger.info("Components window opened.")

    @staticmethod
    def _raise(window: QDialog) -> None:
        """Show a window and put it in front."""
        window.show()
        window.raise_()
        window.activateWindow()

    def _release_window(self, name: str) -> None:
        """Forget a closed window so the next request builds a fresh one."""
        window = getattr(self, name, None)
        setattr(self, name, None)

        if window is not None:
            window.deleteLater()

    def _close_windows(self) -> None:
        """Close every open window (shutdown path)."""
        for name in ("_settings_window", "_privacy_window", "_components_window"):
            window = getattr(self, name, None)
            if window is not None:
                try:
                    window.close()
                except Exception:
                    pass
                setattr(self, name, None)

    # ── Tray Event Handlers ─────────────────────────────────────

    def _on_open(self) -> None:
        """Tray "Open" — same behaviour as pressing the hotkey."""
        if self._controller is not None:
            self._controller.on_hotkey()

    def _on_about(self) -> None:
        """Tray "About"."""
        self._notify(
            "Cursor Bite v1.0",
            f"Privacy-first Windows assistant.\n"
            f"Press {settings.hotkey_main} to open the menu.\n"
            f"Translation, OCR, and AI all run on this machine.",
            timeout_ms=5000,
        )

    def _on_exit(self) -> None:
        """Tray "Exit"."""
        logger.info("Exit requested from tray.")
        self.shutdown()

    def _on_toggled(self, enabled: bool) -> None:
        """Tray enable/disable toggle."""
        settings.set("general.enabled", enabled)
        self._persist("Enabled state")

        logger.info(f"Cursor Bite {'enabled' if enabled else 'disabled'}.")

        if not enabled and self._controller is not None:
            # Disabled means disabled: get anything on screen out of the way.
            self._controller.close_menu()
            self._controller.dismiss_panel()

    def _on_offline_toggled(self, offline: bool) -> None:
        """Tray offline mode toggle."""
        settings.set("privacy.offline_mode", offline)
        self._persist("Offline mode")

        logger.info(f"Offline mode {'enabled' if offline else 'disabled'}.")

        if self._privacy_window is not None:
            # Keep the dashboard honest if it happens to be open.
            self._privacy_window.refresh()

    def _on_settings_saved(self) -> None:
        """React to a settings save: re-read anything the app caches."""
        self._sync_tray()
        event_bus.emit(AppEvent.SETTINGS_CHANGED)

        if not settings.general_enabled and self._controller is not None:
            self._controller.close_menu()

    # ── Shared Helpers ──────────────────────────────────────────

    def _sync_tray(self) -> None:
        """Make the tray menu reflect the saved settings."""
        if self._tray is None:
            return

        self._tray.set_enabled(settings.general_enabled)
        self._tray.set_offline_mode(settings.privacy_offline_mode)

    def _persist(self, label: str) -> bool:
        """Write config.json, telling the user if it could not be written."""
        try:
            settings.save()
            return True
        except OSError as e:
            logger.error(f"Failed to save settings: {e}")
            self._notify(
                "Settings Not Saved",
                f"{label} was changed for this session only — config.json "
                f"could not be written.",
                timeout_ms=5000,
            )
            return False

    def _notify(self, title: str, message: str, timeout_ms: int = 4000) -> None:
        """Show a tray notification if the tray exists."""
        if self._tray is not None:
            self._tray.show_notification(title, message, timeout_ms=timeout_ms)

    # ── Run ─────────────────────────────────────────────────────

    def run(self) -> int:
        """Start the application event loop.

        Returns:
            Exit code (0 = success).
        """
        if not self._running:
            if not self.initialize():
                logger.error("Initialization failed.")
                return 1

        logger.info("Starting event loop...")
        return self._app.exec()

    # ── Shutdown ────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Shut down gracefully.

        Order matters: everything the user can see goes first, then the
        OS-level registrations, then the event loop.
        """
        logger.info("Shutting down Cursor Bite...")

        self._running = False

        # 1. Menu, result panel, region selector
        if self._controller is not None:
            self._controller.shutdown()

        # 2. Open windows
        self._close_windows()

        # 3. Release the hotkey and its HWND
        self._unregister_hotkey()
        self._hotkey_listener = None

        # 4. Stop receiving WM_HOTKEY
        self._uninstall_native_filter()

        # 5. Tray icon
        if self._tray is not None:
            try:
                self._tray.hide()
            except Exception:
                pass

        logger.info("Cursor Bite shutdown complete.")

        # 6. Leave the event loop. Without this the process would keep
        # running with nothing on screen and no way to reach it.
        if self._app is not None:
            self._app.quit()


# ── Module-level Access ────────────────────────────────────────────

_app_instance: Optional[Application] = None


def get_application() -> Application:
    """Get the global application instance (singleton)."""
    global _app_instance
    if _app_instance is None:
        _app_instance = Application()
    return _app_instance
