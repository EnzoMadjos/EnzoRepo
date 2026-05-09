"""
Phase 2b — Witnesses, Evidence, Red Herrings generation via GitHub Models API.
Sequential calls (Ollama is sequential internally; same principle here for reliability).
Each component is validated via Pydantic independently — bad component = retry that component only.
"""
from __future__ import annotations

import logging

from pydantic import ValidationError

from generation.entropy import EntropySeed
from generation.schemas import ComponentsSchema, CoreCaseSchema
from llm.github_client import get_github_client

logger = logging.getLogger(__name__)

_SYSTEM = """You are a forensic case file generator for a mystery game.
Generate realistic characters, evidence, and red herrings.
Always respond with valid JSON matching the exact schema. No markdown, no prose outside JSON."""


def _build_prompt(seed: EntropySeed, core: CoreCaseSchema) -> str:
    killer_name = core.killer.witness_name
    timeline_summary = "\n".join(
        f"  {e.time}: {e.event} (known by: {', '.join(e.known_by)})"
        for e in core.causal_timeline
    )

    return f"""Given this case core:
Victim: {core.victim.name}, {core.victim.age}, {core.victim.occupation}
Setting: {seed.setting.replace("_", " ")}
Killer (DO NOT reveal to player — just use this name in witnesses): {killer_name}
Killer's alibi weakness: {core.killer.alibi_weakness}
Killer's opportunity window: {core.killer.opportunity_window}

Timeline:
{timeline_summary}

Generate EXACTLY {seed.num_witnesses} witnesses, {seed.num_red_herrings} red herrings, and 4-6 evidence items.

CRITICAL RULES:
1. The killer ({killer_name}) MUST be one of the witnesses.
2. Each red herring's assigned_witness_name must be a witness who knows the innocent_explanation.
3. At least one witness must know the killer's alibi_weakness.
4. Witnesses must NOT know they are suspects — they are just people connected to the victim.
5. The killer's witness entry should show no obvious guilt in their true_knowledge.

Return ONLY this JSON (no markdown):
{{
  "witnesses": [
    {{
      "name": "Full Name",
      "occupation": "specific job",
      "relationship_to_victim": "how they knew the victim",
      "true_knowledge": ["fact they'll reveal when asked relevant questions"],
      "concealed_knowledge": ["fact they hide and why"],
      "their_lie": "one specific false statement they will make",
      "speech_pattern": "brief description of how they speak (e.g. 'formal, measured, looks away when nervous')"
    }}
  ],
  "evidence": [
    {{
      "item": "specific item name",
      "location": "where it was found",
      "examine_text": "what the coroner observes when examining it (clinical, 2-3 sentences)",
      "true_implication": "what this actually proves",
      "misleading_reading": "what it appears to mean at first glance"
    }}
  ],
  "red_herrings": [
    {{
      "suspect_name": "name of witness who seems suspicious",
      "suspicious_behavior": "what makes them look guilty",
      "innocent_explanation": "the true innocent reason for their behavior",
      "resolution_clue": "what evidence or statement breaks this herring",
      "assigned_witness_name": "name of witness who knows the innocent_explanation"
    }}
  ]
}}"""


async def generate_components(seed: EntropySeed, core: CoreCaseSchema) -> ComponentsSchema:
    """
    Generate witnesses, evidence, and red herrings from the core case.
    Returns validated ComponentsSchema or raises ValidationError.
    """
    client = get_github_client()
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _build_prompt(seed, core)},
    ]

    logger.info(f"Generating components (Phase 2b): {seed.num_witnesses} witnesses, {seed.num_red_herrings} red herrings...")
    raw = await client.chat_json(messages, temperature=0.85, max_tokens=4096)

    try:
        schema = ComponentsSchema.model_validate(raw)
    except ValidationError as e:
        logger.warning(f"Components validation failed: {e}")
        raise

    # Verify killer is one of the witnesses
    witness_names = [w.name for w in schema.witnesses]
    if core.killer.witness_name not in witness_names:
        raise ValueError(
            f"Killer '{core.killer.witness_name}' not found in witnesses: {witness_names}"
        )

    logger.info(f"Components generated: {len(schema.witnesses)} witnesses, {len(schema.evidence)} evidence, {len(schema.red_herrings)} red herrings")
    return schema
