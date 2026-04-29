from __future__ import annotations

import json
import time
from typing import Optional

import auth
import config
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["demo", "feedback"])

_FEEDBACK_FILE = config.SECURE_DIR / "feedbacks.json"


class FeedbackIn(BaseModel):
    name: Optional[str] = None
    rating: int  # 1–5
    message: str


def _load() -> list:
    if not _FEEDBACK_FILE.exists():
        return []
    try:
        return json.loads(_FEEDBACK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    _FEEDBACK_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


@router.post("/api/feedback", status_code=201)
def submit_feedback(body: FeedbackIn):
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=422, detail="rating must be 1–5")
    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(status_code=422, detail="message is required")
    items = _load()
    entry = {
        "id": len(items) + 1,
        "name": (body.name or "").strip() or "Anonymous",
        "rating": body.rating,
        "message": msg,
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    items.append(entry)
    _save(items)
    return {"status": "submitted", "id": entry["id"]}


@router.get("/api/feedback")
def list_feedbacks(session: auth.SessionData = Depends(auth.require_auth)):
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return _load()


@router.post("/api/demo/start")
def demo_start():
    """Auto-create a read/write clerk demo session — no credentials required."""
    token = auth.create_session(
        username="demo_visitor",
        role="clerk",
        display_name="Demo Visitor",
    )
    return {"token": token, "username": "Demo Visitor", "role": "clerk"}
