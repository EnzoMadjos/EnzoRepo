import json
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from settings import SECURE_ATLAS_FOLDER_CANDIDATES, VAULT_FILE_NAME


def get_secure_atlas_folder() -> Optional[Path]:
    for candidate in SECURE_ATLAS_FOLDER_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def get_fernet() -> Fernet:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError("Secure ATLAS folder not available for vault operations")

    key_file = secure_folder / "atlas.key"
    if not key_file.exists():
        raise RuntimeError("Encryption key not found in secure ATLAS folder")

    key = key_file.read_bytes()
    return Fernet(key)


def get_vault_file() -> Path:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        raise RuntimeError("Secure ATLAS folder not available for vault operations")
    return secure_folder / VAULT_FILE_NAME


def load_vault() -> Dict[str, Any]:
    vault_file = get_vault_file()
    if not vault_file.exists():
        return {}
    token = vault_file.read_bytes()
    decrypted = get_fernet().decrypt(token)
    return json.loads(decrypted.decode("utf-8"))


def save_vault(data: Dict[str, Any]) -> None:
    vault_file = get_vault_file()
    token = get_fernet().encrypt(json.dumps(data).encode("utf-8"))
    vault_file.write_bytes(token)


def list_secrets() -> list[str]:
    return list(load_vault().keys())


def get_secret(name: str) -> Optional[Any]:
    return load_vault().get(name)


def set_secret(name: str, value: Any) -> None:
    vault = load_vault()
    vault[name] = value
    save_vault(vault)


def delete_secret(name: str) -> bool:
    vault = load_vault()
    if name in vault:
        del vault[name]
        save_vault(vault)
        return True
    return False
