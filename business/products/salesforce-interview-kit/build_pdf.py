#!/usr/bin/env python3
"""Build INTERVIEW_KIT.pdf from INTERVIEW_KIT.md"""

import sys
import pathlib

try:
    import markdown2
    from weasyprint import HTML, CSS
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown2", "weasyprint"])
    import markdown2
    from weasyprint import HTML, CSS

BASE = pathlib.Path(__file__).parent
md_file = BASE / "INTERVIEW_KIT.md"
pdf_file = BASE / "INTERVIEW_KIT.pdf"

print(f"Reading {md_file}...")
md_content = md_file.read_text(encoding="utf-8")

print("Converting Markdown to HTML...")
html_body = markdown2.markdown(
    md_content,
    extras=["tables", "fenced-code-blocks", "code-friendly", "header-ids"]
)

css = """
@page {
    margin: 2cm 2.2cm;
    size: A4;
    @bottom-center {
        content: "MadjosBuilds — Salesforce Developer Interview Kit  |  Page " counter(page) " of " counter(pages);
        font-size: 9px;
        color: #888;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
}

body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 11px;
    line-height: 1.6;
    color: #1a1a2e;
    max-width: 100%;
}

h1 {
    font-size: 26px;
    color: #0b2545;
    border-bottom: 3px solid #0070d2;
    padding-bottom: 10px;
    margin-top: 0;
}

h2 {
    font-size: 18px;
    color: #0b2545;
    border-bottom: 2px solid #e8edf2;
    padding-bottom: 6px;
    margin-top: 32px;
    page-break-after: avoid;
}

h3 {
    font-size: 14px;
    color: #032d60;
    margin-top: 22px;
    page-break-after: avoid;
}

h4 {
    font-size: 12px;
    color: #0070d2;
    margin-top: 16px;
    page-break-after: avoid;
}

p { margin: 8px 0; }

blockquote {
    border-left: 4px solid #0070d2;
    background: #f0f6ff;
    margin: 16px 0;
    padding: 12px 16px;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #032d60;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 14px 0;
    font-size: 10.5px;
    page-break-inside: avoid;
}

th {
    background-color: #0070d2;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 7px 10px;
    border-bottom: 1px solid #dde4ee;
    vertical-align: top;
}

tr:nth-child(even) td { background-color: #f5f8fc; }

code {
    background-color: #f0f4f8;
    color: #032d60;
    font-family: 'Courier New', Courier, monospace;
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 3px;
}

pre {
    background-color: #0b2545;
    color: #cdd8e8;
    padding: 14px 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 9.5px;
    line-height: 1.5;
    margin: 12px 0;
    page-break-inside: avoid;
}

pre code {
    background: none;
    color: #cdd8e8;
    padding: 0;
    font-size: 9.5px;
}

ul, ol {
    padding-left: 22px;
    margin: 8px 0;
}

li { margin: 4px 0; }

hr {
    border: none;
    border-top: 1px solid #dde4ee;
    margin: 24px 0;
}

strong { color: #032d60; }

a { color: #0070d2; text-decoration: none; }
"""

full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Salesforce Developer Interview Kit — MadjosBuilds</title>
</head>
<body>
{html_body}
</body>
</html>"""

print("Generating PDF...")
HTML(string=full_html, base_url=str(BASE)).write_pdf(
    str(pdf_file),
    stylesheets=[CSS(string=css)]
)

size_kb = pdf_file.stat().st_size // 1024
print(f"PDF generated: {pdf_file} ({size_kb} KB)")
