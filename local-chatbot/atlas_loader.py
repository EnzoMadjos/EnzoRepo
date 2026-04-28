import importlib.util
from pathlib import Path

from cryptography.fernet import Fernet
from settings import SECURE_ATLAS_FOLDER_CANDIDATES


def get_secure_atlas_folder() -> Path | None:
    for path in SECURE_ATLAS_FOLDER_CANDIDATES:
        if path.exists() and path.is_dir():
            return path
    return None


def load_atlas_from_secure_folder() -> str | None:
    secure_folder = get_secure_atlas_folder()
    if not secure_folder:
        return None

    key_file = secure_folder / "atlas.key"
    encrypted_file = secure_folder / "atlas.bin"
    if key_file.exists() and encrypted_file.exists():
        try:
            key = key_file.read_bytes()
            data = Fernet(key).decrypt(encrypted_file.read_bytes())
            return data.decode("utf-8")
        except Exception:
            return None

    plaintext_file = secure_folder / "atlas.py"
    if plaintext_file.exists():
        spec = importlib.util.spec_from_file_location("atlas_secure", plaintext_file)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "ATLAS_SYSTEM_PROMPT", None)

    return None


def load_atlas_prompt() -> str:
    prompt = load_atlas_from_secure_folder()
    if prompt is not None:
        return prompt

    # Fallback to local workspace atlas.py if secure folder is unavailable.
    try:
        from atlas import ATLAS_SYSTEM_PROMPT

        return ATLAS_SYSTEM_PROMPT
    except ImportError as exc:
        raise RuntimeError(
            "ATLAS prompt is not available in the secure folder or the local workspace. "
            "Ensure C:\\ATLAS contains atlas.bin and atlas.key, or restore atlas.py locally."
        ) from exc
