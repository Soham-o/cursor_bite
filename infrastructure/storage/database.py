# Cursor Bite — SQLite Database
# ============================================================
# Lightweight SQLite storage for application metadata.
#
# IMPORTANT: Nothing in the running application constructs a Database
# instance today — every actual setting lives in config.json via
# config/settings.py, and no feature currently needs persistent
# key/value storage. This module is kept as a ready-made option for a
# future feature that does (e.g. caching OCR results across restarts),
# not as a placeholder standing in for missing functionality. It
# creates no database file and performs no operations on import.

import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Optional

from utils.logger import get_logger

logger = get_logger("infrastructure.storage.database")


# ── Database Path ──────────────────────────────────────────────────

def get_database_path() -> str:
    """Get the path to the SQLite database file."""
    app_data = os.path.expanduser("~/.cursor_bite")
    os.makedirs(app_data, exist_ok=True)
    return os.path.join(app_data, "cursor_bite.db")


# ── Database Manager ───────────────────────────────────────────────

class Database:
    """SQLite database manager.

    NOT initialized on import. Call initialize() explicitly when
    database functionality is needed.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or get_database_path()
        self._initialized: bool = False

    # ── Lazy Initialization ─────────────────────────────────────

    def _ensure_initialized(self) -> None:
        """Lazy initialization — creates tables on first use."""
        if self._initialized:
            return

        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)

        conn.commit()
        conn.close()
        self._initialized = True
        logger.info(f"Database initialized at: {self._db_path}")

    # ── Settings ────────────────────────────────────────────────

    def set_setting(self, key: str, value: Any) -> None:
        """Store a setting value."""
        import json
        self._ensure_initialized()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value."""
        import json
        self._ensure_initialized()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
            if row:
                return json.loads(row["value"])
            return default

    # ── Connection ──────────────────────────────────────────────

    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ── Note: no module-level instance ──────────────────────────────────
# Unlike the other infrastructure singletons in this codebase, there is
# deliberately no `database = Database()` here — nothing needs one yet.
# A future feature that does can construct one; see the module docstring.
