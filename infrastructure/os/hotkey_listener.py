# Cursor Bite — Global Hotkey Listener (Windows Native)
# ============================================================
# Uses Windows RegisterHotKey API via pywin32 for native global
# hotkey registration. No admin privileges required.
#
# HOW WM_HOTKEY IS DELIVERED:
#
#   1. A hidden QWidget provides an HWND for RegisterHotKey.
#   2. RegisterHotKey(hwnd, id, modifiers, vk) registers the hotkey
#      on that specific window handle.
#   3. When the hotkey is pressed, Windows sends WM_HOTKEY (0x0312)
#      to that HWND's window procedure.
#   4. A HotkeyNativeEventFilter (QAbstractNativeEventFilter) is
#      installed on the QApplication instance.
#   5. This filter receives raw Windows MSG structs via ctypes for
#      ALL windows in the application.
#   6. When WM_HOTKEY arrives with our hotkey ID, the filter calls
#      the registered callback, which emits a Qt signal.
#
# WHY THIS APPROACH:
#   - No global keyboard hooks (WH_KEYBOARD_LL)
#   - No global mouse hooks (WH_MOUSE_LL)
#   - No admin privileges required
#   - No message pump thread needed
#   - Standard Windows API, well-documented
#   - Works reliably across multi-monitor setups
#
# REGISTRY OF WHAT IS NOT USED:
#   - pywin32's win32api.SetWindowsHookEx: NOT used
#   - pyhooked: NOT used
#   - keyboard library: NOT used (requires admin)
#   - pynput: NOT used (requires admin for global hooks)
#   - Global mouse hook: NOT used

import ctypes
import logging
import threading
from typing import Callable, Optional

import win32api
import win32con
import win32gui
from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget

from utils.logger import get_logger

logger = get_logger("infrastructure.os.hotkey_listener")

# ── Windows Message Constants ──────────────────────────────────────

WM_HOTKEY = 0x0312


# ── ctypes Structures for Windows MSG ─────────────────────────────

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_uint),
        ("pt", POINT),
    ]


# ── Hotkey ID ──────────────────────────────────────────────────────

HOTKEY_ID = 9001  # Application-specific hotkey ID (must be unique per app)


# ── Native Event Filter (receives WM_HOTKEY) ──────────────────────

