"""
ATLAS Tool Executor
Native Ollama tool calling — uses the model's built-in function calling capability.
Tools are passed as Ollama-format dicts; results returned as plain strings.
"""

from typing import Any

# ── Ollama-native tool definitions ────────────────────────────────────────────
# Format matches what ollama.chat(tools=[...]) expects.

OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, documentation, prices, or anything outside training data. Always use this before answering questions about recent events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the full text of a specific URL. Use after web_search to read a relevant page in detail.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL (https://...) to fetch.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "Execute Python or bash code and return the output. Use for calculations, data processing, file operations, or any computation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "The code to execute."},
                    "language": {
                        "type": "string",
                        "description": "'python' (default) or 'bash'.",
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Permanently save an important fact, user preference, or piece of knowledge to long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "Clear statement of the fact to remember.",
                    }
                },
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search long-term memory for stored facts relevant to a topic or keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic or keyword to search memory for.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the user's local workspace. Use when the user asks you to read, review, explain, or modify a specific file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file within the workspace (e.g. 'local-chatbot/app.py').",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the files and subdirectories inside a workspace directory. Use when the user asks what files exist or to explore the project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path within the workspace. Use '' or '.' for the root.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search the text content of workspace files for a keyword or code pattern. Returns matching lines with file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text or pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Optional subdirectory to restrict the search. Use '' for entire workspace.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file in the user's local workspace with the given content. Use this to write code, create new files, or apply changes the user requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path for the file within the workspace (e.g. 'local-chatbot/hello.py').",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full content to write to the file.",
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "If true, create parent directories if they don't exist. Default true.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image from a text description. Use when the user asks to create, draw, generate, or visualize something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate.",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Image width in pixels. Default 1024.",
                    },
                    "height": {
                        "type": "integer",
                        "description": "Image height in pixels. Default 1024.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute a bash shell command on the user's local WSL machine and return the output. Use for system tasks, file operations, installing packages, running scripts, or anything that needs the terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to run.",
                    },
                    "workdir": {
                        "type": "string",
                        "description": "Optional working directory. Defaults to the workspace root.",
                    },
                },
                "required": ["command"],
            },
        },
    },
]


# Prompt note only — no JSON schema needed since we use native tool API
def build_tool_schema_prompt() -> str:
    names = [t["function"]["name"] for t in OLLAMA_TOOLS]
    return (
        "\n## TOOLS\n"
        f"You have access to these tools: {', '.join(names)}.\n"
        "Only use tools when truly necessary — do NOT use run_code for basic math, logic, or anything you can answer directly.\n"
        "Use web_search only when the answer requires current/real-world data you cannot know (news, prices, live info).\n"
        "Use remember when the user explicitly asks you to save something, or reveals a clear persistent preference.\n"
        "Use recall when the user asks about something you may have noted before.\n"
        "Use read_file when the user asks you to read, review, explain, or change a specific file.\n"
        "Use list_dir when the user asks what files exist or wants to explore the project.\n"
        "Use search_files when the user asks you to find something across files.\n"
        "Use write_file to create new files or save code the user asks you to write — always confirm the path with the user if unsure.\n"
        "Use generate_image when the user asks to create, draw, generate, or visualize an image.\n"
        "Use run_bash to execute shell commands on the user's machine — confirm with the user before running destructive commands.\n"
        "Most questions can and should be answered directly without any tool call."
    )


