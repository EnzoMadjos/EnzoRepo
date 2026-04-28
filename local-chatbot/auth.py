import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException
from settings import API_KEY_NAME, SECURE_ATLAS_FOLDER_CANDIDATES


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def load_api_key() -> str:
    env_key = os.getenv("ATLAS_API_KEY")
    if env_key:
        return env_key.strip()

    secure_folder = get_secure_atlas_folder()
    if secure_folder is not None:
        key_file = secure_folder / "atlas_api.key"
        if key_file.exists():
            return key_file.read_text(encoding="utf-8").strip()
        api_key = secrets.token_urlsafe(32)
        key_file.write_text(api_key, encoding="utf-8")
        return api_key

    raise RuntimeError("No secure ATLAS folder available to store or read API key.")


def verify_api_key(api_key: str = Header(..., alias=API_KEY_NAME)) -> None:
    expected = load_api_key()
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
