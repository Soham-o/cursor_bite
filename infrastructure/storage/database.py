# Cursor Bite — SQLite Database
# ============================================================
# Lightweight SQLite storage for application metadata.
#
# IMPORTANT: For Milestone 1, this module is NOT initialized or used.
# The module exists for future milestones but creates no database
# on import and performs no operations unless explicitly called.
#
# Database initialization is deferred to when it's actually needed.

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


# ── Note: No module-level instance for Milestone 1 ─────────────────
# The database is NOT created or used in Milestone 1.
# Future milestones can create a Database() instance when needed.
