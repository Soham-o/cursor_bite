# Cursor Bite — Structured Logging
# ============================================================
# IMPORTANT: Logs must NEVER contain:
#   - clipboard content
#   - screenshots
#   - passwords
#   - API keys
#   - user prompts
#   - private text
#
# Logs contain technical events only:
#   - "Hotkey activated"
#   - "OCR started"
#   - "OCR completed in 180ms"
#   - "Translation completed"
#   - "Local model unavailable"
#
# NEVER:
#   - "User translated: [private content]"

import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Prevent Python 3.13 fatal access violation in logging.LogRecord.__init__
# when libraries (like argostranslate or asyncio) use logging
if hasattr(logging, "logAsyncioTasks"):
    logging.logAsyncioTasks = False

# Ensure standard streams handle UTF-8 on Windows consoles
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


# ── Log Level ──────────────────────────────────────────────────────

LOG_LEVEL = os.environ.get("CURSOR_BITE_LOG_LEVEL", "INFO").upper()
"""Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"""


# ── Format ─────────────────────────────────────────────────────────

class TechnicalLogFilter(logging.Filter):
    """Ensures logs don't contain sensitive content.

    This is a SAFETY NET, not the primary protection.
    Sensitive data should never be passed to logger in the first place.
    """

    # Patterns that should never appear in logs
    _SENSITIVE_INDICATORS = [
        "password", "api_key", "apikey", "secret", "token",
        "credit card", "ssn", "pasword",  # common misspellings
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        msg_lower = msg.lower()
        for indicator in self._SENSITIVE_INDICATORS:
            if indicator in msg_lower:
                # Redact the log message
                record.msg = "[REDACTED — potential sensitive content]"
                record.args = ()
                break
        return True


class CursorBiteFormatter(logging.Formatter):
    """Structured formatter for Cursor Bite logs."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()

        # Add thread info for debugging concurrency issues
        thread_info = f" [{record.threadName}]" if record.threadName != "MainThread" else ""

        return f"[{timestamp}] [{level}] [{logger_name}]{thread_info} {message}"


# ── Logger Setup ───────────────────────────────────────────────────

def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Configure structured logging for the application.

    Args:
        log_file: Optional path to a log file. If provided, logs are
                  written to both file and console.

    Returns:
        The root Cursor Bite logger.
    """
    # Create the main logger
    logger = logging.getLogger("cursor_bite")
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False

    # Remove any existing handlers (avoid duplicates on reload)
    logger.handlers.clear()

    # Add the sensitive content filter
    logger.addFilter(TechnicalLogFilter())

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(CursorBiteFormatter())
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(CursorBiteFormatter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the 'cursor_bite' namespace.

    Usage:
        logger = get_logger("infrastructure.hotkey")
        logger.info("Hotkey registered")
    """
    return logging.getLogger(f"cursor_bite.{name}")


# ── Convenience: silence noisy third-party loggers ────────────────

def silence_third_party_logs() -> None:
    """Reduce noise from third-party libraries."""
    for lib in ["urllib3", "requests", "PIL", "pytesseract", "argostranslate"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
