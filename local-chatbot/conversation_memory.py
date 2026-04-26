"""
Session-scoped conversation history for ATLAS.
Keeps a rolling window of messages per session ID so ATLAS remembers
what was said earlier in the conversation — just like Copilot does.
Sessions are persisted to disk so ATLAS remembers across restarts.
"""

import uuid
import time
import json
from collections import deque
from pathlib import Path
from typing import List, Dict

# Max messages to keep per session (older ones roll off)
MAX_HISTORY = 40
# Sessions inactive for this many seconds are pruned (2 hours)
SESSION_TTL = 7200
# How many messages to save to disk per session
PERSIST_LIMIT = 20

# Persist file — lives next to secure/ folder
def _session_file() -> Path:
    candidates = [
        Path(__file__).parent / "secure" / "atlas_sessions.json",
        Path("/mnt/c/ATLAS V1/secure/atlas_sessions.json"),
    ]
    for p in candidates:
        if p.parent.exists():
            return p
    return candidates[0]

# { session_id: {"messages": deque, "last_active": timestamp} }
_sessions: Dict[str, dict] = {}


def _save_sessions() -> None:
    """Persist active sessions to disk."""
    try:
        data = {}
        for sid, s in _sessions.items():
            msgs = list(s["messages"])[-PERSIST_LIMIT:]
            data[sid] = {"messages": msgs, "last_active": s["last_active"]}
        _session_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_sessions() -> None:
    """Load persisted sessions on startup."""
    try:
        f = _session_file()
        if not f.exists():
            return
        data = json.loads(f.read_text(encoding="utf-8"))
        cutoff = time.time() - SESSION_TTL
        for sid, s in data.items():
            if s.get("last_active", 0) < cutoff:
                continue  # discard stale
            _sessions[sid] = {
                "messages": deque(s.get("messages", []), maxlen=MAX_HISTORY),
                "last_active": s["last_active"],
            }
    except Exception:
        pass


# Load on import
_load_sessions()


def new_session() -> str:
    """Create a new session and return its ID."""
    sid = str(uuid.uuid4())
    _sessions[sid] = {
        "messages": deque(maxlen=MAX_HISTORY),
        "last_active": time.time(),
    }
    return sid


def session_exists(session_id: str) -> bool:
    return session_id in _sessions


def get_history(session_id: str) -> List[dict]:
    """Return the message list for a session, creating one if needed."""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": deque(maxlen=MAX_HISTORY),
            "last_active": time.time(),
        }
    _sessions[session_id]["last_active"] = time.time()
    return list(_sessions[session_id]["messages"])


def append_message(session_id: str, role: str, content: str) -> None:
    """Add a message to the session history."""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "messages": deque(maxlen=MAX_HISTORY),
            "last_active": time.time(),
        }
    _sessions[session_id]["messages"].append({"role": role, "content": content})
    _sessions[session_id]["last_active"] = time.time()
    _save_sessions()


def clear_session(session_id: str) -> None:
    """Wipe history for a session (user clicked New Chat)."""
    if session_id in _sessions:
        _sessions[session_id]["messages"].clear()
        _sessions[session_id]["last_active"] = time.time()
    _save_sessions()


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    _save_sessions()


def prune_old_sessions() -> int:
    """Remove sessions older than SESSION_TTL. Returns count removed."""
    cutoff = time.time() - SESSION_TTL
    stale = [sid for sid, s in _sessions.items() if s["last_active"] < cutoff]
    for sid in stale:
        del _sessions[sid]
    if stale:
        _save_sessions()
    return len(stale)


def session_count() -> int:
    return len(_sessions)


def list_all_sessions() -> list:
    """Return all active session IDs."""
    return list(_sessions.keys())
