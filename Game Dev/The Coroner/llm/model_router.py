"""
Model rotation with automatic daily-limit fallback.

Interactive chain (witness interviews, consults, scoring, voice pass):
  gpt-4.1-mini → gpt-4o-mini → gpt-4.1 → gpt-4o → grok-3-mini → CLOSED

Generation chain (case creation):
  gpt-4.1 → gpt-4.1-mini → gpt-4o → gpt-4o-mini → grok-3-mini → CLOSED

When a model returns 429 it is marked exhausted for the rest of the UTC day.
When ALL models in a chain are exhausted, DailyLimitExhausted is raised.
The server then shows a "closed for today" message — no llama fallback.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DailyLimitExhausted(Exception):
    """All models in the rotation are exhausted for today (UTC midnight reset)."""
    pass


# ── Model chains ──────────────────────────────────────────────────────────────

# Best for fast roleplay responses; mini models first to save quota
INTERACTIVE_CHAIN: list[str] = [
    "gpt-4.1-mini",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4o",
    "grok-3-mini",   # last resort — 30/day, then closed
]

# Best quality first for case generation; gpt-4.1 > gpt-4o quality
GENERATION_CHAIN: list[str] = [
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4o-mini",
    "grok-3-mini",   # last resort — 30/day, then closed
]


# ── Router ────────────────────────────────────────────────────────────────────

class ModelRouter:
    def __init__(self) -> None:
        # model_name → "YYYY-MM-DD" (UTC) when daily quota was hit
        self._exhausted: dict[str, str] = {}

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def is_exhausted(self, model: str) -> bool:
        return self._exhausted.get(model) == self._today()

    def mark_exhausted(self, model: str) -> None:
        today = self._today()
        if self._exhausted.get(model) != today:
            logger.warning(f"[ModelRouter] {model!r} daily quota hit — rotating to next model.")
        self._exhausted[model] = today

    def next_model(self, chain: list[str]) -> str:
        """Return the first non-exhausted model in chain.
        Raises DailyLimitExhausted if all models are exhausted."""
        for model in chain:
            if not self.is_exhausted(model):
                return model
        raise DailyLimitExhausted(
            "The morgue is closed for today. All AI model quotas exhausted. "
            "Come back tomorrow (UTC midnight reset)."
        )

    def next_interactive(self) -> str:
        return self.next_model(INTERACTIVE_CHAIN)

    def next_generation(self) -> str:
        return self.next_model(GENERATION_CHAIN)

    def status(self) -> dict:
        """Return current exhaustion status for all chains."""
        today = self._today()
        return {
            "reset_at": "UTC midnight",
            "date_utc": today,
            "interactive": {
                m: ("exhausted" if self._exhausted.get(m) == today else "available")
                for m in INTERACTIVE_CHAIN
            },
            "generation": {
                m: ("exhausted" if self._exhausted.get(m) == today else "available")
                for m in GENERATION_CHAIN
            },
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
