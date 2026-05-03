"""
Brain Vault Indexer — Atlas integration for the Obsidian brain/ vault.

Scans the vault's .md files, chunks them by section, embeds with nomic-embed-text
via Ollama (same model used by rag_memory), and stores in a dedicated ChromaDB
collection "brain_vault". Syncs incrementally using file mtimes.

Usage:
    from brain_index import vault, search_vault, list_vault_notes
    vault.sync()                   # call at startup (non-blocking, runs in thread)
    results = search_vault("project architecture")
    notes   = list_vault_notes()
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DEFAULT_VAULT = Path(__file__).parent.parent / "brain"
VAULT_PATH = Path(os.getenv("BRAIN_VAULT_PATH", str(_DEFAULT_VAULT))).resolve()

_COLLECTION_NAME = "brain_vault"
_EMBED_MODEL = "nomic-embed-text"
_SYNC_INTERVAL = 300  # seconds between auto-syncs
_TOP_K = 5
_MAX_CHUNK_CHARS = 1800  # soft cap per chunk

# Dirs to skip inside the vault
_SKIP_DIRS = {".obsidian", ".index", ".trash", "__pycache__"}


# ---------------------------------------------------------------------------
# Frontmatter + chunking helpers
# ---------------------------------------------------------------------------

_FM_BLOCK = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_TAGS = re.compile(r"^tags\s*:\s*\[?([^\]\n]+)\]?", re.MULTILINE | re.IGNORECASE)
_FM_TITLE = re.compile(r"^title\s*:\s*(.+)", re.MULTILINE | re.IGNORECASE)
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_H2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _parse_frontmatter(content: str) -> tuple[str, list[str], str]:
    """Return (title, tags, body_without_frontmatter)."""
    title = ""
    tags: list[str] = []
    body = content
    m = _FM_BLOCK.match(content)
    if m:
        fm = m.group(1)
        body = content[m.end():]
        tm = _FM_TITLE.search(fm)
        if tm:
            title = tm.group(1).strip().strip("'\"")
        tgm = _FM_TAGS.search(fm)
        if tgm:
            tags = [t.strip().strip("'\"") for t in tgm.group(1).split(",") if t.strip()]
    return title, tags, body


def _extract_wikilinks(text: str) -> list[str]:
    return _WIKILINK.findall(text)


def _derive_title(file_path: Path, frontmatter_title: str) -> str:
    if frontmatter_title:
        return frontmatter_title
    # Try first # heading
    return file_path.stem.replace("-", " ").replace("_", " ")


def _chunk_note(title: str, tags: list[str], body: str) -> list[dict[str, str]]:
    """
    Split a note into section chunks.
    Each chunk has: text (title + section), section_title.
    Falls back to the entire body if no ## headers exist.
    """
    chunks: list[dict[str, str]] = []
    sections = _H2.split(body)

    # sections alternates: [preamble, header1, content1, header2, content2, ...]
    preamble = sections[0].strip()
    if preamble:
        text = f"# {title}\ntags: {', '.join(tags)}\n\n{preamble[:_MAX_CHUNK_CHARS]}"
        chunks.append({"text": text, "section": "__intro__"})

    pairs = list(zip(sections[1::2], sections[2::2]))
    for hdr, body_part in pairs:
        hdr = hdr.strip()
        part = body_part.strip()
        if not part:
            continue
        text = f"# {title} — {hdr}\ntags: {', '.join(tags)}\n\n{part[:_MAX_CHUNK_CHARS]}"
        chunks.append({"text": text, "section": hdr})

    if not chunks:
        # No structure — use entire body as one chunk
        text = f"# {title}\ntags: {', '.join(tags)}\n\n{body.strip()[:_MAX_CHUNK_CHARS]}"
        chunks.append({"text": text, "section": "__full__"})

    return chunks


def _doc_id(file_path: Path, section: str) -> str:
    key = f"{file_path}::{section}"
    return hashlib.md5(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# ChromaDB helpers (mirrored from rag_memory.py — independent collection)
# ---------------------------------------------------------------------------

_db_lock = threading.Lock()
_chroma_client = None
_collection = None


def _get_collection():
    global _chroma_client, _collection
    if _collection is not None:
        return _collection
    with _db_lock:
        if _collection is not None:
            return _collection
        try:
            import chromadb

            from pathlib import Path as _Path

            db_dir = _Path(__file__).parent / "models" / "chroma_db"
            db_dir.mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(path=str(db_dir))
            _collection = _chroma_client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            return _collection
        except Exception:
            return None


def _embed(text: str) -> list[float] | None:
    try:
        import ollama
        r = ollama.embeddings(model=_EMBED_MODEL, prompt=text)
        return r["embedding"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Incremental sync state (in-memory; repopulated on restart from ChromaDB)
# ---------------------------------------------------------------------------

# Maps file path string → last-indexed mtime
_indexed_mtimes: dict[str, float] = {}


def _load_indexed_mtimes():
    """Populate _indexed_mtimes from ChromaDB metadata on startup."""
    global _indexed_mtimes
    col = _get_collection()
    if col is None:
        return
    try:
        all_items = col.get(include=["metadatas"])
        for meta in all_items.get("metadatas", []):
            if meta and "file_path" in meta and "mtime" in meta:
                path = meta["file_path"]
                mtime = float(meta["mtime"])
                if path not in _indexed_mtimes or _indexed_mtimes[path] < mtime:
                    _indexed_mtimes[path] = mtime
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core indexer
# ---------------------------------------------------------------------------

def _iter_vault_files():
    """Yield all .md files under VAULT_PATH, skipping excluded dirs."""
    if not VAULT_PATH.exists():
        return
    for root, dirs, files in os.walk(VAULT_PATH):
        # Prune skipped dirs in-place so os.walk doesn't recurse into them
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            if fname.endswith(".md"):
                yield Path(root) / fname


def _index_file(file_path: Path, col) -> int:
    """Index a single file. Returns number of chunks upserted."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0

    mtime = file_path.stat().st_mtime
    rel_path = str(file_path.relative_to(VAULT_PATH))
    fm_title, tags, body = _parse_frontmatter(content)
    title = _derive_title(file_path, fm_title)
    links = _extract_wikilinks(content)
    chunks = _chunk_note(title, tags, body)

    upserted = 0
    for chunk in chunks:
        emb = _embed(chunk["text"])
        if emb is None:
            continue
        doc_id = _doc_id(file_path, chunk["section"])
        meta: dict[str, Any] = {
            "file_path": rel_path,
            "title": title,
            "tags": ", ".join(tags),
            "section": chunk["section"],
            "links": ", ".join(links[:20]),
            "mtime": mtime,
        }
        try:
            col.upsert(
                ids=[doc_id],
                embeddings=[emb],
                documents=[chunk["text"]],
                metadatas=[meta],
            )
            upserted += 1
        except Exception:
            pass

    _indexed_mtimes[rel_path] = mtime
    return upserted


