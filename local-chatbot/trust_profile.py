import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from settings import SECURE_ATLAS_FOLDER_CANDIDATES, TRUST_PROFILE_NAME


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_trust_file() -> Path:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError(
            "Secure ATLAS folder not available for trust profile storage"
        )
    return secure_folder / TRUST_PROFILE_NAME


def load_trust_profile() -> Dict[str, Any]:
    trust_file = get_trust_file()
    if not trust_file.exists():
        return {
            "trusted": False,
            "granted_at": None,
            "scope": [],
            "notes": "",
            "last_updated": None,
        }

    try:
        data = json.loads(trust_file.read_text(encoding="utf-8"))
    except Exception:
        return {
            "trusted": False,
            "granted_at": None,
            "scope": [],
            "notes": "",
            "last_updated": None,
        }

    data.setdefault("trusted", False)
    data.setdefault("granted_at", None)
    data.setdefault("scope", [])
    data.setdefault("notes", "")
    data.setdefault("last_updated", None)
    return data


def save_trust_profile(profile: Dict[str, Any]) -> None:
    trust_file = get_trust_file()
    trust_file.write_text(json.dumps(profile, indent=2), encoding="utf-8")


def grant_trust(notes: str = "", scope: Optional[List[str]] = None) -> None:
    profile = {
        "trusted": True,
        "granted_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope or ["full"],
        "notes": notes.strip(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    save_trust_profile(profile)


def revoke_trust() -> None:
    profile = {
        "trusted": False,
        "granted_at": None,
        "scope": [],
        "notes": "",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    save_trust_profile(profile)


def is_trusted() -> bool:
    return bool(load_trust_profile().get("trusted", False))


def get_trust_summary() -> str:
    profile = load_trust_profile()
    if not profile.get("trusted"):
        return "Assistant trust has not been granted yet."

    scope = ", ".join(profile.get("scope", [])) or "full"
    notes = profile.get("notes", "").strip() or "No additional notes provided."
    granted_at = profile.get("granted_at") or "unknown"
    return (
        f"Trusted assistant profile granted at {granted_at}.\n"
        f"Scope: {scope}.\n"
        f"Notes: {notes}."
    )
