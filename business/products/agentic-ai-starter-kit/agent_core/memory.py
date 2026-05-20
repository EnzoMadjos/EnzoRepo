"""
Simple in-memory + file-backed memory for agents.
Stores task/result pairs per agent, persists to memory.json.
"""

from __future__ import annotations
import json
import os
from datetime import datetime

MEMORY_FILE = "memory.json"


class Memory:
    def __init__(self, filepath: str = MEMORY_FILE):
        self.filepath = filepath
        self._store: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                self._store = json.load(f)

    def _save(self):
        with open(self.filepath, "w") as f:
            json.dump(self._store, f, indent=2)

    def add(self, agent: str, task: str, result: str):
        entry = {
            "agent": agent,
            "task": task,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._store.append(entry)
        self._save()

    def get_context(self, agent: str = None, last_n: int = 5) -> str:
        """Return the last N memory entries as a formatted string."""
        entries = self._store
        if agent:
            entries = [e for e in entries if e["agent"] == agent]
        recent = entries[-last_n:]
        if not recent:
            return ""
        lines = []
        for e in recent:
            lines.append(f"[{e['agent']} @ {e['timestamp']}]\nTask: {e['task']}\nResult: {e['result'][:500]}")
        return "\n\n".join(lines)

    def clear(self):
        self._store = []
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
