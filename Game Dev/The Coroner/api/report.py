"""
api/report.py — File and retrieve case reports.

POST /api/report/{case_id}   — File final report (once only)
GET  /api/report/{case_id}   — Retrieve filed report + result
"""
from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Case, Evidence, Killer, Report, Witness

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])


# ── Request / response schemas ─────────────────────────────────────────────

class FileReportBody(BaseModel):
    case_id: int
    suspect_name: str = Field(..., min_length=1, max_length=128)
    cause_of_death: str = Field(..., min_length=1, max_length=256)
    method: str = Field(..., min_length=1, max_length=256)
    motive: str = Field(..., min_length=1, max_length=256)
    evidence_cited: list[int] = Field(default_factory=list)


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_case_or_404(case_id: int, db: Session) -> Case:
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


# ── POST /api/report/{case_id} ─────────────────────────────────────────────

@router.post("/{case_id}")
async def file_report(
    case_id: int,
    body: FileReportBody,
    db: Annotated[Session, Depends(get_db)],
):
    """
    File the player's final report. Can only be filed once per case.
    Runs scorer and returns full result immediately.
    """
    if case_id != body.case_id:
        raise HTTPException(status_code=400, detail="case_id mismatch")

    case = _get_case_or_404(case_id, db)

    if case.is_closed:
        # Already filed — return the stored result
        report = db.query(Report).filter(Report.case_id == case_id).first()
        if report and report.result_json:
            return {"already_filed": True, "result": report.get_result()}
        raise HTTPException(status_code=409, detail="Case already closed but no result found")

    if not case.killer:
        raise HTTPException(status_code=400, detail="Case generation not complete")

    # Load ground truth
    killer: Killer = case.killer
    killer_witness: Witness = db.query(Witness).filter(Witness.id == killer.witness_id).first()
    if not killer_witness:
        raise HTTPException(status_code=500, detail="Killer witness record missing")

    killer_name = killer_witness.name
    killer_method_detail = killer.method_detail
    killer_motive = killer.motive

    # Entropy method = cause of death ground truth (e.g. "poisoning", "blunt_force")
    entropy = case.get_entropy()
    entropy_method: str = entropy.get("method", killer_method_detail)
    # Make it human-readable (underscore → space)
    entropy_method = entropy_method.replace("_", " ")

    # Load all evidence for this case
    evidence_rows: list[Evidence] = (
        db.query(Evidence).filter(Evidence.case_id == case_id).all()
    )
    evidence_items = [
        {"id": ev.id, "item": ev.item, "true_implication": ev.true_implication}
        for ev in evidence_rows
    ]

    # Validate evidence IDs belong to this case
    valid_evidence_ids = {ev.id for ev in evidence_rows}
    bad_ids = [eid for eid in body.evidence_cited if eid not in valid_evidence_ids]
    if bad_ids:
        raise HTTPException(status_code=400, detail=f"Unknown evidence IDs: {bad_ids}")

    # ── Run scorer ──────────────────────────────────────────────────────────
    from scoring.scorer import score_report
    try:
        result = await score_report(
            suspect_name=body.suspect_name,
            cause_of_death=body.cause_of_death,
            method=body.method,
            motive=body.motive,
            evidence_cited_ids=body.evidence_cited,
            killer_name=killer_name,
            killer_method_detail=killer_method_detail,
            killer_motive=killer_motive,
            entropy_method=entropy_method,
            evidence_items=evidence_items,
        )
    except Exception as e:
        logger.error(f"Scoring failed for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Scoring error: {e}")

    # ── Persist report ──────────────────────────────────────────────────────
    # Use a fresh session (this runs after async scoring)
    fresh_db = next(get_db())
    try:
        report_row = Report(
            case_id=case_id,
            session_token=case.session_token,
            suspect_name=body.suspect_name,
            cause_of_death=body.cause_of_death,
            method=body.method,
            motive=body.motive,
            evidence_cited=json.dumps(body.evidence_cited),
            result_json=json.dumps(result),
        )
        fresh_db.add(report_row)

        # Close the case
        db_case = fresh_db.query(Case).filter(Case.id == case_id).first()
        if db_case:
            db_case.is_closed = True

        fresh_db.commit()
        logger.info(f"Report filed for case {case_id}: verdict={result['verdict']}, score={result['score']}")
    except Exception as e:
        fresh_db.rollback()
        logger.error(f"Failed to save report for case {case_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save report")
    finally:
        fresh_db.close()

    return {"already_filed": False, "result": result}


# ── GET /api/report/{case_id} ──────────────────────────────────────────────

@router.get("/{case_id}")
async def get_report(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Return a previously filed report + result. 404 if not yet filed."""
    case = _get_case_or_404(case_id, db)

    report = db.query(Report).filter(Report.case_id == case_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not yet filed for this case")

    return {
        "case_id": case_id,
        "filed_at": report.filed_at.isoformat(),
        "suspect_name": report.suspect_name,
        "cause_of_death": report.cause_of_death,
        "method": report.method,
        "motive": report.motive,
        "evidence_cited": report.get_evidence_cited(),
        "result": report.get_result(),
    }
