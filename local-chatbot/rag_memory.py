"""
RAG Memory — vector store for Atlas training entries.
Uses ChromaDB (fully local, no server needed) + Ollama embeddings.
Falls back to BM25-style keyword search if embeddings are unavailable.
"""

import hashlib as _hash
import json as _json
import time as _time
from pathlib import Path
from typing import Optional

_DB_DIR = Path(__file__).parent / "models" / "chroma_db"
_COLLECTION = "atlas_memory"
_EMBED_MODEL = "nomic-embed-text"  # fast local embedding model via Ollama
_TOP_K = 6  # memories to inject per query

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb

        _DB_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_DB_DIR))
        _collection = _client.get_or_create_collection(
            name=_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except Exception:
        return None


def _embed(text: str) -> list[float] | None:
    """Get embedding from Ollama. Returns None if unavailable."""
    try:
        import ollama

        r = ollama.embeddings(model=_EMBED_MODEL, prompt=text)
        return r["embedding"]
    except Exception:
        return None


def _doc_id(text: str) -> str:
    return _hash.md5(text.encode()).hexdigest()


# ── Public API ───────────────────────────────────────────────────────────────


def upsert_memory(text: str, category: str = "training") -> bool:
    """Add or update a memory entry in the vector store."""
    col = _get_collection()
    if col is None:
        return False
    emb = _embed(text)
    if emb is None:
        return False
    try:
        doc_id = _doc_id(text)
        col.upsert(
            ids=[doc_id],
            embeddings=[emb],
            documents=[text],
            metadatas=[{"category": category, "ts": int(_time.time())}],
        )
        return True
    except Exception:
        return False


def search_memory(query: str, top_k: int = _TOP_K) -> list[str]:
    """Return top_k most relevant memory entries for a query."""
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
            include=["documents", "distances"],
        )
        docs = results["documents"][0] if results["documents"] else []
        dists = results["distances"][0] if results["distances"] else []
        # Filter out very low similarity (distance > 0.7 = cosine sim < 0.3)
        return [d for d, dist in zip(docs, dists) if dist < 0.7]
    except Exception:
        return _keyword_fallback(query, top_k)


def _keyword_fallback(query: str, top_k: int) -> list[str]:
    """Simple keyword search over training_memory as fallback."""
    try:
        from training_memory import list_training

        entries = list_training()
        kw = query.lower().split()
        scored = []
        for e in entries:
            text = e.get("entry") or e.get("content") or ""
            score = sum(1 for w in kw if w in text.lower())
            if score > 0:
                scored.append((score, text))
        scored.sort(reverse=True)
        return [t for _, t in scored[:top_k]]
    except Exception:
        return []


def sync_all_training() -> int:
    """Sync all existing training_memory entries into the vector store. Returns count synced."""
    try:
        from training_memory import list_training

        entries = list_training()
        count = 0
        for e in entries:
            text = e.get("entry") or e.get("content") or ""
            if text and upsert_memory(text, e.get("category", "training")):
                count += 1
        return count
    except Exception:
        return 0


def memory_count() -> int:
    col = _get_collection()
    if col is None:
        return 0
    try:
        return col.count()
    except Exception:
        return 0
