"""Simple PDF/HTML storage utilities for PITOGO.

Attempts to render HTML to PDF using WeasyPrint or wkhtmltopdf if available.
Falls back to storing the HTML file and returns that path.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional


def _write_html(html: str, path: Path) -> Path:
    path.write_text(html, encoding="utf-8")
    return path


def _weasyprint_pdf(html: str, pdf_path: Path) -> bool:
    try:
        from weasyprint import HTML

        HTML(string=html).write_pdf(str(pdf_path))
        return True
    except Exception:
        return False


def _wkhtmltopdf(html: str, pdf_path: Path) -> bool:
    wk = shutil.which("wkhtmltopdf")
    if not wk:
        return False
    # write to a temp html file and call wkhtmltopdf
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(html)
        tmpname = tf.name
    try:
        subprocess.check_call([wk, tmpname, str(pdf_path)])
        return True
    except Exception:
        return False
    finally:
        try:
            Path(tmpname).unlink()
        except Exception:
            pass


def render_and_store(html: str, dest_dir: Path, base_name: str) -> str:
    """Store HTML and try to produce a PDF.

    Returns the filesystem path (string) of the PDF if produced, otherwise the HTML path.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    html_path = dest_dir / f"{base_name}.html"
    _write_html(html, html_path)

    pdf_path = dest_dir / f"{base_name}.pdf"
    # Try WeasyPrint first, then wkhtmltopdf.
    if _weasyprint_pdf(html, pdf_path):
        return str(pdf_path)
    if _wkhtmltopdf(html, pdf_path):
        return str(pdf_path)

    return str(html_path)
