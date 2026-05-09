"""
Evidence API — examine and annotate evidence items.

POST /api/evidence/{evidence_id}/examine   — reveal examine_text (marks as examined)
PATCH /api/evidence/{evidence_id}/annotate — save player's freeform annotation
GET  /api/evidence/{evidence_id}           — get single evidence item
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/evidence", tags=["evidence"])


class AnnotateRequest(BaseModel):
    case_id: int
    annotation: str


class ExamineRequest(BaseModel):
    case_id: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_evidence_or_404(db: Session, evidence_id: int, case_id: int):
    from models import Evidence
    e = db.query(Evidence).filter(
        Evidence.id == evidence_id,
        Evidence.case_id == case_id,
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found in this case")
    return e


def _evidence_dict(e, full: bool = False) -> dict:
    d = {
        "id": e.id,
        "case_id": e.case_id,
        "item": e.item,
        "location": e.location,
        "is_examined": e.is_examined,
        "player_annotation": e.player_annotation or "",
    }
    if e.is_examined or full:
        d["examine_text"] = e.examine_text
        d["misleading_reading"] = e.misleading_reading
    return d


# ── POST /api/evidence/{evidence_id}/examine ──────────────────────────────────

@router.post("/{evidence_id}/examine")
async def examine_evidence(
    evidence_id: int,
    body: ExamineRequest,
    db: Session = Depends(get_db),
):
    """
    Mark evidence as examined and reveal its examine_text + misleading_reading.
    Idempotent — safe to call multiple times.
    """
    e = _get_evidence_or_404(db, evidence_id, body.case_id)

    if not e.is_examined:
        e.is_examined = True
        db.commit()
        db.refresh(e)
        logger.info(f"Evidence {evidence_id} examined (case {body.case_id})")

    return _evidence_dict(e)


# ── PATCH /api/evidence/{evidence_id}/annotate ────────────────────────────────

@router.patch("/{evidence_id}/annotate")
async def annotate_evidence(
    evidence_id: int,
    body: AnnotateRequest,
    db: Session = Depends(get_db),
):
    """Save or update the player's freeform annotation on an evidence item."""
    e = _get_evidence_or_404(db, evidence_id, body.case_id)

    # Clamp annotation length — no essays please
    e.player_annotation = body.annotation[:500]
    db.commit()

    return {"id": e.id, "player_annotation": e.player_annotation}


# ── GET /api/evidence/{evidence_id} ──────────────────────────────────────────

@router.get("/{evidence_id}")
async def get_evidence(evidence_id: int, case_id: int, db: Session = Depends(get_db)):
    e = _get_evidence_or_404(db, evidence_id, case_id)
    return _evidence_dict(e)
