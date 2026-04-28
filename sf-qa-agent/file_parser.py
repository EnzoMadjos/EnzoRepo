"""
file_parser.py — extract plain text from uploaded files or raw paste.

Supported sources:
  - str / bytes  (raw paste, already text)
  - .txt
  - .docx  (python-docx)
  - .pdf   (pymupdf / fitz)
"""

from __future__ import annotations

import io
from pathlib import Path


def parse_bytes(filename: str, data: bytes) -> str:
    """Parse uploaded file bytes into plain text based on file extension."""
    ext = Path(filename).suffix.lower()

    if ext in (".txt", ""):
        return data.decode("utf-8", errors="replace").strip()

    if ext == ".docx":
        return _parse_docx(data)

    if ext == ".pdf":
        return _parse_pdf(data)

    raise ValueError(
        f"Unsupported file type: '{ext}'. Please upload .txt, .docx, or .pdf."
    )


def parse_text(text: str) -> str:
    """Sanitise and return raw pasted text."""
    return text.strip()


def _parse_docx(data: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        raise RuntimeError("python-docx is not installed. Run: pip install python-docx")

    doc = docx.Document(io.BytesIO(data))
    lines = [para.text for para in doc.paragraphs]
    return "\n".join(lines).strip()


def _parse_pdf(data: bytes) -> str:
    try:
        import fitz  # pymupdf
    except ImportError:
        raise RuntimeError("PyMuPDF is not installed. Run: pip install pymupdf")

    text_parts: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()
