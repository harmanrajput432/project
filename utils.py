"""Small shared helpers: logging setup and clipboard auto-clear."""

import logging
import threading
import pyperclip
from config import LOG_PATH, CLIPBOARD_CLEAR_SECONDS


def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def copy_to_clipboard_with_autoclear(text: str, seconds: int = CLIPBOARD_CLEAR_SECONDS) -> None:
    """Copy text to clipboard, then clear it after `seconds` (background thread)."""
    pyperclip.copy(text)

    def _clear():
        # Only clear if clipboard still holds what we copied (avoid wiping
        # something else the user copied in the meantime).
        if pyperclip.paste() == text:
            pyperclip.copy("")

    timer = threading.Timer(seconds, _clear)
    timer.daemon = True
    timer.start()
