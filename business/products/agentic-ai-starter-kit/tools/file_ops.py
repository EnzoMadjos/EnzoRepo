"""
File Operations Tool — read, write, and list files safely.
Restricts operations to the current working directory only.
"""

from __future__ import annotations
import os


def read_file(filepath: str) -> str:
    """Read a file and return its contents."""
    safe_path = _safe_path(filepath)
    if not os.path.exists(safe_path):
        return f"[Error] File not found: {filepath}"
    with open(safe_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath: str, content: str) -> str:
    """Write content to a file, creating directories if needed."""
    safe_path = _safe_path(filepath)
    os.makedirs(os.path.dirname(safe_path) or ".", exist_ok=True)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"[OK] Written to {filepath}"


def list_files(directory: str = ".") -> str:
    """List files in a directory."""
    safe_path = _safe_path(directory)
    if not os.path.isdir(safe_path):
        return f"[Error] Directory not found: {directory}"
    entries = os.listdir(safe_path)
    return "\n".join(sorted(entries)) if entries else "(empty directory)"


def _safe_path(filepath: str) -> str:
    """Prevent path traversal — restrict to cwd."""
    cwd = os.path.abspath(".")
    resolved = os.path.abspath(os.path.join(cwd, filepath))
    if not resolved.startswith(cwd):
        raise PermissionError(f"Access denied: path outside working directory.")
    return resolved
