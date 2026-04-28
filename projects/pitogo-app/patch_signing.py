"""
patch_signing.py — simple RSA SHA256 signature verification helper.

Expect a PEM-encoded public key at `config.PATCH_PUBLIC_KEY_PATH`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import config
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def load_public_key() -> Optional[object]:
    p = Path(config.PATCH_PUBLIC_KEY_PATH)
    if not p.exists():
        return None
    data = p.read_bytes()
    return load_pem_public_key(data)


def verify_signature(data: bytes, signature: bytes) -> bool:
    """Return True if signature verifies using the configured public key."""
    key = load_public_key()
    if key is None:
        return False
    try:
        key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
