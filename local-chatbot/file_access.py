"""
file_access.py — Secure sandboxed file system access for ATLAS.

ATLAS can read, list, search, and write files within a configured workspace root.
Path traversal attacks are blocked — no access outside the workspace.

Config (env vars):
  ATLAS_WORKSPACE  — absolute path to the workspace root (default: ~/ai-lab)
  ATLAS_FS_WRITE   — set to "1" to allow write access (default: read-only)
"""

import os as _os
import re as _re
from pathlib import Path
from typing import Optional

# ── Config ───────────────────────────────────────────────────────────────────
_DEFAULT_WORKSPACE = Path.home() / "ai-lab"
_WORKSPACE_ROOT = Path(
    _os.environ.get("ATLAS_WORKSPACE", str(_DEFAULT_WORKSPACE))
).resolve()
_WRITE_ENABLED = _os.environ.get("ATLAS_FS_WRITE", "0") == "1"

# File extensions ATLAS is allowed to read
_READABLE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".cfg",
    ".ini",
    ".md",
    ".txt",
    ".rst",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".csv",
    ".xml",
    ".apex",
    ".cls",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".tf",
    ".hcl",
    ".dockerfile",
}

# Dirs to skip when listing/indexing
_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "chroma_db",
    "models",
    ".idea",
    ".vscode-server",
}

MAX_READ_BYTES = 256 * 1024  # 256 KB per file
MAX_LIST_ITEMS = 200


# ── Internal helpers ─────────────────────────────────────────────────────────


def _safe_resolve(rel_path: str) -> Optional[Path]:
    """Resolve a relative path inside workspace; returns None if escape detected."""
    try:
        target = (_WORKSPACE_ROOT / rel_path).resolve()
        target.relative_to(_WORKSPACE_ROOT)  # raises ValueError if outside
        return target
    except (ValueError, Exception):
        return None


def workspace_root() -> str:
    return str(_WORKSPACE_ROOT)


# ── Public API ───────────────────────────────────────────────────────────────


def list_dir(rel_path: str = "") -> dict:
    """List files and subdirectories at rel_path within the workspace."""
    target = _safe_resolve(rel_path)
    if target is None:
        return {"error": "Path outside workspace"}
    if not target.exists():
        return {"error": f"Path not found: {rel_path}"}
    if not target.is_dir():
        return {"error": f"Not a directory: {rel_path}"}

    dirs, files = [], []
    try:
        for item in sorted(target.iterdir())[:MAX_LIST_ITEMS]:
            rel = str(item.relative_to(_WORKSPACE_ROOT))
            if item.is_dir():
                if item.name not in _SKIP_DIRS:
                    dirs.append({"name": item.name, "path": rel})
            else:
                if item.suffix.lower() in _READABLE_EXTS:
                    files.append(
                        {
                            "name": item.name,
                            "path": rel,
                            "size": item.stat().st_size,
                            "ext": item.suffix.lower(),
                        }
                    )
    except PermissionError:
        return {"error": "Permission denied"}

    return {
        "path": (
            str(target.relative_to(_WORKSPACE_ROOT))
            if target != _WORKSPACE_ROOT
            else ""
        ),
        "dirs": dirs,
        "files": files,
    }


def read_file(rel_path: str) -> dict:
    """Read a file's contents. Returns chunks if > MAX_READ_BYTES."""
    target = _safe_resolve(rel_path)
    if target is None:
        return {"error": "Path outside workspace"}
    if not target.exists():
        return {"error": f"File not found: {rel_path}"}
    if not target.is_file():
        return {"error": f"Not a file: {rel_path}"}
    if target.suffix.lower() not in _READABLE_EXTS:
        return {"error": f"File type not readable: {target.suffix}"}

    size = target.stat().st_size
    try:
        raw = target.read_bytes()[:MAX_READ_BYTES]
        content = raw.decode("utf-8", errors="replace")
        return {
            "path": rel_path,
            "content": content,
            "size": size,
            "truncated": size > MAX_READ_BYTES,
            "lines": content.count("\n") + 1,
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(rel_path: str, content: str, create_dirs: bool = True) -> dict:
    """Write content to a file. Only allowed if ATLAS_FS_WRITE=1."""
    if not _WRITE_ENABLED:
        return {"error": "Write access disabled. Set ATLAS_FS_WRITE=1 to enable."}
    target = _safe_resolve(rel_path)
    if target is None:
        return {"error": "Path outside workspace"}
    if target.suffix.lower() not in _READABLE_EXTS:
        return {"error": f"File type not writable: {target.suffix}"}
    try:
        if create_dirs:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": rel_path, "written": len(content), "ok": True}
    except Exception as e:
        return {"error": str(e)}


def search_files(query: str, rel_path: str = "", max_results: int = 20) -> list[dict]:
    """
    Search files under rel_path for text matching query.
    Returns list of {path, line_no, snippet} matches.
    """
    base = _safe_resolve(rel_path)
    if base is None or not base.exists():
        return []

    pattern = _re.compile(_re.escape(query), _re.IGNORECASE)
    matches = []

    for fpath in base.rglob("*"):
        if len(matches) >= max_results:
            break
        if not fpath.is_file():
            continue
        if fpath.suffix.lower() not in _READABLE_EXTS:
            continue
        # skip excluded dirs
        if any(part in _SKIP_DIRS for part in fpath.parts):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    rel = str(fpath.relative_to(_WORKSPACE_ROOT))
                    matches.append(
                        {
                            "path": rel,
                            "line": i,
                            "snippet": line.strip()[:200],
                        }
                    )
                    if len(matches) >= max_results:
                        break
        except Exception:
            continue

    return matches


def find_files(name_pattern: str, rel_path: str = "") -> list[dict]:
    """Find files by name pattern (glob) within rel_path."""
    base = _safe_resolve(rel_path)
    if base is None or not base.exists():
        return []

    results = []
    try:
        for fpath in sorted(base.rglob(name_pattern))[:MAX_LIST_ITEMS]:
            if any(part in _SKIP_DIRS for part in fpath.parts):
                continue
            if fpath.is_file() and fpath.suffix.lower() in _READABLE_EXTS:
                rel = str(fpath.relative_to(_WORKSPACE_ROOT))
                results.append(
                    {
                        "name": fpath.name,
                        "path": rel,
                        "size": fpath.stat().st_size,
                    }
                )
    except Exception:
        pass
    return results
