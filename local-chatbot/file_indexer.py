"""
file_indexer.py — Index local workspace files into ATLAS's RAG vector store.

Chunks files by logical sections (functions, classes, headings) or fixed windows,
embeds them via Ollama nomic-embed-text, and stores in ChromaDB.
Tracks file mtimes to skip unchanged files on re-index.
"""

import hashlib as _hash
import json as _json
import os as _os
import re as _re
import time as _time
from pathlib import Path
from typing import Generator

from file_access import (
    _WORKSPACE_ROOT, _SKIP_DIRS, _READABLE_EXTS,
    MAX_READ_BYTES,
)

_STATE_FILE = Path(__file__).parent / "models" / "file_index_state.json"
_CHUNK_SIZE = 60       # lines per chunk
_CHUNK_OVERLAP = 8     # overlap lines between chunks
_MIN_CHUNK_CHARS = 80  # skip tiny chunks


# ── State tracking ───────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        return _json.loads(_STATE_FILE.read_text()) if _STATE_FILE.exists() else {}
    except Exception:
        return {}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(_json.dumps(state, indent=2))


def _file_sig(path: Path) -> str:
    st = path.stat()
    return f"{st.st_mtime:.0f}:{st.st_size}"


# ── Chunking ─────────────────────────────────────────────────────────────────

def _chunk_text(text: str, filepath: str) -> list[str]:
    """Split text into overlapping line-window chunks."""
    lines = text.splitlines()
    chunks = []
    step = _CHUNK_SIZE - _CHUNK_OVERLAP
    for i in range(0, max(1, len(lines) - _CHUNK_OVERLAP), step):
        window = lines[i: i + _CHUNK_SIZE]
        chunk = "\n".join(window).strip()
        if len(chunk) >= _MIN_CHUNK_CHARS:
            header = f"[FILE: {filepath} | lines {i+1}-{i+len(window)}]\n"
            chunks.append(header + chunk)
    return chunks or [f"[FILE: {filepath}]\n{text.strip()}"]


# ── Core indexing ─────────────────────────────────────────────────────────────

def index_file(rel_path: str, force: bool = False) -> dict:
    """Index a single file into the RAG store. Returns status dict."""
    from rag_memory import upsert_memory
    from file_access import read_file

    result = read_file(rel_path)
    if "error" in result:
        return {"path": rel_path, "status": "error", "reason": result["error"]}

    fpath = (_WORKSPACE_ROOT / rel_path).resolve()
    state = _load_state()
    sig = _file_sig(fpath)

    if not force and state.get(rel_path) == sig:
        return {"path": rel_path, "status": "skipped", "reason": "unchanged"}

    content = result["content"]
    chunks = _chunk_text(content, rel_path)

    ok = 0
    for chunk in chunks:
        if upsert_memory(chunk, category="file"):
            ok += 1

    state[rel_path] = sig
    _save_state(state)

    return {
        "path": rel_path,
        "status": "indexed",
        "chunks": len(chunks),
        "embedded": ok,
    }


def index_workspace(
    rel_path: str = "",
    force: bool = False,
    extensions: set[str] | None = None,
) -> dict:
    """
    Walk the workspace and index all readable files.
    rel_path: sub-path to limit scope (default: entire workspace)
    force: re-index even unchanged files
    extensions: limit to specific extensions e.g. {'.py', '.md'}
    """
    exts = extensions or _READABLE_EXTS
    base = (_WORKSPACE_ROOT / rel_path).resolve() if rel_path else _WORKSPACE_ROOT

    if not base.exists():
        return {"error": f"Path not found: {rel_path}"}

    results = {"indexed": 0, "skipped": 0, "errors": 0, "files": []}

    for fpath in sorted(base.rglob("*")):
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in exts:
            continue
        if any(part in _SKIP_DIRS for part in fpath.parts):
            continue
        if fpath.stat().st_size > MAX_READ_BYTES * 2:
            continue  # skip very large files

        try:
            rel = str(fpath.relative_to(_WORKSPACE_ROOT))
            r = index_file(rel, force=force)
            status = r.get("status", "error")
            results["files"].append(r)
            if status == "indexed":
                results["indexed"] += 1
            elif status == "skipped":
                results["skipped"] += 1
            else:
                results["errors"] += 1
        except Exception as e:
            results["errors"] += 1
            results["files"].append({"path": str(fpath), "status": "error", "reason": str(e)})

    return results


def clear_file_index() -> int:
    """Remove all file-category entries from vector store and clear state."""
    try:
        from rag_memory import _get_collection
        col = _get_collection()
        if col:
            # Delete all docs with category=file
            existing = col.get(where={"category": "file"})
            ids = existing.get("ids", [])
            if ids:
                col.delete(ids=ids)
            count = len(ids)
        else:
            count = 0
    except Exception:
        count = 0

    _save_state({})
    return count


def indexed_file_count() -> int:
    """How many files are currently tracked in the index state."""
    return len(_load_state())
