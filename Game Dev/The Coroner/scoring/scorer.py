"""
scoring/scorer.py — Score a player report against the ground truth.

Scoring logic:
  - perpetrator: phi4-mini fuzzy name match (handles partial names, titles, variants)
  - cause_of_death: phi4-mini semantic match
  - method: phi4-mini semantic match
  - motive: phi4-mini semantic match
  - evidence: each cited evidence item is shown with its revealed true_implication;
    relevance = true_implication mentions the killer or the method (keyword check first,
    phi4-mini fallback for ambiguous cases).

Result structure:
  {
    "perpetrator": {"yours": str, "actual": str, "correct": bool},
    "cause_of_death": {"yours": str, "actual": str, "correct": bool},
    "method": {"yours": str, "actual": str, "correct": bool},
    "motive": {"yours": str, "actual": str, "correct": bool},
    "evidence": [
      {
        "id": int,
        "item": str,
        "true_implication": str,
        "player_cited": bool,
        "is_key_evidence": bool,    # True = directly implicates killer/method
        "player_was_right": bool    # True = player cited this key evidence
      },
      ...
    ],
    "score": int,         # 0-100
    "verdict": str        # "CORRECT VERDICT" | "PARTIAL" | "WRONG"
  }
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Prompt templates ───────────────────────────────────────────────────────

_FIELD_SCORE_SYSTEM = """Scoring judge for a forensic mystery game.
Given a ground truth and player answer, return ONLY: {"correct": true/false, "reason": "one sentence"}
Name match: accept partial names, titles, common variants.
Other fields: accept synonyms and paraphrases if the core meaning matches."""

_EVIDENCE_RELEVANCE_SYSTEM = """Scoring judge for a forensic mystery game.
Return ONLY: {"is_key_evidence": true/false}
is_key_evidence=true if the evidence implication directly connects to the killer OR murder method."""


async def _llm_json(system: str, user: str, timeout: int = 30) -> dict:
    """Call gpt-4.1-mini (GitHub Models), return parsed JSON. Raises on failure."""
    from llm.github_client import get_github_client
    client = get_github_client()
    return await client.chat_json_interactive(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=150,
    )


def _keyword_match(text: str, keywords: list[str]) -> bool:
    """True if ANY keyword appears in text (case-insensitive)."""
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


async def _score_field(field_name: str, yours: str, actual: str) -> bool:
    """phi4-mini fuzzy match for a single field. Falls back to False on error."""
    user_msg = (
        f'Field: {field_name}\n'
        f'Actual answer: "{actual}"\n'
        f'Player answer: "{yours}"\n'
        'Are these essentially the same?'
    )
    try:
        result = await _llm_json(_FIELD_SCORE_SYSTEM, user_msg, timeout=20)
        return bool(result.get("correct", False))
    except Exception as e:
        logger.warning(f"_score_field({field_name}) failed: {e}. Falling back to False.")
        return False


async def _is_key_evidence(true_implication: str, killer_name: str, method: str) -> bool:
    """Determine if evidence directly implicates killer or method."""
    # Fast keyword check first — avoid LLM call when obvious
    keywords = [killer_name.split()[0], killer_name.split()[-1], method[:20]]
    if _keyword_match(true_implication, keywords):
        return True

    user_msg = (
        f'Evidence true implication: "{true_implication}"\n'
        f'Killer: "{killer_name}"\n'
        f'Method: "{method}"\n'
        'Is this evidence key?'
    )
    try:
        result = await _llm_json(_EVIDENCE_RELEVANCE_SYSTEM, user_msg, timeout=15)
        return bool(result.get("is_key_evidence", False))
    except Exception as e:
        logger.warning(f"_is_key_evidence failed: {e}. Falling back to False.")
        return False


async def score_report(
    suspect_name: str,
    cause_of_death: str,
    method: str,
    motive: str,
    evidence_cited_ids: list[int],
    killer_name: str,
    killer_method_detail: str,
    killer_motive: str,
    entropy_method: str,           # seed method e.g. "poisoning" — used as cause_of_death ground truth
    evidence_items: list[dict],    # [{"id": int, "item": str, "true_implication": str}, ...]
) -> dict:
    """
    Score all fields and build the full result dict.
    evidence_items: ALL case evidence rows (we mark which ones player cited).
    """
    # Ground truth: cause of death is the entropy method (high-level, e.g. "poisoning")
    # combined with the method_detail for context. We score player's CoD against the entropy method.
    actual_cause = entropy_method

    # Run all four text-field scores concurrently would be nice but phi4-mini is single-threaded,
    # so we run them sequentially to avoid model contention.
    perp_correct = await _score_field("perpetrator", suspect_name, killer_name)
    cod_correct  = await _score_field("cause_of_death", cause_of_death, actual_cause)
    method_correct = await _score_field("method", method, killer_method_detail)
    motive_correct = await _score_field("motive", motive, killer_motive)

    # Score evidence
    cited_set = set(evidence_cited_ids)
    evidence_result = []
    key_evidence_count = 0
    correct_key_cited = 0

    for ev in evidence_items:
        is_key = await _is_key_evidence(ev["true_implication"], killer_name, killer_method_detail)
        player_cited = ev["id"] in cited_set
        player_was_right = is_key and player_cited
        if is_key:
            key_evidence_count += 1
            if player_cited:
                correct_key_cited += 1
        evidence_result.append({
            "id": ev["id"],
            "item": ev["item"],
            "true_implication": ev["true_implication"],
            "player_cited": player_cited,
            "is_key_evidence": is_key,
            "player_was_right": player_was_right,
        })

    # Score 0-100:
    # perpetrator: 40 pts (most important)
    # cause_of_death + method + motive: 10 pts each = 30 pts
    # evidence: 30 pts split over key evidence items
    score = 0
    if perp_correct:
        score += 40
    if cod_correct:
        score += 10
    if method_correct:
        score += 10
    if motive_correct:
        score += 10
    if key_evidence_count > 0:
        evidence_pts = round((correct_key_cited / key_evidence_count) * 30)
        score += evidence_pts
    else:
        score += 30  # no key evidence to find → full evidence points

    if score >= 70 and perp_correct:
        verdict = "CORRECT VERDICT"
    elif perp_correct:
        verdict = "PARTIAL"
    else:
        verdict = "WRONG"

    return {
        "perpetrator": {"yours": suspect_name, "actual": killer_name, "correct": perp_correct},
        "cause_of_death": {"yours": cause_of_death, "actual": actual_cause, "correct": cod_correct},
        "method": {"yours": method, "actual": killer_method_detail, "correct": method_correct},
        "motive": {"yours": motive, "actual": killer_motive, "correct": motive_correct},
        "evidence": evidence_result,
        "score": score,
        "verdict": verdict,
    }
