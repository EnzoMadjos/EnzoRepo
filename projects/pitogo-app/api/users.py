from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import app_logger
import auth
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])


class CreateUserIn(BaseModel):
    username: str
    password: str
    role: str = "clerk"
    display_name: Optional[str] = None


class UpdateUserIn(BaseModel):
    role: Optional[str] = None
    display_name: Optional[str] = None


class ChangePasswordIn(BaseModel):
    new_password: str
    current_password: Optional[str] = None


def _load_users() -> dict:
    return auth._load_users()


def _save_users(users: dict) -> None:
    path: Path = auth._USERS_FILE
    path.write_text(json.dumps(users, indent=2), encoding="utf-8")


@router.get("/")
def list_users(
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    session: auth.SessionData = Depends(auth.require_auth),
):
    """List users with optional search and pagination. Admin only."""
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    users = _load_users()
    items = []
    for uname, u in users.items():
        items.append(
            {
                "username": uname,
                "role": u.get("role"),
                "display_name": u.get("display_name"),
            }
        )

    # search
    if q:
        ql = q.lower()
        items = [
            it
            for it in items
            if ql in it["username"].lower()
            or (it.get("display_name") and ql in str(it.get("display_name")).lower())
        ]

    # pagination bounds
    try:
        per_page = max(1, min(int(per_page), 500))
    except Exception:
        per_page = 50
    page = max(1, int(page or 1))
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]
    return {"items": page_items, "page": page, "per_page": per_page, "total": total}


@router.get("/me")
def get_me(session: auth.SessionData = Depends(auth.require_auth)):
    return {
        "username": session.username,
        "role": session.role,
        "display_name": session.display_name,
    }


@router.post("/", status_code=201)
def create_user(
    body: CreateUserIn, session: auth.SessionData = Depends(auth.require_auth)
):
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    users = _load_users()
    uname = (body.username or "").strip()
    if not uname:
        raise HTTPException(status_code=422, detail="username required")
    # normalize
    uname = uname
    if uname in users:
        raise HTTPException(status_code=400, detail="username already exists")
    # basic username validation
    if not re.match(r"^[A-Za-z0-9_.-]{2,64}$", uname):
        raise HTTPException(
            status_code=422, detail="username must be 2-64 chars, alnum and _.- allowed"
        )
    if not body.password or len(body.password) < 6:
        raise HTTPException(
            status_code=422, detail="password must be at least 6 characters"
        )
    if body.role not in ("admin", "clerk"):
        raise HTTPException(status_code=422, detail="role must be 'admin' or 'clerk'")
    users[body.username] = {
        "password_hash": auth._hash(body.password),
        "role": body.role,
        "display_name": body.display_name or body.username,
    }
    _save_users(users)
    app_logger.info("User created", username=session.username, new_user=body.username)
    return {
        "username": body.username,
        "role": body.role,
        "display_name": body.display_name,
    }


@router.put("/{username}")
def update_user(
    username: str,
    body: UpdateUserIn,
    session: auth.SessionData = Depends(auth.require_auth),
):
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    users = _load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="user not found")
    if body.role:
        # prevent removing last admin
        cur_role = users[username].get("role")
        if cur_role == "admin" and body.role != "admin":
            admins = [u for u in users.values() if u.get("role") == "admin"]
            if len(admins) <= 1:
                raise HTTPException(status_code=400, detail="cannot remove last admin")
        if body.role not in ("admin", "clerk"):
            raise HTTPException(
                status_code=422, detail="role must be 'admin' or 'clerk'"
            )
        users[username]["role"] = body.role
    if body.display_name is not None:
        users[username]["display_name"] = body.display_name
    _save_users(users)
    app_logger.info("User updated", username=session.username, target=username)
    return {
        "username": username,
        "role": users[username]["role"],
        "display_name": users[username].get("display_name"),
    }


@router.post("/{username}/password")
def change_password(
    username: str,
    body: ChangePasswordIn,
    session: auth.SessionData = Depends(auth.require_auth),
):
    users = _load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="user not found")

    # Admin can reset others' passwords without current_password
    if session.role == "admin" and session.username != username:
        users[username]["password_hash"] = auth._hash(body.new_password)
        _save_users(users)
        app_logger.info(
            "Password reset by admin", username=session.username, target=username
        )
        return {"status": "reset"}

    # Allow user to change own password with current_password
    if session.username != username:
        raise HTTPException(status_code=403, detail="forbidden")
    if not body.current_password:
        raise HTTPException(status_code=422, detail="current_password required")
    if users[username]["password_hash"] != auth._hash(body.current_password):
        raise HTTPException(status_code=400, detail="current password incorrect")
    users[username]["password_hash"] = auth._hash(body.new_password)
    _save_users(users)
    app_logger.info("Password changed", username=username)
    return {"status": "changed"}


@router.delete("/{username}")
def delete_user(username: str, session: auth.SessionData = Depends(auth.require_auth)):
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    users = _load_users()
    if username not in users:
        raise HTTPException(status_code=404, detail="user not found")
    # Prevent deleting last admin
    if users[username].get("role") == "admin":
        admins = [u for u in users.values() if u.get("role") == "admin"]
        if len(admins) <= 1:
            raise HTTPException(status_code=400, detail="cannot delete the last admin")
    users.pop(username)
    _save_users(users)
    app_logger.info("User deleted", username=session.username, target=username)
    return {"status": "deleted"}
