"""
Witness interview API — SSE streaming via phi4-mini.
Each interview turn sends ONLY that witness's knowledge slice + rolling 6-turn history.
Never leaks full case JSON or killer identity to the model context.

POST /api/witness/{witness_id}/interview   — send a message, stream response
GET  /api/witness/{witness_id}/history     — full interview history for this witness
DELETE /api/witness/{witness_id}/history   — reset interview (fresh start)
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from llm.github_client import get_github_client
from llm.model_router import DailyLimitExhausted

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/witness", tags=["witness"])

HISTORY_WINDOW = 4  # last N turns (user+assistant pairs) kept in context — trimmed for token efficiency


class MessageRequest(BaseModel):
    message: str
    case_id: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_witness_or_404(db: Session, witness_id: int, case_id: int):
    from models import Witness
    w = db.query(Witness).filter(
        Witness.id == witness_id,
        Witness.case_id == case_id,
    ).first()
    if not w:
        raise HTTPException(status_code=404, detail="Witness not found in this case")
    return w


def _load_history(db: Session, case_id: int, witness_id: int) -> list[dict]:
    """Load last HISTORY_WINDOW*2 messages (pairs) as OpenAI-style dicts."""
    from models import InterviewMessage
    rows = (
        db.query(InterviewMessage)
        .filter(
            InterviewMessage.case_id == case_id,
            InterviewMessage.witness_id == witness_id,
        )
        .order_by(InterviewMessage.created_at.asc())
        .all()
    )
    # Keep only last HISTORY_WINDOW turns (each turn = user + assistant)
    messages = [{"role": r.role, "content": r.content} for r in rows]
    max_messages = HISTORY_WINDOW * 2
    return messages[-max_messages:] if len(messages) > max_messages else messages


def _save_message(db: Session, case_id: int, witness_id: int, role: str, content: str) -> None:
    from models import InterviewMessage
    db.add(InterviewMessage(
        case_id=case_id,
        witness_id=witness_id,
        role=role,
        content=content,
    ))
    db.commit()


def _build_system_prompt(witness, case) -> str:
    """
    Build the full system prompt for this witness interview.
    Uses the cached voice_system_prompt from DB (generated during voice pass).
    Injects the full witness roster + timeline so the LLM never invents people.
    """
    voice_prompt = witness.voice_system_prompt or ""

    true_knowledge = json.loads(witness.true_knowledge or "[]")
    concealed_knowledge = json.loads(witness.concealed_knowledge or "[]")

    # Pull full world context from skeleton
    skeleton = json.loads(case.world_skeleton or "{}")
    core = skeleton.get("core", {})
    components = skeleton.get("components", {})

    victim_name = core.get("victim", {}).get("name", "the victim")
    case_title = core.get("case_title", "this case")

    # Full witness roster — anchors names so LLM never invents characters
    all_witnesses = components.get("witnesses", [])
    roster_lines = []
    for w in all_witnesses:
        n = w.get("name", "?")
        occ = w.get("occupation", "")
        rel = w.get("relationship_to_victim", "")
        roster_lines.append(f"  - {n} ({occ}) — {rel}")
    roster_str = "\n".join(roster_lines) if roster_lines else "  - (none listed)"

    # Timeline — so the witness is consistent about events
    timeline_events = core.get("causal_timeline", [])
    timeline_lines = []
    for evt in timeline_events:
        t = evt.get("time", "?")
        e = evt.get("event", "")
        known_by = evt.get("known_by", [])
        kb_str = f" [known by: {', '.join(known_by)}]" if known_by else ""
        timeline_lines.append(f"  {t}: {e}{kb_str}")
    timeline_str = "\n".join(timeline_lines) if timeline_lines else "  - (not specified)"

    # Filter timeline to only events this witness was listed as knowing
    witness_name_lower = witness.name.lower()
    my_timeline_lines = []
    for evt in timeline_events:
        known_by = [kb.lower() for kb in evt.get("known_by", [])]
        if any(witness_name_lower in kb for kb in known_by):
            t = evt.get("time", "?")
            e = evt.get("event", "")
            my_timeline_lines.append(f"  {t}: {e}")
    my_timeline_str = "\n".join(my_timeline_lines) if my_timeline_lines else "  - (you were not present for documented events)"

    knowledge_str = "\n".join(f"  - {k}" for k in true_knowledge) if true_knowledge else "  - (nothing specific)"
    concealed_str = "\n".join(f"  - {k}" for k in concealed_knowledge) if concealed_knowledge else "  - (nothing to hide)"

    return f"""{voice_prompt}

