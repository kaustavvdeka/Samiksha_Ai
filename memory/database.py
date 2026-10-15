"""
memory/database.py
==================
SQLite database layer for persistent memory.

Schema:
  memories      — key/value store for facts and preferences
  conversations — rolling window of recent conversation turns
  workflows     — user-defined custom command workflows (JSON blobs)

Design:
  - Uses Python's built-in sqlite3 (no ORM dependencies).
  - All operations are synchronous (SQLite doesn't need async for this scale).
  - Database file path comes from settings.memory_db_path.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config.settings import settings
from logger import get_logger

log = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

_CREATE_MEMORIES = """
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT    NOT NULL UNIQUE,
    value       TEXT    NOT NULL,
    category    TEXT    NOT NULL DEFAULT 'general',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
"""

_CREATE_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    timestamp   TEXT NOT NULL
);
"""

_CREATE_WORKFLOWS = """
CREATE TABLE IF NOT EXISTS workflows (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    steps       TEXT NOT NULL,   -- JSON array of {tool, arguments} dicts
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


class Database:
    """
    Low-level SQLite access layer.

    All SQL queries are concentrated here.
    The Memory class above calls these methods; agent code never touches SQL.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        raw_path = db_path if db_path is not None else settings.memory_db_path
        self.db_path = str(raw_path)
        self._persistent_conn = None
        if self.db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
        self._initialise()

    def _initialise(self) -> None:
        """Create tables if they don't exist yet."""
        with self._connect() as conn:
            conn.execute(_CREATE_MEMORIES)
            conn.execute(_CREATE_CONVERSATIONS)
            conn.execute(_CREATE_WORKFLOWS)
            conn.commit()
        log.info("Database initialised", extra={"path": self.db_path})

    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        if self._persistent_conn is not None:
            yield self._persistent_conn
            return

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Memories
    # ------------------------------------------------------------------ #

    def save_memory(self, key: str, value: str, category: str = "general") -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (key, value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    updated_at = excluded.updated_at
                """,
                (key, value, category, now, now),
            )
            conn.commit()
        log.debug("Memory saved", extra={"key": key})

    def get_memory(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM memories WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def search_memories(self, keyword: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT key, value, category, updated_at
                FROM memories
                WHERE key LIKE ? OR value LIKE ?
                LIMIT 10
                """,
                (f"%{keyword}%", f"%{keyword}%"),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_memories(self, category: str | None = None) -> list[dict]:
        with self._connect() as conn:
            if category:
                rows = conn.execute(
                    "SELECT key, value, category, updated_at FROM memories "
                    "WHERE category = ? ORDER BY updated_at DESC LIMIT 50",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT key, value, category, updated_at FROM memories "
                    "ORDER BY updated_at DESC LIMIT 50"
                ).fetchall()
        return [dict(r) for r in rows]

    def delete_memory(self, key: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    # Conversations
    # ------------------------------------------------------------------ #

    def add_conversation_turn(self, role: str, content: str) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, now),
            )
            conn.commit()

    def get_recent_conversations(self, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def clear_old_conversations(self, keep_last: int = 100) -> None:
        """Keep only the most recent `keep_last` conversation turns."""
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM conversations
                WHERE id NOT IN (
                    SELECT id FROM conversations
                    ORDER BY id DESC LIMIT ?
                )
                """,
                (keep_last,),
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Custom Workflows
    # ------------------------------------------------------------------ #

    def save_workflow(
        self, name: str, steps: list[dict], description: str = ""
    ) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (name, description, steps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    steps = excluded.steps,
                    updated_at = excluded.updated_at
                """,
                (name, description, json.dumps(steps), now, now),
            )
            conn.commit()
        log.info("Workflow saved", extra={"name": name, "steps": len(steps)})

    def get_workflow(self, name: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT name, description, steps FROM workflows WHERE name = ?",
                (name.lower(),),
            ).fetchone()
        if not row:
            return None
        return {
            "name": row["name"],
            "description": row["description"],
            "steps": json.loads(row["steps"]),
        }

    def list_workflows(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, description FROM workflows ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]
