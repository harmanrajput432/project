"""Central configuration and constants for the password manager."""

from pathlib import Path

# --- Paths ---
APP_DIR = Path.home() / ".secure_pm"
APP_DIR.mkdir(exist_ok=True)

DB_PATH = APP_DIR / "vault.db"
KEY_PATH = APP_DIR / "secret.key"
LOG_PATH = APP_DIR / "app.log"

# --- Security ---
BCRYPT_ROUNDS = 12
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 60           # lock login after too many failed attempts
CLIPBOARD_CLEAR_SECONDS = 30
AUTO_LOCK_SECONDS = 120        # auto-lock app after inactivity

# --- Password generator defaults ---
DEFAULT_LENGTH = 16
MIN_LENGTH = 8
MAX_LENGTH = 64

# --- GUI ---
APP_NAME = "SecurePM"
WINDOW_SIZE = "1000x650"
DEFAULT_THEME = "dark"   # "dark" or "light"
