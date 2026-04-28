import json
from pathlib import Path
from typing import Any, Dict, Optional

from settings import NICKNAME_PROFILE_NAME, SECURE_ATLAS_FOLDER_CANDIDATES


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_nickname_file() -> Path:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError("Secure ATLAS folder not available for nickname storage")
    return secure_folder / NICKNAME_PROFILE_NAME


def load_nickname_profile() -> Dict[str, Any]:
    nickname_file = get_nickname_file()
    if not nickname_file.exists():
        return {
            "preferred": None,
            "options": ["Pre", "Lods"],
            "last_updated": None,
        }

    try:
        profile = json.loads(nickname_file.read_text(encoding="utf-8"))
    except Exception:
        return {
            "preferred": None,
            "options": ["Pre", "Lods"],
            "last_updated": None,
        }

    profile.setdefault("preferred", None)
    profile.setdefault("options", ["Pre", "Lods"])
    profile.setdefault("last_updated", None)
    return profile


def save_nickname_profile(profile: Dict[str, Any]) -> None:
    nickname_file = get_nickname_file()
    nickname_file.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def set_preferred_nickname(nickname: str) -> None:
    profile = load_nickname_profile()
    if nickname not in profile.get("options", ["Pre", "Lods"]):
        raise ValueError("Nickname must be one of the allowed options")
    profile["preferred"] = nickname
    profile["last_updated"] = (
        __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat()
    )
    save_nickname_profile(profile)


def get_preferred_nickname() -> Optional[str]:
    return load_nickname_profile().get("preferred")