class HotkeyNativeEventFilter(QAbstractNativeEventFilter):
    """QAbstractNativeEventFilter that intercepts WM_HOTKEY messages.

    Install this on QApplication via:
        app.installNativeEventFilter(filter)

    The filter receives raw Windows messages for all windows in the
    application. When WM_HOTKEY arrives with our hotkey ID, it calls
    the registered callback.

    This runs in the Qt main thread context (nativeEventFilter is
    called from Qt's event loop), so emitting signals is safe.

    No global keyboard hooks. No global mouse hooks.
    """

    def __init__(self, hotkey_id: int = HOTKEY_ID) -> None:
        """Initialize the native event filter.

        Args:
            hotkey_id: The hotkey ID to listen for (default: HOTKEY_ID).
        """
        super().__init__()
        self._hotkey_id = hotkey_id
        self._callback: Optional[Callable[[], None]] = None

    def nativeEventFilter(
        self,
        event_type: bytes,
        message: int,
    ) -> tuple:
        """Process native Windows events.

        Called for every native Windows message in the application.
        Checks for WM_HOTKEY with our hotkey ID and invokes the callback.

        Args:
            event_type: Message type identifier (b'windows_generic_MSG' on Windows).
            message: Integer pointer to a MSG struct.

        Returns:
            Tuple of (handled: bool, result: int).
            Returns (True, 0) if the message was handled,
            (False, 0) to pass it to the default handler.
        """
        if event_type != b'windows_generic_MSG':
            return (False, 0)

        try:
            # PyQt6 passes a sip.voidptr; convert to int for ctypes
            msg_address = int(message)
            msg_ptr = ctypes.cast(msg_address, ctypes.POINTER(MSG))
            msg = msg_ptr.contents

            if msg.message == WM_HOTKEY:
                wparam = ctypes.c_void_p(msg.wParam).value
                if wparam == self._hotkey_id:
                    logger.debug("WM_HOTKEY received for our hotkey ID.")
                    if self._callback is not None:
                        self._callback()
                    return (True, 0)
        except Exception as e:
            logger.warning(f"Error in native event filter: {e}")

        return (False, 0)

    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when the hotkey is pressed.

        Args:
            callback: Callable with no arguments to call on hotkey press.
        """
        self._callback = callback

    def clear_callback(self) -> None:
        """Clear the callback (used during cleanup)."""
        self._callback = None


# ── Hotkey Listener ────────────────────────────────────────────────

class HotkeyListener(QObject):
    """Listens for a global hotkey using Windows RegisterHotKey API.

    Architecture:
      1. Creates a hidden QWidget to own an HWND
      2. Registers the hotkey on that HWND via RegisterHotKey
      3. A HotkeyNativeEventFilter (installed separately on QApplication)
         receives WM_HOTKEY and emits hotkey_pressed

    No global keyboard hooks. No global mouse hooks. No admin required.

    IMPORTANT: The native event filter must be installed on QApplication
    separately (by the Application class). This class only manages the
    hidden window and RegisterHotKey registration.
    """

    # ── Signals ─────────────────────────────────────────────────

    hotkey_pressed = pyqtSignal()
    """Emitted when the registered hotkey is pressed."""

    registration_failed = pyqtSignal(str)
    """Emitted when hotkey registration fails."""

    # ── State ───────────────────────────────────────────────────

    _hwnd: Optional[int] = None
    _window: Optional["_HotkeyWindow"] = None
    _registered: bool = False
    _registration_lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────────

    def register(self, hotkey_str: str = "Ctrl+Alt+B") -> bool:
        """Register a global hotkey via RegisterHotKey.

        Args:
            hotkey_str: Hotkey string (e.g., "Ctrl+Alt+B", "Win+C").

        Returns:
            True if registered successfully, False otherwise.
        """
        from infrastructure.os.hotkey_listener import parse_hotkey

        with self._registration_lock:
            if self._registered:
                logger.debug("Hotkey already registered — skipping duplicate registration.")
                return True

            parsed = parse_hotkey(hotkey_str)
            if parsed is None:
                msg = f"Invalid hotkey format: {hotkey_str}"
                logger.error(msg)
                self.registration_failed.emit(msg)
                return False

            modifiers, vk_code = parsed

            # Create hidden window to own the HWND
            self._create_hidden_window()

            if self._hwnd is None:
                msg = "Could not create hidden window for hotkey registration."
                logger.error(msg)
                self.registration_failed.emit(msg)
                return False

            # Register the hotkey on this HWND.
            # win32gui.RegisterHotKey raises pywintypes.error on failure
            # and returns None on success, so we treat no exception = success.
            try:
                win32gui.RegisterHotKey(
                    self._hwnd,
                    HOTKEY_ID,
                    modifiers,
                    vk_code,
                )
                self._registered = True
                logger.info(f"Hotkey registered successfully: {hotkey_str} (HWND: {self._hwnd:#x})")
                return True

            except Exception as e:
                error_code = win32api.GetLastError()
                msg = (
                    f"RegisterHotKey failed: {e} "
                    f"(Windows error code {error_code}). "
                    f"Hotkey '{hotkey_str}' may be in use by another application."
                )
                logger.error(msg)
                self.registration_failed.emit(msg)
                return False

    def unregister(self) -> None:
        """Unregister the global hotkey and clean up resources.

        Must be called on shutdown to release the hotkey registration.
        """
        with self._registration_lock:
            if not self._registered:
                return

            try:
                if self._hwnd is not None:
                    win32gui.UnregisterHotKey(self._hwnd, HOTKEY_ID)
                    logger.info(f"Hotkey unregistered from HWND {self._hwnd:#x}.")
            except Exception as e:
                logger.warning(f"Error unregistering hotkey: {e}")

            self._cleanup_hidden_window()
            self._registered = False
            self._hwnd = None

    # ── Hidden Window Management ─────────────────────────────────

    def _create_hidden_window(self) -> None:
        """Create a hidden QWidget to own an HWND for RegisterHotKey.

        Window flags and attributes must be set before the window is
        realized. We call winId() after show() so Windows has assigned
        a real HWND, then immediately hide the window again.
        """
        self._window = _HotkeyWindow()
        self._window.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SplashScreen
        )
        self._window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._window.resize(1, 1)

        # show() forces Windows to create the real HWND; hide() immediately
        # after so the window is never visible to the user.
        self._window.show()
        self._hwnd = int(self._window.winId())
        self._window.hide()
        logger.debug(f"Hidden hotkey window created. HWND: {self._hwnd:#x}")

    def _cleanup_hidden_window(self) -> None:
        """Destroy the hidden window and release the HWND."""
        if self._window is not None:
            try:
                self._window.close()
                self._window.deleteLater()
            except Exception:
                pass
            self._window = None
            self._hwnd = None

    # ── Properties ──────────────────────────────────────────────

    @property
    def is_registered(self) -> bool:
        """Whether the hotkey is currently registered."""
        return self._registered


# ── Hidden Window Widget ───────────────────────────────────────────

class _HotkeyWindow(QWidget):
    """Minimal hidden widget that exists only to provide an HWND.

    This widget is never shown. It exists solely so we can call
    win32api.RegisterHotKey on its window handle.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(1, 1)
        self.setMaximumSize(1, 1)


