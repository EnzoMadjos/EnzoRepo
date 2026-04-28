#!/usr/bin/env python3
"""Convert docx source templates to HTML files (mammoth).

Place docx files in `templates/docs/source_documents/` and run this script
to produce `templates/certs/<slug>.html` files that can be used as Jinja
templates for certificates.
"""

import re
import sys
from pathlib import Path

try:
    import mammoth
except Exception as e:
    print("mammoth not installed. Run: pip install mammoth", file=sys.stderr)
    raise


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "templates" / "docs" / "source_documents"
DST_DIR = ROOT / "templates" / "certs"
DST_DIR.mkdir(parents=True, exist_ok=True)


def slug_name(name: str) -> str:
    s = re.sub(r"\s+", "_", name)
    s = re.sub(r"[^0-9a-zA-Z_\-]", "", s)
    return s.lower()


def convert_file(p: Path):
    out_name = slug_name(p.stem) + ".html"
    out_path = DST_DIR / out_name
    print(f"Converting {p.name} -> {out_path.name}")
    with p.open("rb") as fh:
        result = mammoth.convert_to_html(fh)
        html = result.value
    # Simple wrapper to ensure valid HTML document
    wrapped = f"<!doctype html>\n<html><head><meta charset='utf-8'/><title>{p.stem}</title></head><body>\n{html}\n</body></html>"
    out_path.write_text(wrapped, encoding="utf-8")


def main():
    if not SRC_DIR.exists():
        print("No source documents directory found:", SRC_DIR)
        return
    files = sorted(SRC_DIR.glob("*.docx"))
    if not files:
        print("No .docx files found in", SRC_DIR)
        return
    for p in files:
        try:
            convert_file(p)
        except Exception as e:
            print("Failed to convert", p, e)


if __name__ == "__main__":
    main()
