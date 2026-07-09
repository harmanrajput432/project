"""Handles Fernet symmetric encryption for vault passwords."""

import logging
from cryptography.fernet import Fernet, InvalidToken
from config import KEY_PATH

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Generates/loads a Fernet key and encrypts/decrypts strings."""

    def __init__(self) -> None:
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if KEY_PATH.exists():
            return KEY_PATH.read_bytes()
        key = Fernet.generate_key()
        KEY_PATH.write_bytes(key)
        try:
            KEY_PATH.chmod(0o600)  # owner read/write only (no-op on Windows)
        except OSError:
            pass
        logger.info("Generated new encryption key.")
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string, returning a base64 token as str."""
        if plaintext is None:
            plaintext = ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Decrypt a token back to plaintext. Returns '' on failure."""
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            logger.error("Decryption failed: %s", exc)
            return ""
