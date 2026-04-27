"""
auth.py — simple username/password session auth for the PITOGO Barangay App.

No Salesforce dependency. Credentials are stored in secure/users.json (hashed).

Flow:
  POST /auth/login  {username, password}
  → Returns {token, username, role}
  All protected routes require:  Authorization: Bearer <token>
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException, status

import config

_USERS_FILE = config.SECURE_DIR / "users.json"


# ── User store ────────────────────────────────────────────────────────────────

def _load_users() -> dict:
    if _USERS_FILE.exists():
        return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
    # Default admin on first run — change immediately after install
    default = {
        "admin": {
            "password_hash": _hash("admin123"),
            "role": "admin",
            "display_name": "Administrator",
        }
    }
    _USERS_FILE.write_text(json.dumps(default, indent=2), encoding="utf-8")
    return default


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_user(username: str, password: str) -> Optional[dict]:
    users = _load_users()
    user  = users.get(username)
    if user and user.get("password_hash") == _hash(password):
        return user
    return None


# ── Session store ─────────────────────────────────────────────────────────────

@dataclasses.dataclass
class SessionData:
    username:     str
    role:         str
    display_name: str
    expiry:       float


_sessions: dict[str, SessionData] = {}


def _expire_seconds() -> float:
    return config.SESSION_EXPIRE_HOURS * 3600


def create_session(username: str, role: str, display_name: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = SessionData(
        username=username,
        role=role,
        display_name=display_name,
        expiry=time.monotonic() + _expire_seconds(),
    )
    return token


def get_session(token: str) -> Optional[SessionData]:
    s = _sessions.get(token)
    if s is None:
        return None
    if time.monotonic() > s.expiry:
        _sessions.pop(token, None)
        return None
    # Slide expiry
    s.expiry = time.monotonic() + _expire_seconds()
    return s


def invalidate_session(token: str) -> None:
    _sessions.pop(token, None)


# ── FastAPI dependency ────────────────────────────────────────────────────────

def require_auth(authorization: str = Header(default="")) -> SessionData:
    token = authorization.removeprefix("Bearer ").strip()
    session = get_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or session expired. Please log in again.",
        )
    return session
