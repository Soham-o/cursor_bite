# Cursor Bite — main.py
# ============================================================
# Entry point for the Cursor Bite application.
#
# Usage:
#   python main.py
#
# The application runs as a system tray app. No main window
# is shown — interact via the tray icon or the global hotkey.
#
# Press Ctrl+Alt+B to activate the radial menu.

import sys
import os
import logging

# Prevent Python 3.13 access violation in logging when asyncio tasks are queried
if hasattr(logging, "logAsyncioTasks"):
    logging.logAsyncioTasks = False

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add the project root to the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# ── Main Entry Point ───────────────────────────────────────────────

def main() -> int:
    """Main entry point for Cursor Bite.

    Returns:
        Exit code (0 = success, non-zero = error).
    """
    from app.application import Application

    app = Application()

    try:
        return app.run()
    except KeyboardInterrupt:
        print("\nCursor Bite interrupted by user.")
        return 0
    except Exception as e:
        import logging
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
