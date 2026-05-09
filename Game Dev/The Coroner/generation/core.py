"""
Phase 2a — Core case generation via GitHub Models API.
Generates: victim, killer profile, causal timeline.
Small targeted output (~700 tokens) for high JSON compliance.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from generation.entropy import EntropySeed
from generation.schemas import CoreCaseSchema
from llm.github_client import get_github_client

logger = logging.getLogger(__name__)

_SYSTEM = """You are a forensic case file generator for a mystery game.
Generate a realistic, morally complex homicide case. The killer must appear innocent at first glance.
Always respond with valid JSON matching the exact schema provided. No markdown, no prose outside JSON."""


def _build_prompt(seed: EntropySeed) -> str:
    return f"""Generate a homicide case with these parameters:
- Motive type: {seed.motive_type.replace("_", " ")}
- Method: {seed.method.replace("_", " ")}
- Victim archetype: {seed.victim_archetype.replace("_", " ")}
- Setting: {seed.setting.replace("_", " ")}
- Killer surface suspicion: {seed.killer_surface_suspicion.replace("_", " ")} (killer must seem innocent)

Return ONLY this JSON structure (no markdown fences, no extra fields):
{{
  "case_title": "Death of [Victim Full Name]",
  "victim": {{
    "name": "Full Name",
    "age": <integer 18-90>,
    "occupation": "specific job title",
    "traits": ["trait1", "trait2", "trait3"],
    "secrets": ["secret1", "secret2"]
  }},
  "killer": {{
    "witness_name": "Full Name (must appear in witness list you'll generate next)",
    "motive": "specific motive narrative",
    "method_detail": "specific method and how it was executed",
    "opportunity_window": "exact time window when the killing occurred",
    "alibi_claim": "what the killer claims they were doing",
    "alibi_weakness": "the specific flaw in their alibi (must be discoverable by a witness)",
    "surface_behavior": "why the player would not suspect them initially",
    "deduction_chain": [
      "Step 1: clue/observation that points to X",
      "Step 2: implication of X leads to Y",
      "Step 3: Y combined with evidence Z confirms killer"
    ]
  }},
  "causal_timeline": [
    {{"time": "HH:MM", "event": "what happened", "known_by": ["Witness Name"]}}
  ]
}}

Make the case genuinely challenging. The killer's alibi_weakness must be something a witness actually knows about.
Include 5-7 timeline events covering: victim's last known activity, killer's movements, discovery of body."""


async def generate_core_case(seed: EntropySeed) -> CoreCaseSchema:
    """
    Call GitHub Models API to generate the core case skeleton.
    Returns a validated CoreCaseSchema or raises ValidationError / httpx errors.
    """
    client = get_github_client()
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _build_prompt(seed)},
    ]

    logger.info("Generating core case (Phase 2a)...")
    raw = await client.chat_json(messages, temperature=0.85, max_tokens=2048)

    # Validate output through Pydantic — ValidationError triggers retry in pipeline
    try:
        schema = CoreCaseSchema.model_validate(raw)
    except ValidationError as e:
        logger.warning(f"Core case validation failed: {e}")
        raise

    logger.info(f"Core case generated: '{schema.case_title}', killer={schema.killer.witness_name}")
    return schema
