"""
Phase 4 — Witness voice pass via gpt-4.1-mini (GitHub Models).
Generates a system prompt for each witness used in interview SSE calls.
"""
from __future__ import annotations

import logging

from generation.schemas import ComponentsSchema, CoreCaseSchema, VoicePromptSchema
from llm.github_client import get_github_client

logger = logging.getLogger(__name__)

_SYSTEM = """Character writer for forensic mystery game.
Write a roleplay system prompt for a witness being questioned by the coroner.
Character stays in-character, reveals true_knowledge only when directly asked,
conceals concealed_knowledge unless cornered, and delivers their_lie convincingly.
Respond with valid JSON only."""


def _build_voice_prompt(
    witness_name: str,
    occupation: str,
    relationship: str,
    true_knowledge: list[str],
    concealed_knowledge: list[str],
    their_lie: str,
    speech_pattern: str,
    is_killer: bool,
    victim_name: str,
) -> list[dict]:
    knowledge_str = "\n".join(f"  - {k}" for k in true_knowledge)
    concealed_str = "\n".join(f"  - {k}" for k in concealed_knowledge)

    return [
        {"role": "system", "content": _SYSTEM},
        {
            "role": "user",
            "content": f"""Witness profile:
Name: {witness_name}
Occupation: {occupation}
Relationship to victim ({victim_name}): {relationship}
Speech pattern: {speech_pattern}

What they WILL reveal if asked the right questions:
{knowledge_str}

What they CONCEAL (reveal only under extreme pressure or contradicting evidence):
{concealed_str}

Their specific lie they will tell: "{their_lie}"
{"Note: This witness is the actual killer. They must seem cooperative but subtly deflect any questions that get too close to their opportunity window. Never confess." if is_killer else ""}

Generate a system prompt (2-4 paragraphs) that instructs an LLM to roleplay as this character during a coroner's inquiry.
Include: personality, speech style, emotional state, what topics make them nervous, what they're proud of.
The system prompt should make the character feel distinct and human.

Return JSON:
{{
  "speech_style": "one sentence describing how they speak",
  "anxiety_topic": "what topic makes them visibly nervous",
  "pride_topic": "what they're proud of or boast about",
  "system_prompt": "full multi-paragraph system prompt for roleplay"
}}""",
        },
    ]


async def generate_voice_prompts(
    core: CoreCaseSchema, components: ComponentsSchema
) -> dict[str, str]:
    """
    Generate voice system prompts for all witnesses via gpt-4.1-mini.
    Returns dict: witness_name -> system_prompt string.
    """
    client = get_github_client()
    victim_name = core.victim.name
    killer_name = core.killer.witness_name
    results: dict[str, str] = {}

    for i, witness in enumerate(components.witnesses):
        is_killer = witness.name == killer_name
        logger.info(f"Voice pass {i+1}/{len(components.witnesses)}: {witness.name}")

        messages = _build_voice_prompt(
            witness_name=witness.name,
            occupation=witness.occupation,
            relationship=witness.relationship_to_victim,
            true_knowledge=witness.true_knowledge,
            concealed_knowledge=witness.concealed_knowledge,
            their_lie=witness.their_lie,
            speech_pattern=witness.speech_pattern,
            is_killer=is_killer,
            victim_name=victim_name,
        )

        try:
            raw = await client.chat_json_interactive(messages, temperature=0.75, max_tokens=500)
            voice = VoicePromptSchema.model_validate(raw)
            results[witness.name] = voice.system_prompt
            logger.info(f"  Voice ready for {witness.name}: {voice.speech_style[:60]}")
        except Exception as e:
            # Non-fatal — fall back to a generic system prompt
            logger.warning(f"Voice pass failed for {witness.name}: {e}. Using fallback.")
            results[witness.name] = (
                f"You are {witness.name}, {witness.occupation}. "
                f"You knew the victim as {witness.relationship_to_victim}. "
                f"Speak in this style: {witness.speech_pattern}. "
                f"Answer questions honestly but protect your privacy. "
                f"You will lie about this: {witness.their_lie}"
            )

    return results
