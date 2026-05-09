"""
Pydantic schemas for LLM output validation.
Every LLM response is parsed through these before touching the DB.
ValidationError = retry trigger.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VictimSchema(BaseModel):
    name: str
    age: int = Field(ge=18, le=90)
    occupation: str
    traits: list[str] = Field(min_length=2, max_length=5)
    secrets: list[str] = Field(min_length=1, max_length=3)


class KillerSchema(BaseModel):
    witness_name: str   # must match one of the witness names
    motive: str
    method_detail: str
    opportunity_window: str
    alibi_claim: str
    alibi_weakness: str
    surface_behavior: str   # why player won't suspect them initially
    deduction_chain: list[str] = Field(min_length=3, max_length=8)


class TimelineEvent(BaseModel):
    time: str
    event: str
    known_by: list[str]   # witness names


class CoreCaseSchema(BaseModel):
    """Phase 2a output — victim, killer profile, causal timeline."""
    victim: VictimSchema
    killer: KillerSchema
    causal_timeline: list[TimelineEvent] = Field(min_length=4, max_length=10)
    case_title: str   # e.g. "Death of [name]" — shown on case file


class WitnessSchema(BaseModel):
    name: str
    occupation: str
    relationship_to_victim: str
    true_knowledge: list[str] = Field(default_factory=list)
    concealed_knowledge: list[str] = Field(default_factory=list)
    their_lie: str = ""
    speech_pattern: str = ""

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Witness name cannot be empty")
        return v.strip()


class EvidenceSchema(BaseModel):
    item: str
    location: str
    examine_text: str       # what player reads when they inspect it
    true_implication: str   # hidden ground truth
    misleading_reading: str # what it looks like at first glance


class RedHerringSchema(BaseModel):
    suspect_name: str       # name of witness who appears suspicious
    suspicious_behavior: str
    innocent_explanation: str
    resolution_clue: str
    assigned_witness_name: str  # which witness can break this herring


class ComponentsSchema(BaseModel):
    """Phase 2b output — witnesses, evidence, red herrings."""
    witnesses: list[WitnessSchema] = Field(min_length=3, max_length=6)
    evidence: list[EvidenceSchema] = Field(min_length=3, max_length=8)
    red_herrings: list[RedHerringSchema] = Field(default_factory=list)

    @field_validator("witnesses")
    @classmethod
    def killer_must_be_a_witness(cls, witnesses: list[WitnessSchema]) -> list[WitnessSchema]:
        # Validated against CoreCaseSchema.killer.witness_name in pipeline
        return witnesses


class VoicePromptSchema(BaseModel):
    """Phase 4 voice pass output per witness."""
    speech_style: str       # e.g. "clipped, formal, avoids eye contact"
    anxiety_topic: str      # what they're nervous about
    pride_topic: str        # what they boast about
    system_prompt: str      # full system prompt for interview SSE calls