def _delete_stale(col, current_rel_paths: set[str]):
    """Remove indexed entries for files that no longer exist."""
    try:
        all_items = col.get(include=["metadatas", "ids"])
        ids_to_delete = []
        for doc_id, meta in zip(
            all_items.get("ids", []), all_items.get("metadatas", [])
        ):
            if meta and meta.get("file_path") not in current_rel_paths:
                ids_to_delete.append(doc_id)
        if ids_to_delete:
            col.delete(ids=ids_to_delete)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public sync API
# ---------------------------------------------------------------------------

_sync_status: dict[str, Any] = {
    "running": False,
    "last_sync": None,
    "total_chunks": 0,
    "total_files": 0,
    "vault_path": str(VAULT_PATH),
    "vault_exists": VAULT_PATH.exists(),
}


def sync(force: bool = False) -> dict[str, Any]:
    """
    Scan vault, (re-)index changed .md files, remove stale entries.
    Thread-safe. Returns sync stats.
    """
    col = _get_collection()
    if col is None:
        return {"error": "ChromaDB unavailable"}

    if _sync_status["running"]:
        return {"skipped": "sync already running"}

    _sync_status["running"] = True
    _load_indexed_mtimes()

    files = list(_iter_vault_files())
    current_rel_paths = {str(f.relative_to(VAULT_PATH)) for f in files}
    _delete_stale(col, current_rel_paths)

    total_chunks = 0
    indexed_files = 0

    for fp in files:
        rel = str(fp.relative_to(VAULT_PATH))
        mtime = fp.stat().st_mtime
        if not force and _indexed_mtimes.get(rel, 0) >= mtime:
            continue  # unchanged
        n = _index_file(fp, col)
        if n > 0:
            indexed_files += 1
            total_chunks += n

    _sync_status.update(
        running=False,
        last_sync=time.time(),
        total_chunks=col.count(),
        total_files=len(files),
        vault_path=str(VAULT_PATH),
        vault_exists=VAULT_PATH.exists(),
        last_run_files=indexed_files,
        last_run_chunks=total_chunks,
    )
    return dict(_sync_status)


def sync_background(force: bool = False):
    """Start sync in a daemon thread so it doesn't block startup."""
    t = threading.Thread(target=sync, args=(force,), daemon=True)
    t.start()


def _auto_sync_loop():
    """Periodic background sync every _SYNC_INTERVAL seconds."""
    time.sleep(10)  # delay first run to let app fully start
    while True:
        try:
            sync()
        except Exception:
            pass
        time.sleep(_SYNC_INTERVAL)