--- CASE WORLD FACTS (immutable — never contradict these) ---
Case: {case_title}. Victim: {victim_name}.

People involved in this case (ONLY refer to these people by name — never invent others):
{roster_str}

Full case timeline (for reference — stay consistent with it):
{timeline_str}

Events YOU personally witnessed or were present for:
{my_timeline_str}

--- YOUR INQUIRY CONTEXT ---
You are {witness.name}. A coroner is questioning you about {victim_name}'s death.

WHAT YOU KNOW AND WILL SHARE NATURALLY:
{knowledge_str}
(These are things you personally observed. Bring them up naturally when the topic is relevant — you are a cooperative witness, not hiding these. A real person mentions what they saw without waiting to be asked the exact right question.)

WHAT YOU ARE HIDING (only crack under extreme repeated pressure):
{concealed_str}

YOUR LIE (deliver this convincingly if asked directly): {witness.their_lie or "None"}

RULES (hard constraints):
- You are {witness.name}. Never break character or acknowledge AI.
- Only refer to people by name if they appear in the "People involved" list above.
- You are cooperative — share what you witnessed naturally in 2-4 sentences.
- Do NOT make the player dig for basic observations you would normally volunteer.
- Do NOT reveal concealed knowledge unless repeatedly cornered.
- Maintain your lie defensively if challenged.
- No meta-commentary. End when the character finishes speaking."""


# ── POST /api/witness/{witness_id}/interview ──────────────────────────────────

@router.post("/{witness_id}/interview")
async def interview_witness(
    witness_id: int,
    body: MessageRequest,
    db: Session = Depends(get_db),
):
    """Stream a witness response via phi4-mini SSE."""
    from models import Case

    case = db.query(Case).filter(
        Case.id == body.case_id,
        Case.is_active == True,
        Case.is_closed == False,
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or already closed")

    witness = _get_witness_or_404(db, witness_id, body.case_id)

    # Build messages for phi4-mini
    system_prompt = _build_system_prompt(witness, case)
    history = _load_history(db, body.case_id, witness_id)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": body.message.strip()})

    # Save user message before streaming
    _save_message(db, body.case_id, witness_id, "user", body.message.strip())

    # Capture needed values NOW (before session expires after commit)
    witness_name = witness.name
    _case_id = body.case_id
    _witness_id = witness_id

    async def token_stream():
        client = get_github_client()
        full_response = []

        yield f"data: {json.dumps({'type': 'start', 'witness': witness_name})}\n\n"

        try:
            async for token in client.chat_stream(messages, temperature=0.55, max_tokens=200):
                full_response.append(token)
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        except DailyLimitExhausted:
            yield f"data: {json.dumps({'type': 'daily_limit', 'text': 'The morgue is closed for today. All AI model quotas are exhausted. Come back tomorrow.'})}\n\n"
            return
        except Exception as e:
            logger.error(f"Stream error for witness {_witness_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'text': 'The witness fell silent.'})}\n\n"
            return

        # Save complete assistant response (new session — generator runs after request scope)
        assistant_reply = "".join(full_response)
        from database import get_db as _get_db
        stream_db = next(_get_db())
        try:
            _save_message(stream_db, _case_id, _witness_id, "assistant", assistant_reply)
        finally:
            stream_db.close()

        yield f"data: {json.dumps({'type': 'done', 'witness_id': _witness_id})}\n\n"

    return StreamingResponse(
        token_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /api/witness/{witness_id}/history ─────────────────────────────────────

@router.get("/{witness_id}/history")
async def get_history(witness_id: int, case_id: int, db: Session = Depends(get_db)):
    from models import InterviewMessage
    rows = (
        db.query(InterviewMessage)
        .filter(
            InterviewMessage.case_id == case_id,
            InterviewMessage.witness_id == witness_id,
        )
        .order_by(InterviewMessage.created_at.asc())
        .all()
    )
    return [{"role": r.role, "content": r.content, "at": r.created_at.isoformat()} for r in rows]


# ── DELETE /api/witness/{witness_id}/history ──────────────────────────────────

@router.delete("/{witness_id}/history")
async def reset_history(witness_id: int, case_id: int, db: Session = Depends(get_db)):
    from models import InterviewMessage
    db.query(InterviewMessage).filter(
        InterviewMessage.case_id == case_id,
        InterviewMessage.witness_id == witness_id,
    ).delete()
    db.commit()
    return {"deleted": True}
