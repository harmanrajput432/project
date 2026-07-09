"""Vault: CRUD operations for password entries, combining DB + encryption."""

import logging
from datetime import datetime
from dataclasses import dataclass
from database import Database
from encryption import EncryptionManager

logger = logging.getLogger(__name__)


@dataclass
class Entry:
    id: int
    website: str
    username: str
    password: str  # decrypted plaintext (only populated when needed)
    notes: str
    created_at: str


class Vault:
    """High-level API for managing encrypted password entries."""

    def __init__(self, db: Database, encryptor: EncryptionManager) -> None:
        self.db = db
        self.encryptor = encryptor

    @staticmethod
    def _validate(website: str, username: str, password: str) -> None:
        if not website.strip():
            raise ValueError("Website cannot be empty.")
        if not username.strip():
            raise ValueError("Username cannot be empty.")
        if not password:
            raise ValueError("Password cannot be empty.")

    def add_entry(self, website: str, username: str, password: str, notes: str = "") -> int:
        self._validate(website, username, password)
        enc = self.encryptor.encrypt(password)
        created_at = datetime.now().isoformat(timespec="seconds")
        entry_id = self.db.insert_entry(website.strip(), username.strip(), enc, notes.strip(), created_at)
        logger.info("Added entry for %s", website)
        return entry_id

    def update_entry(self, entry_id: int, website: str, username: str,
                      password: str, notes: str = "") -> None:
        self._validate(website, username, password)
        enc = self.encryptor.encrypt(password)
        self.db.update_entry(entry_id, website.strip(), username.strip(), enc, notes.strip())
        logger.info("Updated entry id=%d", entry_id)

    def delete_entry(self, entry_id: int) -> None:
        self.db.delete_entry(entry_id)
        logger.info("Deleted entry id=%d", entry_id)

    def _row_to_entry(self, row, reveal: bool) -> Entry:
        password = self.encryptor.decrypt(row["password"]) if reveal else "••••••••"
        return Entry(
            id=row["id"], website=row["website"], username=row["username"],
            password=password, notes=row["notes"] or "", created_at=row["created_at"],
        )

    def list_all(self, reveal: bool = False) -> list[Entry]:
        return [self._row_to_entry(r, reveal) for r in self.db.get_all_entries()]

    def search(self, term: str, reveal: bool = False) -> list[Entry]:
        if not term.strip():
            return self.list_all(reveal)
        return [self._row_to_entry(r, reveal) for r in self.db.search_entries(term.strip())]

    def reveal_password(self, entry_id: int) -> str:
        """Decrypt and return the plaintext password for a single entry."""
        for row in self.db.get_all_entries():
            if row["id"] == entry_id:
                return self.encryptor.decrypt(row["password"])
        raise ValueError("Entry not found.")
