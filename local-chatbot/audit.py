from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from settings import AUDIT_LOG_NAME, SECURE_ATLAS_FOLDER_CANDIDATES


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def append_audit(action: str, details: str = "") -> None:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        return

    log_file = secure_folder / AUDIT_LOG_NAME
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_file.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] {action}: {details}\n")


def read_audit_history(max_lines: int = 200) -> list[str]:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        return []

    log_file = secure_folder / AUDIT_LOG_NAME
    if not log_file.exists():
        return []

    lines = log_file.read_text(encoding="utf-8").splitlines()
    return lines[-max_lines:]
