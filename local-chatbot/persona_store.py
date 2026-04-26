import json
from pathlib import Path
from typing import Optional

from settings import SECURE_ATLAS_FOLDER_CANDIDATES, PERSONA_SUMMARY_NAME


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_persona_file() -> Path:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError("Secure ATLAS folder not available for persona storage")
    return secure_folder / PERSONA_SUMMARY_NAME


def save_persona_summary(summary: str) -> None:
    persona_file = get_persona_file()
    persona_file.write_text(summary, encoding="utf-8")


def load_persona_summary() -> str:
    persona_file = get_persona_file()
    if not persona_file.exists():
        return ""
    return persona_file.read_text(encoding="utf-8")
