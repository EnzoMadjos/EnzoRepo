from __future__ import annotations

import json
import time
import uuid
from datetime import date
from typing import Optional

import auth
import config
from api.deps import get_db
from fastapi import APIRouter, Depends, HTTPException
from models import CertificateType, Resident
from pydantic import BaseModel
from sqlalchemy.orm import Session

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


def _ensure_demo_seed(db: Session) -> None:
    """Seed sample cert types and residents if the database is empty."""
    try:
        if db.query(CertificateType).count() == 0:
            db.add_all([
                CertificateType(id=str(uuid.uuid4()), code="BCL", name="Barangay Clearance", template="clearance"),
                CertificateType(id=str(uuid.uuid4()), code="COR", name="Certificate of Residency", template="residency"),
                CertificateType(id=str(uuid.uuid4()), code="COI", name="Certificate of Indigency", template="indigency"),
            ])
            db.commit()
        if db.query(Resident).count() == 0:
            db.add_all([
                Resident(id=str(uuid.uuid4()), first_name="Juan", last_name="Dela Cruz", birthdate=date(1985, 3, 14), contact_number="09171234567"),
                Resident(id=str(uuid.uuid4()), first_name="Maria", last_name="Santos", middle_name="Reyes", birthdate=date(1992, 7, 22), contact_number="09281234567"),
                Resident(id=str(uuid.uuid4()), first_name="Jose", last_name="Rizal", middle_name="Protacio", birthdate=date(1978, 6, 19)),
                Resident(id=str(uuid.uuid4()), first_name="Ana", last_name="Bautista", birthdate=date(2000, 1, 5), contact_number="09391234567"),
                Resident(id=str(uuid.uuid4()), first_name="Pedro", last_name="Garcia", middle_name="Lim", birthdate=date(1965, 11, 30)),
            ])
            db.commit()
    except Exception:
        db.rollback()  # don't block demo session if seed fails


@router.post("/api/demo/start")
def demo_start(db: Session = Depends(get_db)):
    """Auto-create a read/write clerk demo session — no credentials required."""
    _ensure_demo_seed(db)
    token = auth.create_session(
        username="demo_visitor",
        role="clerk",
        display_name="Demo Visitor",
    )
    return {"token": token, "username": "Demo Visitor", "role": "clerk"}
