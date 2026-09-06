# Cursor Bite — Windows Startup Registration
# ============================================================
# Implements the "Start with Windows" setting by writing a value under
# HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run.
#
# HKCU, not HKLM: per-user, no administrator rights, and removable by
# the same user who added it. Nothing outside the current user's own
# registry hive is touched.
#
# The registry is the source of truth for this setting, not config.json —
# the user may have removed the entry with Task Manager's Startup tab or
# an autoruns tool, and the checkbox should reflect reality.
#
# IMPORTANT: This module does NOT touch the registry on import.

import os
import sys
from typing import Optional

from utils.logger import get_logger

logger = get_logger("infrastructure.os.startup")


# ── Registry Location ──────────────────────────────────────────────

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "CursorBite"


# ── Launch Command ─────────────────────────────────────────────────

def _launch_command() -> Optional[str]:
    """Build the command Windows should run at logon.

    Returns None if the command can't be determined — better to report
    failure than to register something that won't start.
    """
    # Frozen build (PyInstaller and friends): the exe is self-contained.
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    entry_point = os.path.join(project_root, "main.py")

    if not os.path.exists(entry_point):
        logger.warning("Cannot register startup entry: main.py not found.")
        return None

    # pythonw.exe runs without a console window — for a tray app that
    # matters, otherwise every logon opens a stray black window.
    interpreter = sys.executable
    windowed = os.path.join(os.path.dirname(interpreter), "pythonw.exe")
    if os.path.exists(windowed):
        interpreter = windowed

    return f'"{interpreter}" "{entry_point}"'


# ── Public API ─────────────────────────────────────────────────────

def is_registered() -> bool:
    """Whether a startup entry currently exists."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning(f"Could not read startup registration: {e}")
        return False


def register() -> bool:
    """Add the startup entry. Returns True on success."""
    command = _launch_command()
    if command is None:
        return False

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, command)

        logger.info("Startup entry registered.")
        return True
    except Exception as e:
        logger.error(f"Failed to register startup entry: {e}")
        return False


def unregister() -> bool:
    """Remove the startup entry. Returns True if it is now absent."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _VALUE_NAME)

        logger.info("Startup entry removed.")
        return True
    except FileNotFoundError:
        # Already absent — the requested end state.
        return True
    except Exception as e:
        logger.error(f"Failed to remove startup entry: {e}")
        return False


def apply(enabled: bool) -> bool:
    """Make the registry match `enabled`. Returns True on success."""
    return register() if enabled else unregister()
