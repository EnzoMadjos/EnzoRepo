import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from settings import SECURE_ATLAS_FOLDER_CANDIDATES, TRAINING_STORE_NAME


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_training_file() -> Path:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError("Secure ATLAS folder not available for training storage")
    return secure_folder / TRAINING_STORE_NAME


def load_training() -> List[Dict[str, Any]]:
    training_file = get_training_file()
    if not training_file.exists():
        return []
    try:
        return json.loads(training_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_training(training: List[Dict[str, Any]]) -> None:
    training_file = get_training_file()
    training_file.write_text(json.dumps(training, indent=2), encoding="utf-8")


def add_training(entry: str, category: str = "training") -> None:
    training = load_training()
    training.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "entry": entry.strip(),
    })
    save_training(training)


def list_training() -> List[Dict[str, Any]]:
    return load_training()


def clear_training() -> None:
    save_training([])


def get_training_summary(max_items: int = 10, max_chars_per_item: int = 300) -> str:
    training = load_training()
    if not training:
        return ""
    lines = [f"- [{item['category']}] {item['entry'][:max_chars_per_item]}" for item in training[-max_items:]]
    return "\n".join(lines)