# ── Tool executor ─────────────────────────────────────────────────────────────


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with args dict. Returns observation string."""
    try:
        if name == "web_search":
            return _tool_web_search(args.get("query", ""))
        elif name == "web_fetch":
            return _tool_web_fetch(args.get("url", ""))
        elif name == "run_code":
            return _tool_run_code(args.get("code", ""), args.get("language", "python"))
        elif name == "remember":
            return _tool_remember(args.get("fact", ""))
        elif name == "recall":
            return _tool_recall(args.get("query", ""))
        elif name == "read_file":
            return _tool_read_file(args.get("path", ""))
        elif name == "list_dir":
            return _tool_list_dir(args.get("path", ""))
        elif name == "search_files":
            return _tool_search_files(args.get("query", ""), args.get("path", ""))
        elif name == "write_file":
            return _tool_write_file(
                args.get("path", ""),
                args.get("content", ""),
                args.get("create_dirs", True),
            )
        elif name == "generate_image":
            return _tool_generate_image(
                args.get("prompt", ""),
                args.get("width", 1024),
                args.get("height", 1024),
            )
        elif name == "run_bash":
            return _tool_run_bash(args.get("command", ""), args.get("workdir", ""))
        else:
            return f"[ERROR] Unknown tool: {name!r}"
    except Exception as exc:
        return f"[ERROR] Tool {name!r} failed: {exc}"


# ── Individual tool implementations ─────────────────────────────────────────


def _tool_web_search(query: str) -> str:
    if not query.strip():
        return "[ERROR] Empty search query."
    try:
        import re as _re2
        import urllib.parse
        import urllib.request
        from html.parser import HTMLParser

        # DuckDuckGo Lite — minimal stable HTML, text-only, no JS required
        encoded = urllib.parse.urlencode({"q": query, "kl": "us-en"})
        url = f"https://lite.duckduckgo.com/lite/?{encoded}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")

        # Lite page structure: results in <table> rows
        # Each result: <a class="result-link"> title </a>  +  <span class="link-text"> url </span>
        # + <td class="result-snippet"> snippet </td>
        class _LiteParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self._in_link = self._in_url = self._in_snip = False
                self._cur: dict = {}

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                cls = a.get("class", "")
                if tag == "a" and "result-link" in cls:
                    self._in_link = True
                    href = a.get("href", "")
                    # Unwrap DDG redirect: extract uddg= param
                    m = _re2.search(r"uddg=([^&]+)", href)
                    if m:
                        import urllib.parse as _ul

                        href = _ul.unquote(m.group(1))
                    self._cur = {"title": "", "url": href, "snippet": ""}
                elif tag == "span" and "link-text" in cls:
                    self._in_url = True
                elif tag == "td" and "result-snippet" in cls:
                    self._in_snip = True

            def handle_endtag(self, tag):
                if tag == "a" and self._in_link:
                    self._in_link = False
                if tag == "span" and self._in_url:
                    self._in_url = False
                if tag == "td" and self._in_snip:
                    self._in_snip = False
                    if self._cur.get("title"):
                        self.results.append(dict(self._cur))
                        self._cur = {}

            def handle_data(self, data):
                if self._in_link:
                    self._cur["title"] = (self._cur.get("title", "") + data).strip()
                elif self._in_url:
                    self._cur["url"] = data.strip()
                elif self._in_snip:
                    self._cur["snippet"] = (self._cur.get("snippet", "") + data).strip()

        parser = _LiteParser()
        parser.feed(html)
        results = [r for r in parser.results if r["title"]][:6]

        if not results:
            return f"[SEARCH] No results found for: {query!r}"

        lines = [f"[SEARCH RESULTS for '{query}']"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}")
            if r["url"]:
                lines.append(f"   URL: {r['url']}")
            if r["snippet"]:
                lines.append(f"   {r['snippet']}")

        # Auto-fetch top result when query needs detail, not just a quick fact
        _DETAIL_TRIGGERS = _re2.compile(
            r"\b(how|explain|what is|what are|why|tutorial|guide|steps|diff(?:erence)?|vs\b|review|release notes|changelog|docs|documentation|example|examples)\b",
            _re2.I,
        )
        if _DETAIL_TRIGGERS.search(query):
            try:
                from web_fetcher import extract_text_from_html, fetch_url_content

                # Try each result URL until we get clean readable text (skip JS-heavy pages)
                for r in results[:3]:
                    top_url = r.get("url", "")
                    if not top_url or not top_url.startswith("http"):
                        continue
                    try:
                        page = fetch_url_content(top_url, timeout=10)
                        text = extract_text_from_html(
                            page["html"], max_chars=50000
                        ).strip()
                        # Skip pages that are mostly JS/not readable prose
                        word_count = len(text.split())
                        if word_count < 80:
                            continue
                        # Check prose ratio: real text has lots of common short words
                        words = text.lower().split()
                        common = sum(
                            1
                            for w in words
                            if w
                            in {
                                "the",
                                "a",
                                "is",
                                "in",
                                "of",
                                "to",
                                "and",
                                "for",
                                "with",
                                "it",
                                "that",
                                "this",
                                "its",
                                "are",
                                "was",
                            }
                        )
                        if len(words) > 0 and common / len(words) < 0.03:
                            continue  # too few common words = still looks like code/JS
                        lines.append(f"\n[TOP RESULT CONTENT from {top_url}]")
                        lines.append(text[:3000])
                        break
                    except Exception:
                        continue
            except Exception:
                pass  # fetch failure is non-fatal — snippets still available

        return "\n".join(lines)
    except Exception as exc:
        return f"[SEARCH ERROR] {exc}"


def _tool_web_fetch(url: str) -> str:
    if not url.strip():
        return "[ERROR] No URL provided."
    try:
        from settings import MAX_WEB_TEXT_CHARS
        from web_fetcher import extract_text_from_html, fetch_url_content

        result = fetch_url_content(url, timeout=12)
        text = extract_text_from_html(result["html"], max_chars=MAX_WEB_TEXT_CHARS)
        return f"[PAGE CONTENT from {url}]\n{text[:4000]}"
    except Exception as exc:
        return f"[FETCH ERROR] {exc}"


def _tool_run_code(code: str, language: str = "python") -> str:
    if not code.strip():
        return "[ERROR] No code provided."
    import subprocess
    import tempfile
    import time
    from pathlib import Path

    lang = language.lower().strip()
    if lang not in ("python", "python3", "bash", "sh"):
        return f"[ERROR] Unsupported language: {lang!r}"
    ext = ".py" if lang in ("python", "python3") else ".sh"
    py = str(Path(__file__).resolve().parent / "venv" / "bin" / "python3")
    interpreter = [py] if lang in ("python", "python3") else ["bash"]
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp = f.name
        t0 = time.monotonic()
        r = subprocess.run(
            interpreter + [tmp], capture_output=True, text=True, timeout=15, cwd="/tmp"
        )
        ms = int((time.monotonic() - t0) * 1000)
        import os

        os.unlink(tmp)
        out = r.stdout[:3000]
        err = r.stderr[:1000]
        parts = [f"[CODE RESULT] exit={r.returncode} ({ms}ms)"]
        if out:
            parts.append(f"stdout:\n{out}")
        if err:
            parts.append(f"stderr:\n{err}")
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return "[CODE ERROR] Timed out after 15s."
    except Exception as exc:
        return f"[CODE ERROR] {exc}"


def _tool_remember(fact: str) -> str:
    if not fact.strip():
        return "[ERROR] No fact provided."
    try:
        from audit import append_audit
        from rag_memory import upsert_memory
        from training_memory import add_training

        add_training(fact.strip(), category="auto-memory")
        upsert_memory(fact.strip(), category="auto-memory")
        append_audit("auto_remember", fact.strip()[:120])
        return f"[MEMORY] Saved: {fact.strip()}"
    except Exception as exc:
        return f"[MEMORY ERROR] {exc}"


def _tool_recall(query: str) -> str:
    if not query.strip():
        return "[ERROR] No query provided."
    try:
        from rag_memory import search_memory

        matches = search_memory(query, top_k=6)
        if not matches:
            return f"[RECALL] No memories found matching '{query}'."
        lines = [f"[RECALL] Relevant memories for '{query}':"]
        for m in matches:
            lines.append(f"- {m[:200]}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[RECALL ERROR] {exc}"


def _tool_read_file(path: str) -> str:
    if not path.strip():
        return "[ERROR] No path provided."
    try:
        import file_access as _fa

        result = _fa.read_file(path.strip())
        if "error" in result:
            return f"[READ_FILE ERROR] {result['error']}"
        trunc = " (truncated)" if result.get("truncated") else ""
        return f"[FILE: {result['path']} | {result['lines']} lines{trunc}]\n{result['content']}"
    except Exception as exc:
        return f"[READ_FILE ERROR] {exc}"


def _tool_list_dir(path: str) -> str:
    try:
        import file_access as _fa

        result = _fa.list_dir((path or "").strip())
        if "error" in result:
            return f"[LIST_DIR ERROR] {result['error']}"
        lines = [f"[DIR: /{result['path']}]"]
        for d in result.get("dirs", []):
            lines.append(f"  📁 {d['name']}/")
        for f in result.get("files", []):
            kb = round(f["size"] / 1024, 1)
            lines.append(f"  📄 {f['name']}  ({kb} kb)")
        if not result.get("dirs") and not result.get("files"):
            lines.append("  (empty)")
        return "\n".join(lines)
    except Exception as exc:
        return f"[LIST_DIR ERROR] {exc}"


def _tool_search_files(query: str, path: str = "") -> str:
    if not query.strip():
        return "[ERROR] No search query provided."
    try:
        import file_access as _fa

        result = _fa.search_files(
            query.strip(), path.strip() if path else "", max_results=20
        )
        if "error" in result:
            return f"[SEARCH_FILES ERROR] {result['error']}"
        hits = result.get("results", [])
        if not hits:
            return f"[SEARCH_FILES] No matches found for '{query}'."
        lines = [f"[SEARCH_FILES] Results for '{query}':"]
        for h in hits:
            lines.append(f"  {h['path']}:{h['line']}  {h['snippet']}")
        return "\n".join(lines)
    except Exception as exc:
        return f"[SEARCH_FILES ERROR] {exc}"


def _tool_write_file(path: str, content: str, create_dirs: bool = True) -> str:
    if not path.strip():
        return "[ERROR] No path provided."
    try:
        import file_access as _fa

        result = _fa.write_file(path.strip(), content, create_dirs=create_dirs)
        if "error" in result:
            return f"[WRITE_FILE ERROR] {result['error']}"
        return f"[WRITE_FILE] Written {result['written']} bytes to {result['path']}"
    except Exception as exc:
        return f"[WRITE_FILE ERROR] {exc}"


def _tool_generate_image(prompt: str, width: int = 1024, height: int = 1024) -> str:
    if not prompt.strip():
        return "[ERROR] No image prompt provided."
    try:
        import urllib.parse

        encoded = urllib.parse.quote(prompt.strip())
        w = max(256, min(2048, int(width)))
        h = max(256, min(2048, int(height)))
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={w}&height={h}&nologo=true&enhance=true"
        # Return a special marker the UI can render as an <img>
        return f"[IMAGE_URL] {url}"
    except Exception as exc:
        return f"[GENERATE_IMAGE ERROR] {exc}"


def _rtk_wrap(command: str) -> str:
    """Rewrite known noisy commands to their rtk-compressed equivalents.
    Only rewrites when rtk is available and the command matches a known pattern.
    Falls back to original command silently if rtk is not installed."""
    import re as _re
    import shutil

    rtk = shutil.which("rtk") or shutil.which("/home/enzo/.local/bin/rtk")
    if not rtk:
        return command

    cmd = command.strip()

    # Patterns: (regex to match the raw command, rtk replacement template)
    # $1 captures everything after the base command keyword
    _PATTERNS = [
        # git subcommands
        (r"^git\s+(.+)", r"rtk git \1"),
        # ls / directory listing
        (r"^ls\b(.*)", r"rtk ls\1"),
        # grep / ripgrep
        (r"^(grep|rg)\b(.*)", r"rtk grep\2"),
        # find
        (r"^find\b(.*)", r"rtk find\1"),
        # cat / read file
        (r"^cat\b(.*)", r"rtk read\1"),
        # pytest
        (r"^pytest\b(.*)", r"rtk pytest\1"),
        # cargo test / build / clippy
        (r"^cargo\s+(test|build|clippy)(.*)", r"rtk cargo \1\2"),
        # docker ps / logs
        (r"^docker\s+(ps|logs|images|compose)\b(.*)", r"rtk docker \1\2"),
        # kubectl
        (r"^kubectl\s+(get\s+pods?|logs|get\s+services?)\b(.*)", r"rtk kubectl\2"),
        # pip list / outdated
        (r"^pip\s+(list|outdated)(.*)", r"rtk pip \1\2"),
        # npm / pnpm test/lint
        (r"^(npm|pnpm)\s+(test|list)(.*)", r"rtk \1 \2\3"),
        # env (filtered)
        (r"^env\b(.*)", r"rtk env\1"),
    ]

    for pattern, replacement in _PATTERNS:
        m = _re.match(pattern, cmd, _re.I)
        if m:
            rewritten = _re.sub(pattern, replacement, cmd, flags=_re.I)
            return rewritten

    return command


def _tool_run_bash(command: str, workdir: str = "") -> str:
    if not command.strip():
        return "[ERROR] No command provided."
    # Block dangerous patterns
    import re as _re

    _BLOCKED = _re.compile(
        r"\b(rm\s+-rf\s+/|mkfs|dd\s+if=|chmod\s+777\s+/|shutdown|reboot|:\(\)\{.*\})\b",
        _re.I,
    )
    if _BLOCKED.search(command):
        return "[BLOCKED] That command was blocked for safety. Ask the user to confirm before running destructive operations."
    # Wrap with RTK for token-efficient output where applicable
    command = _rtk_wrap(command)
    try:
        import os
        import subprocess
        from pathlib import Path

        import file_access as _fa

        cwd = str(_fa._WORKSPACE_ROOT)
        if workdir:
            candidate = (_fa._WORKSPACE_ROOT / workdir).resolve()
            if str(candidate).startswith(str(_fa._WORKSPACE_ROOT)):
                cwd = str(candidate)
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        parts = []
        if out:
            parts.append(f"STDOUT:\n{out[:4000]}")
        if err:
            parts.append(f"STDERR:\n{err[:1000]}")
        if result.returncode != 0:
            parts.append(f"EXIT CODE: {result.returncode}")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return "[BASH ERROR] Command timed out after 30 seconds."
    except Exception as exc:
        return f"[BASH ERROR] {exc}"
