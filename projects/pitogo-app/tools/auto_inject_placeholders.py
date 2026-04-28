#!/usr/bin/env python3
"""Heuristically inject Jinja placeholders into converted cert HTML files.

This script edits files in `templates/certs/` in-place, creating `.bak`
backups. It looks for common label patterns (Full Name, Age, Birthdate,
Address, Barangay, City, Purpose, Control Number) and replaces nearby
literal values with Jinja placeholders (e.g. `{{ resident.full_name }}`).

Run locally after the importer: `python tools/auto_inject_placeholders.py`
"""
from pathlib import Path
import re
import sys

try:
    from bs4 import BeautifulSoup, NavigableString
except Exception as exc:
    print("BeautifulSoup (bs4) is required. Install with: pip install beautifulsoup4", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]
CERTS_DIR = ROOT / "templates" / "certs"

MAPPINGS = [
    (re.compile(r'\bFull\s*Name\b', re.I), '{{ resident.full_name }}'),
    (re.compile(r'\bAge\b', re.I), '{{ resident.age }}'),
    (re.compile(r'\bBirth(?:date)?\b|\bDOB\b', re.I), '{{ resident.birthdate_fmt }}'),
    (re.compile(r'\bAddress(?: Line)?\b', re.I), '{{ household.address_line }}'),
    (re.compile(r'\bBarangay\b', re.I), '{{ household.barangay }}'),
    (re.compile(r'\bCity\b', re.I), '{{ household.city }}'),
    (re.compile(r'\bZip\b|\bPostal\b', re.I), '{{ household.zip_code }}'),
    (re.compile(r'\bPurpose\b', re.I), '{{ meta.purpose }}'),
    (re.compile(r'\bControl(?: Number| No| #)?\b', re.I), '{{ control_number }}'),
]


def replace_in_text_node(text_node, regex, placeholder):
    orig = str(text_node)
    # Replace patterns like 'Label: value' -> 'Label: {{ placeholder }}'
    new = re.sub(r'(?i)(' + regex.pattern + r')\s*[:\-]?\s*([^\n<]+)', lambda m: f"{m.group(1)}: {placeholder}", orig)
    if new != orig:
        text_node.replace_with(new)
        return True
    return False


def inject_into_file(p: Path) -> bool:
    txt = p.read_text(encoding='utf-8')
    soup = BeautifulSoup(txt, 'html.parser')
    changed = False

    # First pass: simple text-node replacements
    for text_node in list(soup.find_all(string=True)):
        # skip template placeholders
        if '{{' in text_node or '}}' in text_node:
            continue
        for regex, placeholder in MAPPINGS:
            if regex.search(text_node):
                ok = replace_in_text_node(text_node, regex, placeholder)
                if ok:
                    changed = True
                    break

    # Second pass: label nodes in <strong>/<b> etc followed by value nodes
    if not changed:
        for label_tag in soup.find_all(['strong', 'b', 'th', 'label']):
            txt = label_tag.get_text(strip=True)
            for regex, placeholder in MAPPINGS:
                if regex.search(txt):
                    # look for next sibling text node with value
                    sib = label_tag.next_sibling
                    # skip whitespace-only siblings
                    while sib and isinstance(sib, NavigableString) and not sib.strip():
                        sib = sib.next_sibling
                    if isinstance(sib, NavigableString):
                        sib.replace_with(' ' + placeholder)
                        changed = True
                        break
                    elif sib and hasattr(sib, 'string') and sib.string and sib.string.strip():
                        sib.string.replace_with(placeholder)
                        changed = True
                        break
            if changed:
                break

    if changed:
        bak = p.with_suffix(p.suffix + '.bak')
        bak.write_text(txt, encoding='utf-8')
        p.write_text(str(soup), encoding='utf-8')
        print('Patched:', p.name)
    return changed


def simulate_inject_into_file(p: Path) -> dict:
    """Simulate placeholder injection for a single file.

    Returns a dict: { 'patched': bool, 'replacements': [ {file, type, before, after}, ... ], 'patched_html': str|None }
    Does not write any files.
    """
    txt = p.read_text(encoding='utf-8')
    soup = BeautifulSoup(txt, 'html.parser')
    changed = False
    replacements: list[dict] = []

    # First pass: simple text-node replacements
    for text_node in list(soup.find_all(string=True)):
        if '{{' in text_node or '}}' in text_node:
            continue
        for regex, placeholder in MAPPINGS:
            if regex.search(text_node):
                orig = str(text_node)
                new = re.sub(r'(?i)(' + regex.pattern + r')\s*[:\-]?\s*([^\n<]+)', lambda m: f"{m.group(1)}: {placeholder}", orig)
                if new != orig:
                    replacements.append({'file': p.name, 'type': 'text_node', 'before': orig.strip(), 'after': new.strip()})
                    text_node.replace_with(new)
                    changed = True
                    break
    # Second pass: label nodes in <strong>/<b> etc followed by value nodes
    if not changed:
        for label_tag in soup.find_all(['strong', 'b', 'th', 'label']):
            txtlbl = label_tag.get_text(strip=True)
            for regex, placeholder in MAPPINGS:
                if regex.search(txtlbl):
                    sib = label_tag.next_sibling
                    # skip whitespace-only siblings
                    while sib and isinstance(sib, NavigableString) and not sib.strip():
                        sib = sib.next_sibling
                    if isinstance(sib, NavigableString):
                        before = str(sib)
                        after = ' ' + placeholder
                        replacements.append({'file': p.name, 'type': 'sibling_text', 'before': before.strip(), 'after': after.strip()})
                        sib.replace_with(after)
                        changed = True
                        break
                    elif sib and hasattr(sib, 'string') and sib.string and sib.string.strip():
                        before = str(sib.string)
                        replacements.append({'file': p.name, 'type': 'sibling_node', 'before': before.strip(), 'after': placeholder})
                        sib.string.replace_with(placeholder)
                        changed = True
                        break
            if changed:
                break

    return {'patched': changed, 'replacements': replacements, 'patched_html': str(soup) if changed else None}


def main():
    if not CERTS_DIR.exists():
        print('No certs directory at', CERTS_DIR)
        return
    files = sorted(CERTS_DIR.glob('*.html'))
    for f in files:
        try:
            inject_into_file(f)
        except Exception as e:
            print('Failed:', f.name, e)


if __name__ == '__main__':
    main()
