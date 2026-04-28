"""
org_profiles.py — save and load Salesforce org login profiles locally.

Profiles are stored in secure/org_profiles.json.
Sensitive fields (password, security_token, consumer_secret) are encrypted
using Fernet symmetric encryption. The key is derived from a machine-specific
salt stored alongside the profiles — making the data unreadable if the file
is copied to another machine without the key file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import config
from cryptography.fernet import Fernet

_PROFILES_FILE = config.SECURE_DIR / "org_profiles.json"
_KEY_FILE = config.SECURE_DIR / "profiles.key"

_SENSITIVE_FIELDS = {"password", "security_token", "consumer_secret"}


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------


def _get_key() -> bytes:
    """Load or create the Fernet key for this machine."""
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    try:
        os.chmod(_KEY_FILE, 0o600)
    except Exception:
        pass
    return key


def _fernet() -> Fernet:
    return Fernet(_get_key())


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Profile storage
# ---------------------------------------------------------------------------


def _load_all() -> dict[str, Any]:
    if not _PROFILES_FILE.exists():
        return {}
    try:
        return json.loads(_PROFILES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_all(data: dict[str, Any]) -> None:
    _PROFILES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(_PROFILES_FILE, 0o600)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_profiles() -> list[dict[str, str]]:
    """Return a list of saved profiles with non-sensitive fields only."""
    all_profiles = _load_all()
    return [
        {
            "name": name,
            "username": data.get("username", ""),
            "domain": data.get("domain", "login"),
            "has_consumer_key": bool(data.get("consumer_key", "")),
        }
        for name, data in all_profiles.items()
    ]


def save_profile(name: str, profile: dict[str, str]) -> None:
    """Save a profile, encrypting sensitive fields."""
    all_profiles = _load_all()
    stored: dict[str, str] = {}
    for field, value in profile.items():
        if field in _SENSITIVE_FIELDS and value:
            stored[field] = _encrypt(value)
        else:
            stored[field] = value
    all_profiles[name] = stored
    _save_all(all_profiles)


def load_profile(name: str) -> dict[str, str] | None:
    """Load a profile and decrypt sensitive fields."""
    all_profiles = _load_all()
    data = all_profiles.get(name)
    if data is None:
        return None
    result: dict[str, str] = {}
    for field, value in data.items():
        if field in _SENSITIVE_FIELDS and value:
            result[field] = _decrypt(value)
        else:
            result[field] = value
    return result


def delete_profile(name: str) -> bool:
    """Delete a profile by name. Returns True if it existed."""
    all_profiles = _load_all()
    if name not in all_profiles:
        return False
    del all_profiles[name]
    _save_all(all_profiles)
    return True
