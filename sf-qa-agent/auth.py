"""
auth.py — Salesforce-credential-based session auth.

Flow:
  1. POST /auth/login  {username, password, security_token, domain}
     → App attempts Salesforce login. On success, returns {token, username, org_id, instance_url}
  2. All protected routes require header:  Authorization: Bearer <token>

Each session stores the user's SF credentials so that each /run-test call
uses that specific user's org. Multiple users on different orgs are fully
supported — credentials are never shared.

Tokens expire after SESSION_EXPIRE_HOURS (set in config.py).
Credentials are held in memory only — never written to disk.
"""

from __future__ import annotations

import dataclasses
import secrets
import time
from typing import Optional

import config
from fastapi import Header, HTTPException, status


@dataclasses.dataclass
class SessionData:
    username: str
    sf_password: str
    sf_security_token: str
    sf_domain: str
    org_id: str
    instance_url: str
    expiry: float
    consumer_key: str = ""
    consumer_secret: str = ""
    access_token: str = ""  # OAuth/SOAP token — used directly to avoid re-auth


# In-memory token store: token → SessionData
_sessions: dict[str, SessionData] = {}


def _expire_seconds() -> float:
    return config.SESSION_EXPIRE_HOURS * 3600


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


def create_session(
    username: str,
    sf_password: str,
    sf_security_token: str,
    sf_domain: str,
    org_id: str,
    instance_url: str,
    consumer_key: str = "",
    consumer_secret: str = "",
    access_token: str = "",
) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = SessionData(
        username=username,
        sf_password=sf_password,
        sf_security_token=sf_security_token,
        sf_domain=sf_domain,
        org_id=org_id,
        instance_url=instance_url,
        expiry=time.monotonic() + _expire_seconds(),
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
    )
    return token


def get_session(token: str) -> Optional[SessionData]:
    session = _sessions.get(token)
    if session is None:
        return None
    if time.monotonic() > session.expiry:
        del _sessions[token]
        return None
    return session


def invalidate_session(token: str) -> None:
    _sessions.pop(token, None)


# ---------------------------------------------------------------------------
# FastAPI dependency — returns the SessionData for the request
# ---------------------------------------------------------------------------


def require_auth(authorization: Optional[str] = Header(default=None)) -> SessionData:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    session = get_session(token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session