def start_auto_sync():
    """Call once at app startup to begin periodic background sync."""
    t = threading.Thread(target=_auto_sync_loop, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_vault(query: str, top_k: int = _TOP_K) -> list[dict[str, Any]]:
    """
    Semantic search over indexed vault notes.
    Returns list of {text, title, file_path, section, score} dicts.
    """
    col = _get_collection()
    if col is None or col.count() == 0:
        return _keyword_fallback(query, top_k)

    emb = _embed(query)
    if emb is None:
        return _keyword_fallback(query, top_k)

    try:
        results = col.query(
            query_embeddings=[emb],
            n_results=min(top_k, col.count()),
            include=["documents", "distances", "metadatas"],
        )
        docs = results["documents"][0] if results["documents"] else []
        dists = results["distances"][0] if results["distances"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []

        out = []
        for doc, dist, meta in zip(docs, dists, metas):
            if dist > 0.72:  # cosine distance threshold
                continue
            out.append(
                {
                    "text": doc,
                    "title": (meta or {}).get("title", ""),
                    "file_path": (meta or {}).get("file_path", ""),
                    "section": (meta or {}).get("section", ""),
                    "score": round(1 - dist, 3),
                }
            )
        return out
    except Exception:
        return _keyword_fallback(query, top_k)


def _keyword_fallback(query: str, top_k: int) -> list[dict[str, Any]]:
    """Simple keyword fallback when embeddings are unavailable."""
    terms = [t.lower() for t in query.split() if len(t) > 2]
    results = []
    for fp in _iter_vault_files():
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
            score = sum(content.lower().count(t) for t in terms)
            if score > 0:
                rel = str(fp.relative_to(VAULT_PATH))
                fm_title, tags, body = _parse_frontmatter(content)
                title = _derive_title(fp, fm_title)
                results.append(
                    {
                        "text": content[:800],
                        "title": title,
                        "file_path": rel,
                        "section": "__keyword__",
                        "score": min(score / 10, 1.0),
                    }
                )
        except Exception:
            pass
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Note listing + retrieval
# ---------------------------------------------------------------------------

def list_vault_notes() -> list[dict[str, Any]]:
    """Return metadata for all .md files in the vault (no content)."""
    notes = []
    for fp in _iter_vault_files():
        try:
            rel = str(fp.relative_to(VAULT_PATH))
            content = fp.read_text(encoding="utf-8", errors="ignore")
            fm_title, tags, _ = _parse_frontmatter(content)
            title = _derive_title(fp, fm_title)
            notes.append(
                {
                    "path": rel,
                    "title": title,
                    "tags": tags,
                    "folder": str(Path(rel).parent),
                    "modified": fp.stat().st_mtime,
                }
            )
        except Exception:
            pass
    notes.sort(key=lambda x: x["folder"] + "/" + x["title"])
    return notes


def get_vault_note(rel_path: str) -> dict[str, Any] | None:
    """Return title, tags, raw content for a single note by relative path."""
    fp = VAULT_PATH / rel_path
    if not fp.exists() or not fp.is_file():
        return None
    try:
        content = fp.read_text(encoding="utf-8", errors="ignore")
        fm_title, tags, body = _parse_frontmatter(content)
        title = _derive_title(fp, fm_title)
        links = _extract_wikilinks(content)
        return {
            "path": rel_path,
            "title": title,
            "tags": tags,
            "links": links,
            "content": content,
            "body": body,
        }
    except Exception:
        return None


def get_status() -> dict[str, Any]:
    """Return current sync status."""
    s = dict(_sync_status)
    s["vault_exists"] = VAULT_PATH.exists()
    return s


def build_graph() -> dict[str, Any]:
    """
    Return {nodes, links} for a D3 force-graph visualization.
    Nodes = vault notes. Edges = wikilinks between notes.
    """
    notes = list_vault_notes()
    if not notes:
        return {"nodes": [], "links": []}

    # Build lookup: title/stem (lower) → path for wikilink resolution
    title_to_path: dict[str, str] = {}
    stem_to_path: dict[str, str] = {}
    for n in notes:
        title_to_path[n["title"].lower()] = n["path"]
        stem_to_path[Path(n["path"]).stem.lower()] = n["path"]

    node_ids = {n["path"] for n in notes}
    nodes = [
        {
            "id": n["path"],
            "title": n["title"],
            "folder": n["folder"] if n["folder"] not in ("", ".") else "root",
            "tags": n["tags"],
        }
        for n in notes
    ]

    seen: set[frozenset] = set()
    links: list[dict[str, str]] = []
    for n in notes:
        note = get_vault_note(n["path"])
        if not note:
            continue
        for lnk in note.get("links", []):
            target = title_to_path.get(lnk.lower()) or stem_to_path.get(lnk.lower())
            if target and target in node_ids and target != n["path"]:
                key: frozenset = frozenset([n["path"], target])
                if key not in seen:
                    seen.add(key)
                    links.append({"source": n["path"], "target": target})

    return {"nodes": nodes, "links": links}


# Singleton convenience alias
vault = type("_Vault", (), {"sync": staticmethod(sync), "sync_background": staticmethod(sync_background)})()
