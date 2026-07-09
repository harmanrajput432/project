"""Secure password generation and strength estimation."""

import string
import secrets
from config import MIN_LENGTH, MAX_LENGTH


class PasswordGenerator:
    """Generates cryptographically secure passwords using `secrets`."""

    @staticmethod
    def generate(length: int = 16, use_upper: bool = True, use_lower: bool = True,
                 use_digits: bool = True, use_symbols: bool = True) -> str:
        if not (MIN_LENGTH <= length <= MAX_LENGTH):
            raise ValueError(f"Length must be between {MIN_LENGTH} and {MAX_LENGTH}.")

        pools = []
        if use_upper:
            pools.append(string.ascii_uppercase)
        if use_lower:
            pools.append(string.ascii_lowercase)
        if use_digits:
            pools.append(string.digits)
        if use_symbols:
            pools.append("!@#$%^&*()-_=+[]{}?")

        if not pools:
            raise ValueError("At least one character set must be selected.")

        alphabet = "".join(pools)
        # Guarantee at least one char from each selected pool
        password_chars = [secrets.choice(pool) for pool in pools]
        password_chars += [secrets.choice(alphabet) for _ in range(length - len(pools))]
        secrets.SystemRandom().shuffle(password_chars)
        return "".join(password_chars)

    @staticmethod
    def strength(password: str) -> str:
        """Return 'Weak', 'Medium', or 'Strong'."""
        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.isupper() for c in password) and any(c.islower() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()-_=+[]{}?" for c in password):
            score += 1

        if score <= 2:
            return "Weak"
        if score <= 4:
            return "Medium"
        return "Strong"
