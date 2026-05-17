"""
Standalone Fernet vault for Live Seller app.
Key is generated once and stored in secure/liveseller.key
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet

from config import SECURE_DIR

_KEY_FILE = SECURE_DIR / "liveseller.key"
_VAULT_FILE = SECURE_DIR / "vault.json.enc"


def _ensure_secure_dir() -> None:
    SECURE_DIR.mkdir(parents=True, exist_ok=True)
    SECURE_DIR.chmod(0o700)


def _get_or_create_key() -> bytes:
    _ensure_secure_dir()
    if not _KEY_FILE.exists():
        key = Fernet.generate_key()
        _KEY_FILE.write_bytes(key)
        _KEY_FILE.chmod(0o600)
        return key
    return _KEY_FILE.read_bytes()


def _get_fernet() -> Fernet:
    return Fernet(_get_or_create_key())


def load_vault() -> dict[str, Any]:
    if not _VAULT_FILE.exists():
        return {}
    try:
        token = _VAULT_FILE.read_bytes()
        decrypted = _get_fernet().decrypt(token)
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return {}


def save_vault(data: dict[str, Any]) -> None:
    _ensure_secure_dir()
    token = _get_fernet().encrypt(json.dumps(data).encode("utf-8"))
    _VAULT_FILE.write_bytes(token)


def get_secret(name: str) -> Optional[Any]:
    return load_vault().get(name)


def set_secret(name: str, value: Any) -> None:
    vault = load_vault()
    vault[name] = value
    save_vault(vault)


def delete_secret(name: str) -> None:
    vault = load_vault()
    vault.pop(name, None)
    save_vault(vault)
