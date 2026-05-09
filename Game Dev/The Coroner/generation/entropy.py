"""
Entropy injection engine — Phase 1 of case generation.
Python chooses WHAT kind of mystery is generated. The LLM executes.
Anti-repeat: blocks same motive_type from appearing in last N sessions.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session

from config import ANTI_REPEAT_WINDOW

# ── Pools ──────────────────────────────────────────────────────────────────

MOTIVE_TYPES = [
    "financial_gain",
    "jealousy",
    "revenge",
    "cover_up_crime",
    "ideological",
    "accident_concealment",
    "protection_of_another",
    "mistaken_identity",
    "obsession",
    "inheritance",
]

METHODS = [
    "poisoning",
    "blunt_force",
    "staged_accident",
    "overdose",
    "drowning",
    "strangulation",
    "staged_natural_death",
    "sharp_force",
    "suffocation",
]

VICTIM_ARCHETYPES = [
    "public_figure",
    "recluse",
    "business_rival",
    "family_member",
    "stranger_with_secrets",
    "institution_head",
    "whistleblower",
    "old_friend",
]

SETTINGS = [
    "residential_home",
    "workplace_office",
    "hotel_room",
    "rural_property",
    "vehicle",
    "public_venue",
    "medical_facility",
    "waterfront",
]

KILLER_SURFACE_SUSPICION = ["low", "very_low"]


@dataclass
class EntropySeed:
    motive_type: str
    method: str
    victim_archetype: str
    setting: str
    num_witnesses: int
    num_red_herrings: int
    killer_surface_suspicion: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, s: str) -> "EntropySeed":
        return cls(**json.loads(s))


def _recent_motives(db: Session, window: int) -> list[str]:
    """Return motive_types used in the last `window` sessions."""
    from models import GenerationSession
    rows = (
        db.query(GenerationSession.motive_type)
        .order_by(GenerationSession.id.desc())
        .limit(window)
        .all()
    )
    return [r[0] for r in rows]


def sample_entropy(db: Session) -> EntropySeed:
    """
    Sample a fresh entropy seed, avoiding motive repetition from recent sessions.
    """
    recent = _recent_motives(db, ANTI_REPEAT_WINDOW)

    # Build available motive pool — exclude recently used
    available_motives = [m for m in MOTIVE_TYPES if m not in recent]
    if not available_motives:
        # Fallback: all motives (e.g. first session or pool exhausted)
        available_motives = MOTIVE_TYPES

    return EntropySeed(
        motive_type=random.choice(available_motives),
        method=random.choice(METHODS),
        victim_archetype=random.choice(VICTIM_ARCHETYPES),
        setting=random.choice(SETTINGS),
        num_witnesses=random.randint(4, 6),
        num_red_herrings=random.randint(2, 3),
        killer_surface_suspicion=random.choice(KILLER_SURFACE_SUSPICION),
    )


def record_session(db: Session, seed: EntropySeed) -> None:
    """Log the entropy selections after a successful case generation."""
    from models import GenerationSession
    row = GenerationSession(
        motive_type=seed.motive_type,
        method=seed.method,
        victim_archetype=seed.victim_archetype,
        setting=seed.setting,
    )
    db.add(row)
    db.commit()
