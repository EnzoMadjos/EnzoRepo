"""
Session Memory — cross-session context for ATLAS.

Stores and retrieves compressed summaries of past work sessions so ATLAS
can resume conversations with full context about what was built, discussed,
and decided in previous sessions — similar to claude-mem's approach but
running entirely on local infrastructure (SQLite + ChromaDB + Ollama).

Storage:
  - training_memory (JSON) — fast retrieval, no embeddings needed
  - rag_memory (ChromaDB)  — semantic search by topic

Categories:
  - "session-memory"  — full session summaries (what was worked on, decided)
  - "work-observation" — single-fact captures mid-session (tool use, code written)
"""

import hashlib
import time
from datetime import datetime, timezone
from typing import List, Optional


# ── Retrieval ────────────────────────────────────────────────────────────────

def get_recent_summaries(n: int = 4) -> List[dict]:
    """Return the last n session summaries as dicts with 'entry' and 'timestamp'."""
    try:
        from training_memory import list_training
        entries = list_training()
        session_entries = [
            e for e in entries
            if isinstance(e, dict) and e.get("category") == "session-memory"
        ]
        return session_entries[-n:]
    except Exception:
        return []


def get_context_block(n: int = 3) -> str:
    """
    Return a formatted block of past session context ready for system prompt injection.
    Returns empty string if no summaries exist.
    """
    entries = get_recent_summaries(n)
    if not entries:
        return ""

    lines = ["Previous work sessions (most recent first):"]
    for entry in reversed(entries):
        text = entry.get("entry", "").replace("[Session summary] ", "").strip()
        ts = entry.get("timestamp", "")
        try:
            # Format timestamp as human-readable date
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
        except Exception:
            date_str = ""

        header = f"[Session — {date_str}]" if date_str else "[Past session]"
        lines.append(f"\n{header}\n{text}")

    return "\n".join(lines)


def search_relevant(query: str, top_k: int = 3) -> List[str]:
    """
    Semantic search over session summaries for the given query.
    Returns matching summary texts (without the '[Session summary]' prefix).
    """
    try:
        from rag_memory import search_memory
        all_results = search_memory(query, top_k=top_k * 3)
        # Filter to only session-memory entries (they contain the prefix)
        session_hits = [r for r in all_results if "[Session summary]" in r][:top_k]
        return [r.replace("[Session summary] ", "").strip() for r in session_hits]
    except Exception:
        return []


def get_summary_count() -> int:
    """Return the total number of stored session summaries."""
    try:
        from training_memory import list_training
        entries = list_training()
        return sum(1 for e in entries if isinstance(e, dict) and e.get("category") == "session-memory")
    except Exception:
        return 0


# ── Work observations (mid-session, lightweight facts) ──────────────────────

_seen_work_hashes: set = set()


def _work_hash(text: str) -> str:
    return hashlib.md5(text.lower().strip().encode()).hexdigest()


def record_work_observation(observation: str) -> bool:
    """
    Record a single work fact mid-session (e.g. 'User edited chat.html to fix modal animation').
    Stored as category='work-observation' — lighter than a full session summary.
    Deduplicates by content hash.
    Returns True if saved, False if duplicate/skipped.
    """
    if not observation or len(observation) < 15:
        return False

    h = _work_hash(observation)
    if h in _seen_work_hashes:
        return False

    # Quick word-overlap dedup against recent entries
    try:
        from training_memory import list_training
        entries = list_training()
        recent_work = [
            e.get("entry", "") for e in entries[-50:]
            if isinstance(e, dict) and e.get("category") == "work-observation"
        ]
        obs_words = set(observation.lower().split())
        for existing in recent_work:
            existing_words = set(existing.lower().split())
            overlap = len(obs_words & existing_words) / max(len(obs_words), 1)
            if overlap > 0.70:
                _seen_work_hashes.add(h)
                return False
    except Exception:
        pass

    try:
        from training_memory import add_training
        add_training(observation, category="work-observation")
        _seen_work_hashes.add(h)
        try:
            from rag_memory import upsert_memory
            upsert_memory(observation, category="work-observation")
        except Exception:
            pass
        return True
    except Exception:
        return False


def get_recent_work_observations(n: int = 10) -> List[str]:
    """Return the last n work observations."""
    try:
        from training_memory import list_training
        entries = list_training()
        work_entries = [
            e.get("entry", "") for e in entries
            if isinstance(e, dict) and e.get("category") == "work-observation"
        ]
        return work_entries[-n:]
    except Exception:
        return []


# ── Summary management ───────────────────────────────────────────────────────

def delete_summary_by_index(index: int) -> bool:
    """Delete a session summary by its position in the list (0 = oldest)."""
    try:
        from training_memory import load_training, save_training
        entries = load_training()
        session_entries_idx = [
            i for i, e in enumerate(entries)
            if isinstance(e, dict) and e.get("category") == "session-memory"
        ]
        if index < 0 or index >= len(session_entries_idx):
            return False
        real_idx = session_entries_idx[index]
        entries.pop(real_idx)
        save_training(entries)
        return True
    except Exception:
        return False


def clear_all_summaries() -> int:
    """Remove all session summaries. Returns count removed."""
    try:
        from training_memory import load_training, save_training
        entries = load_training()
        kept = [e for e in entries if not (isinstance(e, dict) and e.get("category") == "session-memory")]
        removed = len(entries) - len(kept)
        save_training(kept)
        return removed
    except Exception:
        return 0
