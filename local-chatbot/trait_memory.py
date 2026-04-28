import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from settings import SECURE_ATLAS_FOLDER_CANDIDATES, TRAIT_STORE_NAME


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_trait_file() -> Path:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError("Secure ATLAS folder not available for trait storage")
    return secure_folder / TRAIT_STORE_NAME


def load_traits() -> List[Dict[str, Any]]:
    trait_file = get_trait_file()
    if not trait_file.exists():
        return []
    try:
        return json.loads(trait_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_traits(traits: List[Dict[str, Any]]) -> None:
    trait_file = get_trait_file()
    trait_file.write_text(json.dumps(traits, indent=2), encoding="utf-8")


def add_trait(content: str, category: str = "trait") -> None:
    traits = load_traits()
    traits.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "content": content.strip(),
        }
    )
    save_traits(traits)


def list_traits() -> List[Dict[str, Any]]:
    return load_traits()


def clear_traits() -> None:
    save_traits([])


def get_trait_summary(max_items: int = 12) -> str:
    traits = load_traits()
    if not traits:
        return ""
    lines = [
        f"- [{item['category']}] {item['content']}" for item in traits[-max_items:]
    ]
    return "\n".join(lines)
