"""
SQLAlchemy models for The Coroner: Inquest
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ── Anti-repeat log ────────────────────────────────────────────────────────

class GenerationSession(Base):
    """Tracks entropy selections of past sessions to avoid repetition."""
    __tablename__ = "generation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    motive_type: Mapped[str] = mapped_column(String(64))
    method: Mapped[str] = mapped_column(String(64))
    victim_archetype: Mapped[str] = mapped_column(String(64))
    setting: Mapped[str] = mapped_column(String(64))


# ── Case generation job ────────────────────────────────────────────────────

class CaseGenerationJob(Base):
    __tablename__ = "case_generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # null until case row is created
    case_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("cases.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending | generating_core | generating_witnesses | generating_evidence
    # generating_herrings | validating | voice_pass | done | failed
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    case: Mapped[Optional["Case"]] = relationship("Case", foreign_keys=[case_id], uselist=False)


# ── Core case models ───────────────────────────────────────────────────────

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_token: Mapped[str] = mapped_column(String(64), index=True)
    generation_job_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("case_generation_jobs.id"), nullable=True
    )
    # Entropy selections for replay/debug
    entropy_seed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    # Raw validated world skeleton from GitHub Models API
    world_skeleton: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    generation_job: Mapped[Optional["CaseGenerationJob"]] = relationship(
        "CaseGenerationJob", foreign_keys=[generation_job_id], viewonly=True, uselist=False
    )
    victim: Mapped[Optional["Victim"]] = relationship("Victim", back_populates="case", uselist=False)
    killer: Mapped[Optional["Killer"]] = relationship("Killer", back_populates="case", uselist=False)
    witnesses: Mapped[list["Witness"]] = relationship("Witness", back_populates="case")
    evidence_items: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="case")
    red_herrings: Mapped[list["RedHerring"]] = relationship("RedHerring", back_populates="case")
    board_state: Mapped[Optional["BoardState"]] = relationship("BoardState", back_populates="case", uselist=False)
    report: Mapped[Optional["Report"]] = relationship("Report", back_populates="case", uselist=False)

    def get_entropy(self) -> dict:
        return json.loads(self.entropy_seed) if self.entropy_seed else {}


class Victim(Base):
    __tablename__ = "victims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    name: Mapped[str] = mapped_column(String(128))
    age: Mapped[int] = mapped_column(Integer)
    occupation: Mapped[str] = mapped_column(String(128))
    traits: Mapped[str] = mapped_column(Text)          # JSON list[str]
    secrets: Mapped[str] = mapped_column(Text)         # JSON list[str]
    # SVG portrait seed — deterministic face generation client-side
    portrait_seed: Mapped[str] = mapped_column(String(64))

    case: Mapped["Case"] = relationship("Case", back_populates="victim")

    def get_traits(self) -> list[str]:
        return json.loads(self.traits)

    def get_secrets(self) -> list[str]:
        return json.loads(self.secrets)


class Killer(Base):
    """Stored separately from witnesses — player should not know who this is."""
    __tablename__ = "killers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    # References the Witness row (killer IS one of the witnesses)
    witness_id: Mapped[int] = mapped_column(Integer, ForeignKey("witnesses.id"))
    motive: Mapped[str] = mapped_column(Text)
    method_detail: Mapped[str] = mapped_column(Text)
    opportunity_window: Mapped[str] = mapped_column(Text)
    alibi_claim: Mapped[str] = mapped_column(Text)
    alibi_weakness: Mapped[str] = mapped_column(Text)
    deduction_chain: Mapped[str] = mapped_column(Text)  # JSON list[str]

    case: Mapped["Case"] = relationship("Case", back_populates="killer")
    witness: Mapped["Witness"] = relationship("Witness", foreign_keys=[witness_id])

    def get_deduction_chain(self) -> list[str]:
        return json.loads(self.deduction_chain)


class Witness(Base):
    __tablename__ = "witnesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    name: Mapped[str] = mapped_column(String(128))
    occupation: Mapped[str] = mapped_column(String(128))
    relationship_to_victim: Mapped[str] = mapped_column(Text)
    true_knowledge: Mapped[str] = mapped_column(Text)      # JSON list[str]
    concealed_knowledge: Mapped[str] = mapped_column(Text) # JSON list[str]
    their_lie: Mapped[str] = mapped_column(Text)
    speech_pattern: Mapped[str] = mapped_column(Text)
    # Generated by phi4-mini voice pass, cached here
    voice_system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    portrait_seed: Mapped[str] = mapped_column(String(64))
    # Structural red-herring assignment (null if this witness isn't a herring-breaker)
    breaks_red_herring_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("red_herrings.id"), nullable=True
    )

    case: Mapped["Case"] = relationship("Case", back_populates="witnesses")
    interviews: Mapped[list["InterviewMessage"]] = relationship("InterviewMessage", back_populates="witness")
    breaks_herring: Mapped[Optional["RedHerring"]] = relationship(
        "RedHerring", foreign_keys=[breaks_red_herring_id]
    )

    def get_true_knowledge(self) -> list[str]:
        return json.loads(self.true_knowledge)

    def get_concealed_knowledge(self) -> list[str]:
        return json.loads(self.concealed_knowledge)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    item: Mapped[str] = mapped_column(String(256))
    location: Mapped[str] = mapped_column(String(256))
    examine_text: Mapped[str] = mapped_column(Text)        # shown to player on examine
    true_implication: Mapped[str] = mapped_column(Text)    # hidden ground truth
    misleading_reading: Mapped[str] = mapped_column(Text)  # initial appearance
    is_examined: Mapped[bool] = mapped_column(Boolean, default=False)
    player_annotation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case: Mapped["Case"] = relationship("Case", back_populates="evidence_items")


class RedHerring(Base):
    __tablename__ = "red_herrings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    suspect_name: Mapped[str] = mapped_column(String(128))
    suspicious_behavior: Mapped[str] = mapped_column(Text)
    innocent_explanation: Mapped[str] = mapped_column(Text)
    resolution_clue: Mapped[str] = mapped_column(Text)
    # FK to the witness who can break this herring (structural enforcement)
    assigned_witness_id: Mapped[int] = mapped_column(Integer, ForeignKey("witnesses.id"))

    case: Mapped["Case"] = relationship("Case", back_populates="red_herrings")
    assigned_witness: Mapped["Witness"] = relationship(
        "Witness", foreign_keys=[assigned_witness_id]
    )


# ── Gameplay state ─────────────────────────────────────────────────────────

class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    witness_id: Mapped[int] = mapped_column(Integer, ForeignKey("witnesses.id"))
    role: Mapped[str] = mapped_column(String(16))   # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    witness: Mapped["Witness"] = relationship("Witness", back_populates="interviews")


class BoardState(Base):
    __tablename__ = "board_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), unique=True)
    state_json: Mapped[str] = mapped_column(Text, default="{}")  # full JS board state
    server_version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    case: Mapped["Case"] = relationship("Case", back_populates="board_state")


class ConsultLog(Base):
    __tablename__ = "consult_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"))
    specialist: Mapped[str] = mapped_column(String(64))   # "pathologist" | "toxicologist"
    question: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), unique=True)
    session_token: Mapped[str] = mapped_column(String(64))
    # Player's answers
    suspect_name: Mapped[str] = mapped_column(String(128))
    cause_of_death: Mapped[str] = mapped_column(String(256))
    method: Mapped[str] = mapped_column(String(256))
    motive: Mapped[str] = mapped_column(String(256))
    evidence_cited: Mapped[str] = mapped_column(Text)   # JSON list[int] evidence IDs
    # Result (populated after scoring)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    filed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    case: Mapped["Case"] = relationship("Case", back_populates="report")

    def get_evidence_cited(self) -> list[int]:
        return json.loads(self.evidence_cited) if self.evidence_cited else []

    def get_result(self) -> dict:
        return json.loads(self.result_json) if self.result_json else {}
