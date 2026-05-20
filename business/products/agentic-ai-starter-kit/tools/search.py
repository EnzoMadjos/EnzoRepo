"""
Web Search Tool — DuckDuckGo (no API key required).
Falls back gracefully if network is unavailable.
"""

from __future__ import annotations
import urllib.parse
import requests
import re


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search DuckDuckGo and return top results as plain text.
    No API key needed — uses the HTML endpoint.
    """
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AgentKit/1.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        # Extract result snippets from HTML
        snippets = re.findall(
            r'<a class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL
        )
        clean = [re.sub(r"<[^>]+>", "", s).strip() for s in snippets[:max_results]]

        if not clean:
            return f"No results found for: {query}"

        lines = [f"{i+1}. {s}" for i, s in enumerate(clean)]
        return f"Search results for '{query}':\n" + "\n".join(lines)

    except Exception as e:
        return f"[Search unavailable: {e}]"
