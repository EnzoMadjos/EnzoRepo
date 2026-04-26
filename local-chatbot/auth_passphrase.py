import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Optional

from settings import SECURE_ATLAS_FOLDER_CANDIDATES

PASS_FILE = "atlas_pass.json"


def _get_secure_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _get_pass_file() -> Path:
    folder = _get_secure_folder()
    if folder is None:
        raise RuntimeError("Secure ATLAS folder not found")
    return folder / PASS_FILE


def passphrase_is_set() -> bool:
    try:
        return _get_pass_file().exists()
    except Exception:
        return False


def set_passphrase(passphrase: str) -> None:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 200_000)
    data = {"salt": salt.hex(), "hash": key.hex()}
    p = _get_pass_file()
    p.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass


def verify_passphrase(passphrase: str) -> bool:
    try:
        p = _get_pass_file()
        if not p.exists():
            return False
        data = json.loads(p.read_text(encoding="utf-8"))
        salt = bytes.fromhex(data["salt"])
        expected = bytes.fromhex(data["hash"])
        key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(key, expected)
    except Exception:
        return False


def get_api_key() -> str:
    folder = _get_secure_folder()
    if folder is None:
        raise RuntimeError("Secure folder not found")
    return (folder / "atlas_api.key").read_text(encoding="utf-8").strip()
