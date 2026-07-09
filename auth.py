"""Master password hashing/verification and login-attempt lockout logic."""

import time
import logging
import bcrypt
from config import BCRYPT_ROUNDS, MAX_LOGIN_ATTEMPTS, LOCKOUT_SECONDS
from database import Database

logger = logging.getLogger(__name__)


class AuthManager:
    """Handles master password creation/verification and brute-force lockout."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._failed_attempts = 0
        self._locked_until: float = 0.0

    def is_first_launch(self) -> bool:
        return not self.db.has_master_password()

    def create_master_password(self, password: str) -> None:
        """Hash and store a new master password. Never stores plaintext."""
        if not password or len(password) < 8:
            raise ValueError("Master password must be at least 8 characters.")
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS))
        self.db.set_master_password_hash(hashed.decode("utf-8"))
        logger.info("Master password created.")

    def is_locked(self) -> tuple[bool, float]:
        """Return (locked, seconds_remaining)."""
        remaining = self._locked_until - time.time()
        if remaining > 0:
            return True, remaining
        return False, 0.0

    def verify_master_password(self, password: str) -> bool:
        """Verify password; enforces lockout after MAX_LOGIN_ATTEMPTS failures."""
        locked, remaining = self.is_locked()
        if locked:
            raise PermissionError(f"Locked out. Try again in {int(remaining)}s.")

        stored_hash = self.db.get_master_password_hash()
        if stored_hash is None:
            raise RuntimeError("No master password set.")

        ok = bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        if ok:
            self._failed_attempts = 0
            return True

        self._failed_attempts += 1
        logger.warning("Failed login attempt #%d", self._failed_attempts)
        if self._failed_attempts >= MAX_LOGIN_ATTEMPTS:
            self._locked_until = time.time() + LOCKOUT_SECONDS
            self._failed_attempts = 0
        return False
