# SecurePM 🔐

A lightweight desktop password manager built with Python and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter). SecurePM stores your website/username/password entries locally in an encrypted SQLite vault, protected behind a single master password.

## Features

- **Master password login** — protects the vault with a bcrypt-hashed master password (plaintext is never stored).
- **Brute-force lockout** — the app temporarily locks after repeated failed login attempts.
- **Encrypted vault** — each saved password is encrypted at rest with `cryptography`'s Fernet symmetric encryption before it touches the database.
- **Full CRUD** — add, update, delete, and search password entries (by website/username).
- **Password generator** — create strong random passwords with configurable length.
- **Clipboard support** — copy passwords to the clipboard via `pyperclip` (with an auto-clear timeout).
- **Auto-lock** — the app can automatically lock itself after a period of inactivity.
- **Local-first** — all data lives on your machine in `~/.secure_pm`; nothing is sent over the network.

## Tech Stack

| Component        | Library                                      |
|------------------|-----------------------------------------------|
| GUI              | `customtkinter`                               |
| Password hashing | `bcrypt`                                      |
| Encryption       | `cryptography` (Fernet)                       |
| Clipboard        | `pyperclip`                                   |
| Storage          | SQLite (via the standard library)             |

## Project Structure

```
project/
├── main.py               # Application entry point
├── gui.py                 # CustomTkinter GUI (login, vault view, etc.)
├── auth.py                # Master password hashing, verification, lockout logic
├── vault.py                # High-level CRUD API combining DB + encryption
├── encryption.py           # Fernet key management and encrypt/decrypt helpers
├── database.py             # SQLite access layer
├── password_generator.py   # Random password generation
├── config.py                # Central paths and configuration constants
├── utils.py                 # Logging setup and shared helpers
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.10+ (uses modern type-hint syntax like `list[Entry]`)

### Installation

```bash
git clone https://github.com/harmanrajput432/project.git
cd project
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

On first launch, you'll be prompted to create a master password (minimum 8 characters). This password is hashed with bcrypt and never stored in plaintext — **if you forget it, your vault cannot be recovered.**

## How It Works

- **First launch:** `AuthManager.is_first_launch()` checks whether a master password hash exists yet. If not, you're prompted to create one.
- **Login:** Your master password is verified against the stored bcrypt hash. Too many failed attempts triggers a temporary lockout (`MAX_LOGIN_ATTEMPTS` / `LOCKOUT_SECONDS` in `config.py`).
- **Storing a password:** `Vault.add_entry()` validates the input, encrypts the password with a locally generated Fernet key (`encryption.py`), and stores the encrypted blob plus metadata in SQLite.
- **Viewing a password:** Entries are listed masked (`••••••••`) by default; passwords are only decrypted on demand via `Vault.reveal_password()`.

## Local Data

All application data is stored under:

```
~/.secure_pm/
├── vault.db      # SQLite database (encrypted password entries)
├── secret.key     # Fernet encryption key (owner-only permissions where supported)
└── app.log        # Application logs
```

> ⚠️ **Back up `secret.key` along with `vault.db`.** Without the key, encrypted entries in the database cannot be decrypted.

## Configuration

Key settings can be tuned in `config.py`, including bcrypt rounds, lockout duration, clipboard auto-clear timing, auto-lock timeout, and default generated password length.

## Disclaimer

This project is a personal/learning-oriented password manager. Before relying on it for sensitive real-world credentials, review the code — especially the encryption key handling and storage paths — to make sure it meets your security needs.

## License

No license has been specified for this repository. Contact the repository owner if you'd like to use or contribute to this project.
