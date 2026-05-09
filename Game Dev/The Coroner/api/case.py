"""
Case generation API.
POST /api/case/generate     — start a new case generation job
GET  /api/case/generate/{job_id}/stream  — SSE progress stream
GET  /api/case/{case_id}    — fetch full case data
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from generation.pipeline import run_generation_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/case", tags=["case"])

# ── Progress label map ─────────────────────────────────────────────────────

_STAGE_LABELS: dict[str, str] = {
    "pending":              "Recovering case files...",
    "generating_core":      "Reconstructing the scene...",
    "generating_witnesses": "Identifying witnesses...",
    "validating":           "Cross-referencing evidence...",
    "voice_pass":           "Profiling witnesses...",
    "done":                 "Case ready.",
    "failed":               "Case files corrupted — try again.",
}


# ── POST /api/case/generate ───────────────────────────────────────────────

@router.post("/generate")
async def start_generation(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new generation job and fire the background pipeline."""
    from models import CaseGenerationJob

    session_token = request.cookies.get("coroner_session", "")

    job = CaseGenerationJob(
        status="pending",
        attempt=0,
        progress_pct=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_generation_pipeline, job.id, session_token)

    return {
        "job_id": job.id,
        "stream_url": f"/api/case/generate/{job.id}/stream",
    }


# ── GET /api/case/generate/{job_id}/stream ────────────────────────────────

@router.get("/generate/{job_id}/stream")
async def stream_progress(job_id: int, db: Session = Depends(get_db)):
    """SSE stream — emits progress events until done or failed."""

    async def event_generator():
        poll_interval = 1.0  # seconds
        max_polls = 300      # 5 minutes max
        polls = 0

        while polls < max_polls:
            from models import CaseGenerationJob
            job = db.query(CaseGenerationJob).filter(
                CaseGenerationJob.id == job_id
            ).first()

            if not job:
                yield _sse({"error": "Job not found", "pct": 0, "label": "Error"})
                return

            label = _STAGE_LABELS.get(job.status, job.status)
            pct = job.progress_pct or 0

            if job.status == "done":
                yield _sse({
                    "status": "done",
                    "pct": 100,
                    "label": "Case ready.",
                    "case_id": job.case_id,
                    "redirect": f"/case/{job.case_id}",
                })
                return

            if job.status == "failed":
                yield _sse({
                    "status": "failed",
                    "pct": 0,
                    "label": "Case files corrupted — try again.",
                    "error": job.error_detail or "Unknown error",
                })
                return

            yield _sse({"status": job.status, "pct": pct, "label": label})

            db.expire_all()  # force re-read on next poll
            polls += 1
            await asyncio.sleep(poll_interval)

        yield _sse({"status": "failed", "pct": 0, "label": "Timed out waiting for case.", "error": "timeout"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ── GET /api/case/{case_id} ───────────────────────────────────────────────

@router.get("/{case_id}")
async def get_case(case_id: int, db: Session = Depends(get_db)):
    """Return full case data (player-visible only — no killer identity)."""
    from models import Case, Evidence, Witness

    case = db.query(Case).filter(Case.id == case_id, Case.is_active == True).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # World skeleton has full data — we strip killer identity for player view
    skeleton = json.loads(case.world_skeleton or "{}")
    core = skeleton.get("core", {})
    components = skeleton.get("components", {})

    # Witnesses — return name, occupation, relationship, speech_pattern only
    witnesses_public = [
        {
            "id": w.id,
            "name": w.name,
            "occupation": w.occupation,
            "relationship_to_victim": w.relationship_to_victim,
            "speech_pattern": w.speech_pattern,
            "portrait_seed": w.portrait_seed,
        }
        for w in db.query(Witness).filter(Witness.case_id == case_id).all()
    ]

    # Evidence — return public fields, player annotations
    evidence_public = [
        {
            "id": e.id,
            "item": e.item,
            "location": e.location,
            "examine_text": e.examine_text if e.is_examined else None,
            "misleading_reading": e.misleading_reading if e.is_examined else None,
            "is_examined": e.is_examined,
            "player_annotation": e.player_annotation,
        }
        for e in db.query(Evidence).filter(Evidence.case_id == case_id).all()
    ]

    victim = core.get("victim", {})
    return {
        "case_id": case_id,
        "case_title": core.get("case_title", "Unknown Case"),
        "is_closed": case.is_closed,
        "victim": {
            "name": victim.get("name"),
            "age": victim.get("age"),
            "occupation": victim.get("occupation"),
            "traits": victim.get("traits", []),
            "portrait_seed": skeleton.get("victim_portrait_seed", 1234),
        },
        "witnesses": witnesses_public,
        "evidence": evidence_public,
        "timeline": core.get("causal_timeline", []),
        "setting": json.loads(case.entropy_seed or "{}").get("setting", "unknown"),
    }
