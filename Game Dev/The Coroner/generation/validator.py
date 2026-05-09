"""
Phase 3 — Python consistency validation (zero LLM).
Checks the generated case is actually solvable before committing to DB.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from generation.schemas import ComponentsSchema, CoreCaseSchema

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str]


def validate_case(core: CoreCaseSchema, components: ComponentsSchema) -> ValidationResult:
    """
    Structural consistency checks. All checks are O(1) or O(n) — no LLM needed.
    Returns ValidationResult with all errors found (not fail-fast).
    """
    errors: list[str] = []
    witness_names = {w.name for w in components.witnesses}

    # ── Check 1: Killer is a witness ──────────────────────────────────────
    if core.killer.witness_name not in witness_names:
        errors.append(
            f"Killer '{core.killer.witness_name}' is not in the witness list. "
            f"Witnesses: {sorted(witness_names)}"
        )

    # ── Check 2: Killer's alibi weakness is in at least one witness's true_knowledge ──
    alibi_weakness = core.killer.alibi_weakness.lower()
    alibi_breakable = any(
        any(alibi_weakness[:30] in fact.lower() for fact in w.true_knowledge)
        for w in components.witnesses
        if w.name != core.killer.witness_name
    )
    if not alibi_breakable:
        # Softer check: at least one non-killer witness has knowledge relevant to opportunity window
        opportunity = core.killer.opportunity_window.lower()
        alibi_breakable = any(
            any(
                any(word in fact.lower() for word in opportunity.split()[:3])
                for fact in w.true_knowledge
            )
            for w in components.witnesses
            if w.name != core.killer.witness_name
        )
    if not alibi_breakable:
        errors.append(
            f"Killer's alibi weakness ('{core.killer.alibi_weakness[:60]}...') "
            f"is not covered by any witness's true_knowledge. Case may be unsolvable."
        )

    # ── Check 3: Every red herring has a valid assigned_witness ──────────
    for rh in components.red_herrings:
        if rh.assigned_witness_name not in witness_names:
            errors.append(
                f"Red herring '{rh.suspect_name}' assigned to unknown witness "
                f"'{rh.assigned_witness_name}'. Known: {sorted(witness_names)}"
            )

    # ── Check 4: Deduction chain is supported by evidence ────────────────
    chain_len = len(core.killer.deduction_chain)
    evidence_count = len(components.evidence)
    if chain_len > evidence_count + 2:
        errors.append(
            f"Deduction chain has {chain_len} steps but only {evidence_count} "
            f"evidence items exist. Chain likely unsupportable."
        )

    # ── Check 5: Minimum evidence for a solvable case ────────────────────
    if evidence_count < 3:
        errors.append(
            f"Only {evidence_count} evidence items generated — minimum 3 required."
        )

    # ── Check 6: World skeleton size guard ───────────────────────────────
    import json
    skeleton_size = len(json.dumps(
        {"core": core.model_dump(), "components": components.model_dump()}
    ).encode())
    from config import MAX_WORLD_SKELETON_BYTES
    if skeleton_size > MAX_WORLD_SKELETON_BYTES:
        errors.append(
            f"World skeleton is {skeleton_size} bytes — exceeds {MAX_WORLD_SKELETON_BYTES} limit."
        )

    passed = len(errors) == 0
    if passed:
        logger.info("Case validation passed.")
    else:
        logger.warning(f"Case validation failed ({len(errors)} errors): {errors}")

    return ValidationResult(passed=passed, errors=errors)
