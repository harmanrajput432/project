"""SQLite database layer. Owns schema creation and raw queries."""

import sqlite3
import logging
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around sqlite3 with schema management."""

    def __init__(self) -> None:
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS master (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    password_hash TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,   -- encrypted
                    notes TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    # --- master password ---
    def has_master_password(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM master WHERE id = 1").fetchone()
            return row is not None

    def set_master_password_hash(self, password_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO master (id, password_hash) VALUES (1, ?)",
                (password_hash,),
            )

    def get_master_password_hash(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT password_hash FROM master WHERE id = 1").fetchone()
            return row["password_hash"] if row else None

    # --- vault entries (all parameterized -> SQL injection safe) ---
    def insert_entry(self, website: str, username: str, enc_password: str,
                      notes: str, created_at: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO entries (website, username, password, notes, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (website, username, enc_password, notes, created_at),
            )
            return cur.lastrowid

    def update_entry(self, entry_id: int, website: str, username: str,
                      enc_password: str, notes: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE entries SET website=?, username=?, password=?, notes=? WHERE id=?",
                (website, username, enc_password, notes, entry_id),
            )

    def delete_entry(self, entry_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))

    def get_all_entries(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM entries ORDER BY website COLLATE NOCASE ASC"
            ).fetchall()

    def search_entries(self, term: str) -> list[sqlite3.Row]:
        like = f"%{term}%"
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM entries WHERE website LIKE ? OR username LIKE ? "
                "ORDER BY website COLLATE NOCASE ASC",
                (like, like),
            ).fetchall()
