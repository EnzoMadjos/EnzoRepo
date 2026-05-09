"""
Specialist consult API — pathologist and toxicologist via phi4-mini SSE.
Each specialist has a distinct persona and knowledge scope.
Consult responses are logged in ConsultLog for player review.

POST /api/consult/{case_id}   — stream a consult response
GET  /api/consult/{case_id}   — list all consults for this case
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from llm.github_client import get_github_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/consult", tags=["consult"])

VALID_SPECIALISTS = {"pathologist", "toxicologist"}

_SPECIALIST_PROMPTS = {
    "pathologist": """You are Dr. Harlow, attending pathologist.
Clinical, precise, dry authority. Domain: cause of death, wound patterns, TOD window, lividity, rigor mortis.
No suspect/motive speculation — redirect: "That's outside my remit."
3-4 sentences. Use medical terms but briefly explain them.
You have examined the body and physical evidence for this case.""",

    "toxicologist": """You are Dr. Avery, forensic toxicologist.
Careful and precise — use "consistent with" / "indicative of" rather than absolutes.
Domain: substances in tissue/blood, drug interactions, poisoning, alcohol, time-of-administration windows.
No wound/suspect/motive comments — redirect: "You'd want the pathologist for that."
3-4 sentences. Cite sample types naturally (vitreous humor, liver tissue, blood).""",
}


class ConsultRequest(BaseModel):
    specialist: str   # "pathologist" | "toxicologist"
    question: str


def _get_case_context(case) -> str:
    """Extract minimal forensic context for the specialist — no killer identity."""
    skeleton = json.loads(case.world_skeleton or "{}")
    core = skeleton.get("core", {})
    victim = core.get("victim", {})
    timeline = core.get("causal_timeline", [])

    timeline_str = "\n".join(
        f"  {e.get('time', '?')}: {e.get('event', '')}"
        for e in timeline[:5]
    )

    return f"""Case: {core.get('case_title', 'Unknown')}
Victim: {victim.get('name', 'Unknown')}, {victim.get('age', '?')} years old, {victim.get('occupation', 'unknown occupation')}

Known timeline:
{timeline_str}"""


# ── POST /api/consult/{case_id} ───────────────────────────────────────────────

@router.post("/{case_id}")
async def consult_specialist(
    case_id: int,
    body: ConsultRequest,
    db: Session = Depends(get_db),
):
    """Stream a specialist consult response and log it."""
    if body.specialist not in VALID_SPECIALISTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown specialist. Valid: {sorted(VALID_SPECIALISTS)}"
        )

    from models import Case, ConsultLog

    case = db.query(Case).filter(
        Case.id == case_id,
        Case.is_active == True,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    system_prompt = _SPECIALIST_PROMPTS[body.specialist]
    case_context = _get_case_context(case)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Case context:\n{case_context}\n\nCoroner's question: {body.question.strip()}",
        },
    ]

    # Capture case_id before session scope ends in generator
    _case_id = case_id
    _specialist = body.specialist
    _question = body.question.strip()

    async def stream_response():
        client = get_github_client()
        full_response: list[str] = []

        yield f"data: {json.dumps({'type': 'start', 'specialist': _specialist})}\n\n"

        try:
            async for token in client.chat_stream(messages, temperature=0.7, max_tokens=250):
                full_response.append(token)
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        except Exception as e:
            logger.error(f"Consult stream error ({_specialist}, case {_case_id}): {e}")
            yield f"data: {json.dumps({'type': 'error', 'text': 'Specialist unavailable.'})}\n\n"
            return

        # Persist to ConsultLog (new session — generator runs after request scope)
        full_text = "".join(full_response)
        from database import get_db as _get_db
        stream_db = next(_get_db())
        log_id = None
        try:
            from models import ConsultLog
            log = ConsultLog(
                case_id=_case_id,
                specialist=_specialist,
                question=_question[:1000],
                response=full_text[:4000],
            )
            stream_db.add(log)
            stream_db.commit()
            stream_db.refresh(log)
            log_id = log.id
        finally:
            stream_db.close()

        yield f"data: {json.dumps({'type': 'done', 'log_id': log_id})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /api/consult/{case_id} ────────────────────────────────────────────────

@router.get("/{case_id}")
async def list_consults(case_id: int, db: Session = Depends(get_db)):
    from models import ConsultLog
    logs = (
        db.query(ConsultLog)
        .filter(ConsultLog.case_id == case_id)
        .order_by(ConsultLog.created_at.asc())
        .all()
    )
    return [
        {
            "id": l.id,
            "specialist": l.specialist,
            "question": l.question,
            "response": l.response,
            "at": l.created_at.isoformat(),
        }
        for l in logs
    ]
