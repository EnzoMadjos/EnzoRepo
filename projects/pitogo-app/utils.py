from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Tuple

import config


def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64u_decode(s: str) -> bytes:
    # add padding
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def create_signed_token(rel_path: str, ttl_seconds: int = 300) -> Tuple[str, int]:
    """Create a signed token for a path relative to `config.SECURE_DIR`.

    Returns (token, expires_at_unix).
    """
    secret = config.DOWNLOAD_SECRET
    if not secret:
        raise RuntimeError("DOWNLOAD_SECRET not configured")

    exp = int(time.time()) + int(ttl_seconds)
    payload = json.dumps({"path": rel_path, "exp": exp}, separators=(",", ":")).encode(
        "utf-8"
    )
    payload_b64 = _b64u_encode(payload)
    sig = hmac.new(
        secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
    ).digest()
    sig_b64 = _b64u_encode(sig)
    token = f"{payload_b64}.{sig_b64}"
    return token, exp


def verify_signed_token(token: str) -> dict:
    """Verify token and return the payload dict. Raises ValueError on failure."""
    secret = config.DOWNLOAD_SECRET
    if not secret:
        raise ValueError("DOWNLOAD_SECRET not configured")
    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except Exception:
        raise ValueError("invalid token format")
    expected_sig = hmac.new(
        secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256
    ).digest()
    try:
        sig = _b64u_decode(sig_b64)
    except Exception:
        raise ValueError("invalid signature encoding")
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("invalid signature")
    try:
        payload_bytes = _b64u_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise ValueError("invalid payload")
    if not isinstance(payload, dict) or "path" not in payload or "exp" not in payload:
        raise ValueError("invalid payload structure")
    if int(time.time()) > int(payload["exp"]):
        raise ValueError("token expired")
    return payload
