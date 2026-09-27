# Password Manager

A desktop password manager written in Python. Passwords are encrypted with Fernet (AES-128 in CBC mode with HMAC, from the `cryptography` package) before being stored in a local SQLite database, and the app is a small Tkinter GUI.

## Features

- Encrypted storage of site / username / password entries
- Encryption key generated automatically on first run (`secret.key`)
- Simple Tkinter GUI - save and retrieve passwords

## Installation

```bash
git clone https://github.com/Cybersec-001/password-manager.git
cd password-manager
pip install -r requirements.txt
```

Tkinter ships with Python on Windows and macOS. On Debian/Ubuntu install it once with:

```bash
sudo apt install python3-tk
```

## Run

```bash
python password_manager.py
```

On first launch the app generates `secret.key` in the project folder and creates `passwords.db`. Both are git-ignored on purpose - never commit them.

## How it works

- `secret.key` holds the Fernet key. Every password is encrypted with it before being written to SQLite, and decrypted only when you retrieve it.
- Anyone who gets both `secret.key` and `passwords.db` can decrypt every stored password, so keep the key file private and don't run this on shared machines.

## Honest limitations

This is a learning project, not a replacement for a vetted password manager:

- No master password - the key sits in a file next to the database.
- Fernet is AES-128-CBC + HMAC: solid authenticated encryption, but there is no key derivation from a passphrase and no protection if the key file leaks.
- No password generator, search, or clipboard clearing yet.
