"""
Case generation pipeline — orchestrates all phases end-to-end.
Runs as a FastAPI BackgroundTask. Updates CaseGenerationJob throughout.
Progress SSE reads from CaseGenerationJob.progress_pct + status.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import string
import uuid
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from config import GITHUB_TIMEOUT, MAX_GENERATION_RETRIES
from database import get_db
from generation.components import generate_components
from generation.core import generate_core_case
from generation.entropy import EntropySeed, record_session, sample_entropy
from generation.schemas import ComponentsSchema, CoreCaseSchema
from generation.validator import validate_case
from generation.voice_pass import generate_voice_prompts
from llm.model_router import DailyLimitExhausted

logger = logging.getLogger(__name__)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _update_job(db: Session, job_id: int, **kwargs) -> None:
    from models import CaseGenerationJob
    db.query(CaseGenerationJob).filter(CaseGenerationJob.id == job_id).update(kwargs)
    db.commit()


def _create_db_case(
    db: Session,
    job_id: int,
    session_token: str,
    seed: EntropySeed,
    core: CoreCaseSchema,
    components: ComponentsSchema,
    voice_prompts: dict[str, str],
) -> int:
    """Commit everything to DB. Returns case.id."""
    from models import (
        BoardState,
        Case,
        Evidence,
        Killer,
        RedHerring,
        Victim,
        Witness,
    )

    world_skeleton = json.dumps({
        "core": core.model_dump(),
        "components": components.model_dump(),
    })

    case = Case(
        session_token=session_token,
        generation_job_id=job_id,
        entropy_seed=seed.to_json(),
        world_skeleton=world_skeleton,
        is_active=True,
        is_closed=False,
    )
    db.add(case)
    db.flush()  # get case.id

    # Victim
    victim = Victim(
        case_id=case.id,
        name=core.victim.name,
        age=core.victim.age,
        occupation=core.victim.occupation,
        traits=json.dumps(core.victim.traits),
        secrets=json.dumps(core.victim.secrets),
        portrait_seed=str(random.randint(1000, 9999)),
    )
    db.add(victim)
    db.flush()

    # Witnesses (killer is one of them)
    witness_map: dict[str, int] = {}  # name → db id
    for w_schema in components.witnesses:
        is_killer = w_schema.name == core.killer.witness_name
        voice_prompt = voice_prompts.get(w_schema.name, "")
        witness = Witness(
            case_id=case.id,
            name=w_schema.name,
            occupation=w_schema.occupation,
            relationship_to_victim=w_schema.relationship_to_victim,
            true_knowledge=json.dumps(w_schema.true_knowledge),
            concealed_knowledge=json.dumps(w_schema.concealed_knowledge),
            their_lie=w_schema.their_lie,
            speech_pattern=w_schema.speech_pattern,
            voice_system_prompt=voice_prompt,
            portrait_seed=str(random.randint(1000, 9999)),
        )
        db.add(witness)
        db.flush()
        witness_map[w_schema.name] = witness.id

    # Killer record (links to Witness)
    killer_witness_id = witness_map.get(core.killer.witness_name)
    killer = Killer(
        case_id=case.id,
        witness_id=killer_witness_id,
        motive=core.killer.motive,
        method_detail=core.killer.method_detail,
        opportunity_window=core.killer.opportunity_window,
        alibi_claim=core.killer.alibi_claim,
        alibi_weakness=core.killer.alibi_weakness,
        deduction_chain=json.dumps(core.killer.deduction_chain),
    )
    db.add(killer)
    db.flush()

    # Evidence
    for e_schema in components.evidence:
        evidence = Evidence(
            case_id=case.id,
            item=e_schema.item,
            location=e_schema.location,
            examine_text=e_schema.examine_text,
            true_implication=e_schema.true_implication,
            misleading_reading=e_schema.misleading_reading,
            is_examined=False,
            player_annotation="",
        )
        db.add(evidence)
    db.flush()

    # Red Herrings — structural assignment via assigned_witness_id
    for rh_schema in components.red_herrings:
        assigned_id = witness_map.get(rh_schema.assigned_witness_name)
        rh = RedHerring(
            case_id=case.id,
            suspect_name=rh_schema.suspect_name,
            suspicious_behavior=rh_schema.suspicious_behavior,
            innocent_explanation=rh_schema.innocent_explanation,
            resolution_clue=rh_schema.resolution_clue,
            assigned_witness_id=assigned_id,
        )
        db.add(rh)
    db.flush()

    # Board State (empty canvas)
    board = BoardState(
        case_id=case.id,
        state_json="{}",
        server_version=0,
    )
    db.add(board)

    db.commit()
    logger.info(f"Case {case.id} committed to DB (job {job_id})")
    return case.id


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def run_generation_pipeline(job_id: int, session_token: str) -> None:
    """
    Full case generation pipeline. Runs as a background task.
    Reads/writes its own DB session (not request-scoped).
    """
    db: Session = next(get_db())
    try:
        await _pipeline(db, job_id, session_token)
    except Exception as e:
        logger.exception(f"Pipeline crashed for job {job_id}: {e}")
        _update_job(
            db, job_id,
            status="failed",
            error_detail=str(e)[:1000],
            progress_pct=0,
        )
    finally:
        db.close()


async def _pipeline(db: Session, job_id: int, session_token: str) -> None:
    _update_job(db, job_id, status="pending", progress_pct=0)

    seed = sample_entropy(db)
    logger.info(f"Job {job_id} — entropy: {seed}")

    last_error: str = ""

    for attempt in range(1, MAX_GENERATION_RETRIES + 1):
        try:
            _update_job(db, job_id, status="generating_core", progress_pct=10, attempt=attempt)

            # Phase 2a — core case
            core: CoreCaseSchema = await asyncio.wait_for(
                generate_core_case(seed), timeout=90
            )
            _update_job(db, job_id, progress_pct=30)

            # Phase 2b — components
            _update_job(db, job_id, status="generating_witnesses", progress_pct=35)
            components: ComponentsSchema = await asyncio.wait_for(
                generate_components(seed, core), timeout=90
            )

            # SSE progress: spread witnesses 35→70
            num_w = len(components.witnesses)
            progress_per_w = int(35 / max(num_w, 1))
            _update_job(db, job_id, progress_pct=70)

            # Phase 3 — validation
            _update_job(db, job_id, status="validating", progress_pct=72)
            result = validate_case(core, components)
            if not result.passed:
                raise ValueError(f"Validation failed: {'; '.join(result.errors)}")
            _update_job(db, job_id, progress_pct=85)

            # Phase 4 — voice pass
            _update_job(db, job_id, status="voice_pass", progress_pct=86)
            voice_prompts = await asyncio.wait_for(
                generate_voice_prompts(core, components),
                timeout=GITHUB_TIMEOUT * len(components.witnesses),
            )
            _update_job(db, job_id, progress_pct=95)

            # Commit to DB
            case_id = _create_db_case(
                db, job_id, session_token, seed, core, components, voice_prompts
            )

            # Record generation session for anti-repeat (only on success)
            record_session(db, seed)

            _update_job(
                db, job_id,
                status="done",
                progress_pct=100,
                error_detail=None,
            )
            # Store case_id on the job for the SSE stream to redirect to
            from models import CaseGenerationJob
            db.query(CaseGenerationJob).filter(CaseGenerationJob.id == job_id).update(
                {"case_id": case_id}
            )
            db.commit()
            logger.info(f"Job {job_id} complete → case {case_id}")
            return

        except asyncio.TimeoutError:
            last_error = f"Attempt {attempt}: LLM call timed out"
            logger.warning(last_error)
        except DailyLimitExhausted as e:
            # Not retryable — all models exhausted for the day
            err = f"DAILY_LIMIT_EXHAUSTED: {e}"
            logger.warning(f"Job {job_id}: {err}")
            _update_job(db, job_id, status="failed", progress_pct=0, error_detail=err[:1000])
            return
        except Exception as e:
            last_error = f"Attempt {attempt}: {type(e).__name__}: {str(e)[:300]}"
            logger.warning(last_error)
            _update_job(db, job_id, error_detail=last_error[:1000])

        if attempt < MAX_GENERATION_RETRIES:
            # Resample entropy on retry to get a different case
            seed = sample_entropy(db)
            await asyncio.sleep(1)

    # All retries exhausted
    _update_job(
        db, job_id,
        status="failed",
        progress_pct=0,
        error_detail=last_error[:1000],
    )
    logger.error(f"Job {job_id} failed after {MAX_GENERATION_RETRIES} attempts: {last_error}")