# ── Hotkey Parser ──────────────────────────────────────────────────

def parse_hotkey(hotkey_str: str) -> Optional[tuple]:
    """Parse a hotkey string like 'Ctrl+Alt+B' into (modifiers, vk_code).

    Args:
        hotkey_str: Hotkey string (e.g., "Ctrl+Alt+B", "Win+C").

    Returns:
        Tuple of (modifier_flags: int, virtual_key_code: int), or None if parsing fails.
    """
    if not hotkey_str:
        return None

    parts = [p.strip().upper() for p in hotkey_str.split("+")]
    if len(parts) < 2:
        logger.warning(f"Invalid hotkey format: '{hotkey_str}'. Need at least modifier+key.")
        return None

    # Modifier names to Windows flag constants
    MODIFIER_FLAGS = {
        "CTRL": win32con.MOD_CONTROL,
        "CONTROL": win32con.MOD_CONTROL,
        "ALT": win32con.MOD_ALT,
        "SHIFT": win32con.MOD_SHIFT,
        "WIN": win32con.MOD_WIN,
    }

    # Key names to virtual key codes
    VK_CODES = {
        "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45, "F": 0x46,
        "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A, "K": 0x4B,
        "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F, "P": 0x50,
        "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54, "U": 0x55,
        "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59, "Z": 0x5A,
        "A": 0x41,
        "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
        "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
        "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
        "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
        "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
        "SPACE": 0x20, "ENTER": 0x0D, "ESCAPE": 0x1B,
        "TAB": 0x09, "BACKSPACE": 0x08,
    }

    modifiers = 0
    vk_code: Optional[int] = None

    for part in parts:
        if part in MODIFIER_FLAGS:
            modifiers |= MODIFIER_FLAGS[part]
        elif part in VK_CODES:
            if vk_code is not None:
                logger.warning(f"Multiple keys in hotkey: '{hotkey_str}'. Using last key.")
            vk_code = VK_CODES[part]
        else:
            logger.warning(f"Unknown key in hotkey: '{part}' in '{hotkey_str}'")
            return None

    if vk_code is None:
        logger.warning(f"No valid key found in hotkey: '{hotkey_str}'")
        return None

    return (modifiers, vk_code)
