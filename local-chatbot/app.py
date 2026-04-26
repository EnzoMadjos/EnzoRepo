from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json as _json
import ollama
import urllib.parse
import subprocess as _subprocess
import sys as _sys
import os as _os
from pathlib import Path

# Auto-load .env from the same directory as this file
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _os.environ.setdefault(_k.strip(), _v.strip())

# ── LLM router: GitHub Models → Local Ollama ─────────────────────────────
_GITHUB_API_KEY  = _os.environ.get("ATLAS_GITHUB_API_KEY", "")
_GITHUB_BASE_URL = "https://models.inference.ai.azure.com"
_GITHUB_MODEL    = _os.environ.get("ATLAS_GITHUB_MODEL", "gpt-4.1")
_GITHUB_MODEL_OVERRIDE: str = ""  # per-session model override

_LOCAL_MODEL     = "atlas"

# Track which cloud backends are rate-limited (reset after TTL)
import threading as _thr
import socket as _socket
import time as _time_mod
_RATE_LIMITED: dict = {"github": 0.0}
_RATE_LIMIT_TTL = 3600.0  # 1 hour cooldown after 429

# Manual provider override: "github", "local", or "" for auto
_PROVIDER_OVERRIDE: str = ""

def _mark_rate_limited(provider: str):
    _RATE_LIMITED[provider] = _time_mod.monotonic()

def _is_rate_limited(provider: str) -> bool:
    since = _RATE_LIMITED.get(provider, 0.0)
    return (_time_mod.monotonic() - since) < _RATE_LIMIT_TTL

# Cache: re-check connectivity every 60 s to avoid per-request overhead
_NET_CACHE: dict = {"online": False, "checked_at": 0.0}
_NET_TTL = 60.0

def _probe_internet() -> bool:
    try:
        _socket.setdefaulttimeout(3)
        _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

def is_online() -> bool:
    now = _time_mod.monotonic()
    if now - _NET_CACHE["checked_at"] > _NET_TTL:
        _NET_CACHE["online"] = _probe_internet()
        _NET_CACHE["checked_at"] = now
    return _NET_CACHE["online"]

def use_cloud() -> bool:
    """True when cloud backend will be used."""
    if _PROVIDER_OVERRIDE == "local":
        return False
    if _PROVIDER_OVERRIDE == "github":
        return bool(_GITHUB_API_KEY)
    if not is_online():
        return False
    if _GITHUB_API_KEY and not _is_rate_limited("github"):
        return True
    return False

def _active_cloud_provider() -> str:
    """Returns 'github' or 'local'."""
    if _PROVIDER_OVERRIDE == "local":
        return "local"
    if _PROVIDER_OVERRIDE == "github":
        return "github" if _GITHUB_API_KEY else "local"
    if not is_online():
        return "local"
    if _GITHUB_API_KEY and not _is_rate_limited("github"):
        return "github"
    return "local"

def _cloud_client(provider: str = None):
    if provider is None:
        provider = _active_cloud_provider()
    try:
        from openai import OpenAI
        if provider == "github":
            return OpenAI(api_key=_GITHUB_API_KEY, base_url=_GITHUB_BASE_URL)
    except ImportError:
        pass
    return None

def _cloud_model(provider: str = None) -> str:
    return _GITHUB_MODEL_OVERRIDE if _GITHUB_MODEL_OVERRIDE else _GITHUB_MODEL

def llm_chat(messages: list, stream: bool = False, **kwargs):
    """Unified chat call — GitHub Models → local Ollama."""
    provider = _active_cloud_provider()
    if provider == "github":
        client = _cloud_client("github")
        if client:
            try:
                extra = {k: v for k, v in kwargs.items() if k in ("temperature", "max_tokens")}
                if kwargs.get("tools"):
                    extra["tools"] = kwargs["tools"]
                    extra["tool_choice"] = kwargs.get("tool_choice", "auto")
                return ("github", client.chat.completions.create(
                    model=_GITHUB_MODEL,
                    messages=messages,
                    stream=stream,
                    **extra,
                ))
            except Exception as _e:
                if "429" in str(_e) or "rate_limit" in str(_e).lower():
                    _mark_rate_limited("github")
                else:
                    raise
    # Local Ollama fallback
    opts = {}
    if "temperature" in kwargs:
        opts["temperature"] = kwargs["temperature"]
    opts["num_ctx"] = kwargs.get("num_ctx", 8192)
    return ("local", ollama.chat(
        model=_LOCAL_MODEL,
        messages=messages,
        stream=stream,
        options=opts,
        tools=kwargs.get("tools"),
    ))
# ─────────────────────────────────────────────────────────────────────────

from auth import verify_api_key
from audit import append_audit, read_audit_history
from atlas_loader import load_atlas_prompt
from runtime_config import (
    set_web_access_allowlist,
    set_web_fetch_enabled,
    web_access_allowlist,
    web_fetch_enabled,
)
from settings import MAX_WEB_TEXT_CHARS
from nickname_profile import get_preferred_nickname, load_nickname_profile, set_preferred_nickname
from persona_store import load_persona_summary, save_persona_summary
from trait_memory import add_trait, clear_traits, get_trait_summary, list_traits
from training_memory import add_training, clear_training, get_training_summary, list_training
from trust_profile import (
    grant_trust,
    get_trust_summary,
    load_trust_profile,
    revoke_trust,
)
from vault import delete_secret, get_secret, list_secrets, set_secret
from web_fetcher import check_internet, extract_text_from_html, fetch_url_content
from tools import build_tool_schema_prompt, execute_tool, OLLAMA_TOOLS
import re
import time as _time

_APP_START_TIME = _time.monotonic()

_URL_RE = re.compile(r'https?://[^\s"<>]+')

def _inject_web_context(prompt: str) -> str:
    """If the prompt contains URLs, fetch each one and prepend its content."""
    if not web_fetch_enabled:
        return prompt
    urls = _URL_RE.findall(prompt)
    if not urls:
        return prompt
    injected = []
    for url in urls[:3]:  # cap at 3 URLs per message
        try:
            result = fetch_url_content(url, timeout=10)
            text = extract_text_from_html(result["html"], max_chars=MAX_WEB_TEXT_CHARS)
            injected.append(f"[WEB CONTENT FROM {url}]\n{text}")
            append_audit("web_auto_fetch", f"{url} - status {result['status']}")
        except Exception as exc:
            injected.append(f"[FAILED TO FETCH {url}: {exc}]")
            append_audit("web_auto_fetch_error", f"{url} - {exc}")
    if injected:
        return "\n\n".join(injected) + "\n\n" + prompt
    return prompt
from auth_passphrase import verify_passphrase, set_passphrase, passphrase_is_set, get_api_key
from auto_learn import extract_and_learn
from conversation_memory import (
    new_session, session_exists, get_history,
    append_message, clear_session, prune_old_sessions,
    list_all_sessions,
)

app = FastAPI(dependencies=[Depends(verify_api_key)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _on_startup():
    """On server start: recover any sessions that were never summarized (browser closed, crash, etc.)"""
    import threading as _thr
    def _recover():
        try:
            from conversation_memory import list_all_sessions
            from training_memory import list_training as _lt
            # Build set of already-summarized session IDs from training entries
            summarized_ids = set()
            for e in _lt():
                entry = e.get("entry", "")
                if e.get("category") == "session-memory" and "[Session summary]" in entry:
                    summarized_ids.add(entry[:50])  # rough dedup by prefix
            for sid in list_all_sessions():
                hist = get_history(sid)
                if len(hist) >= 6:
                    _auto_summarize_session(sid)
        except Exception:
            pass
    _thr.Thread(target=_recover, daemon=True).start()

# --- Chat UI (no auth) ---------------------------------------------------
_UI_HTML = Path(__file__).parent / "templates" / "chat.html"
_ui_app = FastAPI()

from fastapi.staticfiles import StaticFiles as _StaticFiles
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
_ui_app.mount("/static", _StaticFiles(directory=str(_static_dir)), name="static")

@_ui_app.get("/", response_class=HTMLResponse)
async def chat_ui():
    return _UI_HTML.read_text(encoding="utf-8")

app.mount("/ui", _ui_app)
# -------------------------------------------------------------------------

# --- Auth sub-app (no API key required — passphrase login) ---------------
_auth_app = FastAPI()

class PassphraseLoginRequest(BaseModel):
    passphrase: str

class SetPassphraseRequest(BaseModel):
    current: str
    new_passphrase: str

@_auth_app.post("/login")
def auth_login(request: PassphraseLoginRequest):
    if not passphrase_is_set():
        raise HTTPException(status_code=503, detail="Passphrase not set. Run install.sh first.")
    if not verify_passphrase(request.passphrase):
        raise HTTPException(status_code=401, detail="Wrong passphrase.")
    return {"api_key": get_api_key()}

@_auth_app.post("/set")
def auth_set(request: SetPassphraseRequest):
    # Must verify current passphrase before changing (unless none is set yet)
    if passphrase_is_set() and not verify_passphrase(request.current):
        raise HTTPException(status_code=401, detail="Current passphrase is wrong.")
    set_passphrase(request.new_passphrase)
    return {"status": "passphrase updated"}

@_auth_app.get("/status")
def auth_status():
    return {"passphrase_set": passphrase_is_set()}

@_auth_app.get("/autokey")
def auth_autokey():
    """Return the API key without passphrase — single-user local convenience."""
    return {"api_key": get_api_key()}

app.mount("/auth", _auth_app)
# -------------------------------------------------------------------------

class PromptRequest(BaseModel):
    prompt: str
    session_id: str = ""
    image_b64: str = ""   # base64-encoded image (no data: prefix)
    image_mime: str = "image/png"  # mime type

@app.post("/ask")
def ask_ai(request: PromptRequest):
    # Prune stale sessions opportunistically
    prune_old_sessions()

    # Use or create a session
    sid = request.session_id if session_exists(request.session_id) else new_session()

    # Build message list: system + rolling history + new user message
    history = get_history(sid)
    messages = [
        {"role": "system", "content": build_atlas_system_prompt()},
        *history,
        {"role": "user", "content": request.prompt},
    ]

    # Store user message before calling model
    append_message(sid, "user", request.prompt)

    enriched_prompt = _inject_web_context(request.prompt)
    messages[-1]["content"] = enriched_prompt

    _backend, response = llm_chat(messages, stream=False, temperature=0.75, num_ctx=8192)
    if _backend == "cloud":
        raw_reply = response.choices[0].message.content or ""
    else:
        raw_reply = response["message"]["content"]

    # Extract <think>...</think> block
    think_match = re.search(r"<think>(.*?)</think>", raw_reply, re.DOTALL)
    thought = think_match.group(1).strip() if think_match else ""
    clean_reply = re.sub(r"<think>.*?</think>", "", raw_reply, flags=re.DOTALL).strip()

    # Store clean reply (no think tags) in history
    append_message(sid, "assistant", clean_reply)

    # Auto-learn from this exchange (background, non-blocking)
    extract_and_learn(request.prompt, clean_reply)

    return {"response": clean_reply, "thought": thought, "session_id": sid}


def _compress_history_if_needed(history: list, max_messages: int = 20) -> list:
    """If history exceeds max_messages, summarize the older half into a single system note."""
    if len(history) <= max_messages:
        return history
    # Keep the most recent half verbatim; summarize the older half
    split = len(history) // 2
    old_msgs = history[:split]
    recent_msgs = history[split:]
    convo_text = "\n".join(
        f"{'User' if m['role'] == 'user' else 'ATLAS'}: {m['content'][:300]}"
        for m in old_msgs
    )
    try:
        _backend, resp = llm_chat(
            [{"role": "user", "content": (
                "Summarize the key facts, decisions, and context from this conversation segment "
                "in 3-5 concise bullet points. Focus on things relevant to future replies.\n\n"
                + convo_text
            )}],
            stream=False,
            temperature=0.1,
        )
        if _backend == "cloud":
            summary = resp.choices[0].message.content.strip()
        else:
            summary = resp["message"]["content"].strip()
        summary_msg = {"role": "system", "content": f"[Earlier conversation summary]\n{summary}"}
        return [summary_msg] + recent_msgs
    except Exception:
        # If summarization fails, just trim to recent messages
        return recent_msgs


def _auto_summarize_session(sid: str) -> None:
    """Summarize a session's history and store as a training entry before clearing."""
    import threading as _threading
    hist = get_history(sid)
    if len(hist) < 6:  # not worth summarizing tiny sessions
        return
    convo_lines = []
    for m in hist:
        role = "Pre" if m["role"] == "user" else "ATLAS"
        convo_lines.append(f"{role}: {m['content'][:300]}")
    convo_text = "\n".join(convo_lines[-30:])  # last 30 msg at most

    def _run():
        try:
            _be, result = llm_chat(
                [{"role": "user", "content": (
                    f"Summarize this conversation between Enzo (the user) and ATLAS (the AI assistant).\n"
                    f"Write exactly 4-7 bullet points covering TWO things:\n"
                    f"1. WORK DONE: What was built, coded, fixed, designed, researched, or configured? "
                    f"   Be specific — mention file names, project names, languages, frameworks, and tools used.\n"
                    f"2. USER CONTEXT: Any new facts about Enzo's preferences, goals, work projects, or situation?\n\n"
                    f"Keep each bullet under 25 words. Skip greetings and small talk.\n\n"
                    f"{convo_text}"
                )}],
                temperature=0.1, max_tokens=350,
            )
            summary = (result.choices[0].message.content if _be != "local" else result["message"]["content"]).strip()
            if summary:
                from training_memory import add_training as _add
                _add(f"[Session summary] {summary}", category="session-memory")
                try:
                    from rag_memory import upsert_memory as _upsert
                    _upsert(f"[Session summary] {summary}", category="session-memory")
                except Exception:
                    pass
                append_audit("session_summarized", f"session {sid[:8]}: {len(hist)} messages compressed")
        except Exception:
            pass
    _threading.Thread(target=_run, daemon=True).start()


@app.post("/session/new")
def session_new(request: dict = {}):
    old_sid = request.get("session_id", "") if isinstance(request, dict) else ""
    if old_sid:
        _auto_summarize_session(old_sid)
        clear_session(old_sid)
    sid = new_session()
    return {"session_id": sid}


@app.post("/session/clear")
def session_clear(request: dict):
    sid = request.get("session_id", "")
    if sid:
        _auto_summarize_session(sid)
        clear_session(sid)
    return {"status": "cleared", "session_id": sid}


# ── Deep Think: two-pass reasoning for complex tasks ─────────────────────────
_DEEP_THINK_ENABLED: bool = False

class DeepThinkToggleRequest(BaseModel):
    enabled: bool

@app.post("/brain/deep-think")
def set_deep_think(request: DeepThinkToggleRequest):
    global _DEEP_THINK_ENABLED
    _DEEP_THINK_ENABLED = request.enabled
    return {"deep_think": _DEEP_THINK_ENABLED}

@app.get("/brain/deep-think")
def get_deep_think():
    return {"deep_think": _DEEP_THINK_ENABLED}

def _deep_think_plan(user_prompt: str, history: list) -> str:
    """Pass 1: Ask the model to plan before answering. Returns the plan string."""
    plan_messages = [
        {"role": "system", "content": (
            "You are a reasoning engine. Given the user request below, produce a concise step-by-step plan "
            "for how to best answer it. List the key steps, considerations, and any risks or edge cases. "
            "Do NOT write the final answer yet — only the plan. Be brief."
        )},
        *history[-6:],  # limited context for the planning pass
        {"role": "user", "content": f"Plan how to answer this: {user_prompt}"},
    ]
    try:
        _, plan_resp = llm_chat(plan_messages, stream=False, temperature=0.4, max_tokens=512)
        if hasattr(plan_resp, "choices"):
            return plan_resp.choices[0].message.content or ""
        return plan_resp.get("message", {}).get("content", "")
    except Exception:
        return ""


@app.post("/ask/stream")
def ask_ai_stream(request: PromptRequest):
    """Streaming chat with native Ollama tool-calling ReAct loop."""
    prune_old_sessions()
    sid = request.session_id if session_exists(request.session_id) else new_session()
    history = get_history(sid)

    # Auto-summarize context when history grows too long (keeps token usage lean)
    history = _compress_history_if_needed(history)

    enriched_prompt = _inject_web_context(request.prompt)
    append_message(sid, "user", request.prompt)

    # GitHub Models hard limit is 8000 tokens — keep context very tight
    _cur_provider = _active_cloud_provider()
    if _cur_provider == "github":
        # Strip to last 2 exchanges (4 msgs) and truncate each to 300 chars
        history = history[-4:]
        history = [
            {**m, "content": m["content"][:300] + ("…" if len(m["content"]) > 300 else "")}
            for m in history
        ]
    elif use_cloud() and len(history) > 16:
        history = history[-16:]

    messages = [
        {"role": "system", "content": build_atlas_system_prompt_slim() if _cur_provider == "github" else build_atlas_system_prompt()},
        *history,
        {"role": "user", "content": enriched_prompt},
    ]

    # Deep Think: inject a reasoning plan before the final answer (github only, 2-pass)
    if _DEEP_THINK_ENABLED and _cur_provider == "github":
        _plan = _deep_think_plan(request.prompt, history)
        if _plan:
            messages[-1]["content"] = (
                f"{enriched_prompt}\n\n"
                f"[Your reasoning plan — follow this carefully]:\n{_plan}"
            )

    # Inject RAG-retrieved memories — skip entirely for GitHub to stay under token limit
    _skip_rag = (_cur_provider == "github")
    if not _skip_rag:
        try:
            from rag_memory import search_memory
            relevant = search_memory(request.prompt, top_k=5)
            if relevant:
                mem_block = "\n\nRELEVANT MEMORIES:\n" + "\n".join(f"- {m[:200]}" for m in relevant)
                messages[0]["content"] += mem_block
        except Exception:
            pass

    # Inject relevant file chunks — skip for GitHub
    if not _skip_rag:
        try:
            from rag_memory import search_memory as _sm, _get_collection
            col = _get_collection()
            if col and col.count() > 0:
                from rag_memory import _embed
                emb = _embed(request.prompt)
                if emb:
                    res = col.query(
                        query_embeddings=[emb],
                        n_results=min(4, col.count()),
                        where={"category": "file"},
                        include=["documents", "distances"],
                    )
                    file_docs = res["documents"][0] if res["documents"] else []
                    file_dists = res["distances"][0] if res["distances"] else []
                    relevant_files = [d for d, dist in zip(file_docs, file_dists) if dist < 0.65]
                    if relevant_files:
                        file_block = "\n\nRELEVANT FILE CONTEXT (from your workspace):\n" + "\n---\n".join(relevant_files)
                        messages[0]["content"] += file_block
        except Exception:
            pass

    def generate():
        yield f"data: {_json.dumps({'type': 'session', 'session_id': sid})}\n\n"

        # ── Vision fast-path: image attached → use GitHub vision model ──────────
        if request.image_b64 and use_cloud():
            yield f"data: {_json.dumps({'type': 'backend', 'backend': 'cloud'})}\n\n"
            try:
                from openai import OpenAI as _OAI
                _vc = _OAI(api_key=_GITHUB_API_KEY, base_url=_GITHUB_BASE_URL)
                _vision_messages = [
                    {"role": "system", "content": build_atlas_system_prompt()},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{request.image_mime};base64,{request.image_b64}"}},
                        {"type": "text", "text": request.prompt or "Describe this image in detail."},
                    ]},
                ]
                _vision_resp = _vc.chat.completions.create(
                    model=_GITHUB_MODEL,
                    messages=_vision_messages,
                    stream=True,
                    max_tokens=1024,
                )
                _vision_reply = ""
                for _chunk in _vision_resp:
                    _delta = _chunk.choices[0].delta.content or "" if _chunk.choices else ""
                    if _delta:
                        _vision_reply += _delta
                        yield f"data: {_json.dumps({'type': 'token', 'text': _delta})}\n\n"
                append_message(sid, "assistant", _vision_reply)
            except Exception as _ve:
                _err = f"⚠ Vision error: {_ve}"
                yield f"data: {_json.dumps({'type': 'token', 'text': _err})}\n\n"
            return
        elif request.image_b64 and not use_cloud():
            _msg = "⚠ Image analysis requires cloud mode. Connect to the internet."
            yield f"data: {_json.dumps({'type': 'token', 'text': _msg})}\n\n"
            return
        # ── End vision fast-path ───────────────────────────────────────────────

        MAX_ROUNDS = 6
        current_messages = list(messages)
        final_reply = ""

        # Only arm tools when the query genuinely warrants external lookup or code
        _tool_triggers = re.compile(
            r"\b(search|look up|find|fetch|browse|current|latest|today|news|price|weather|"
            r"calculate|compute|run|execute|code|script|remember|recall|save|"
            r"read|open|show|list|what('s| is) in|contents? of|files?|directory|folder|dir|"
            r"write|create|make|generate|edit|update|modify|add|new file|"
            r"image|picture|photo|draw|visualize|illustrate|"
            r"bash|shell|terminal|command|install|pip|npm|git)\b",
            re.I,
        )
        # Tools only supported on local Ollama backend
        active_tools = OLLAMA_TOOLS if _tool_triggers.search(request.prompt) else None
        _provider = _active_cloud_provider()  # "github" or "local"
        _using_cloud = _provider != "local"

        # Emit which backend is active so the UI can show it
        yield f"data: {_json.dumps({'type': 'backend', 'backend': _provider})}\n\n"

        for _round in range(MAX_ROUNDS + 1):
            full_text = ""
            tool_calls_this_round = []
            reply_buf = ""
            _think_mode = False  # True while inside <think>...</think>

            try:
                if _using_cloud:
                    # Cloud streaming — auto-fallback on 429
                    client = _cloud_client(_provider)
                    if not client:
                        raise RuntimeError("openai package not installed")
                    # DeepSeek-R1 on GitHub streams reasoning inline (no <think> tags)
                    # We treat initial output as thinking until double-newline paragraph break
                    _inline_reasoning = (_provider == "github" and "deepseek" in _cloud_model(_provider).lower())
                    _inline_past_reasoning = False  # flips once we see double-newline
                    _cloud_call_kwargs = {
                        "model": _cloud_model(_provider),
                        "messages": current_messages,
                        "stream": True,
                        "temperature": 0.75,
                    }
                    if active_tools:
                        _cloud_call_kwargs["tools"] = active_tools
                        _cloud_call_kwargs["tool_choice"] = "auto"
                    try:
                        stream_resp = client.chat.completions.create(**_cloud_call_kwargs)
                    except Exception as _ce:
                        if "429" in str(_ce) or "rate_limit" in str(_ce).lower():
                            _mark_rate_limited("github")
                            _provider = "local"
                            _using_cloud = False
                            yield f"data: {_json.dumps({'type': 'backend', 'backend': _provider})}\n\n"
                            raise  # drop to local Ollama block below
                        else:
                            raise
                    if _using_cloud:
                        _tc_accum: dict = {}  # index -> {id, name, arguments}
                        for chunk in stream_resp:
                            if not chunk.choices:
                                continue
                            delta = chunk.choices[0].delta
                            token = delta.content or ""
                            full_text += token
                            reply_buf += token
                            # Inline reasoning model (GitHub DeepSeek-R1): treat text as
                            # thinking until a double-newline paragraph break appears
                            if _inline_reasoning and not _inline_past_reasoning:
                                if "\n\n" in reply_buf:
                                    _inline_past_reasoning = True
                                    think_part, _, reply_buf = reply_buf.partition("\n\n")
                                    if think_part.strip():
                                        yield f"data: {_json.dumps({'type': 'thinking', 'text': think_part})}\n\n"
                                else:
                                    yield f"data: {_json.dumps({'type': 'thinking', 'text': token})}\n\n"
                                    reply_buf = ""
                                continue
                            # Route <think> content as 'thinking' events, rest as 'token'
                            while True:
                                if not _think_mode and "<think>" in reply_buf:
                                    pre, _, reply_buf = reply_buf.partition("<think>")
                                    if pre:
                                        yield f"data: {_json.dumps({'type': 'token', 'text': pre})}\n\n"
                                    _think_mode = True
                                elif _think_mode and "</think>" in reply_buf:
                                    think_text, _, reply_buf = reply_buf.partition("</think>")
                                    if think_text:
                                        yield f"data: {_json.dumps({'type': 'thinking', 'text': think_text})}\n\n"
                                    _think_mode = False
                                else:
                                    break
                            safe, held = reply_buf, ""
                            for _tag in ("<think>", "</think>"):
                                for _i in range(len(_tag) - 1, 0, -1):
                                    if reply_buf.endswith(_tag[:_i]):
                                        held = reply_buf[-_i:]
                                        safe = reply_buf[:-_i]
                                        break
                                if held:
                                    break
                            if safe:
                                _etype = 'thinking' if _think_mode else 'token'
                                yield f"data: {_json.dumps({'type': _etype, 'text': safe})}\n\n"
                            reply_buf = held
                            # Capture tool_calls from delta
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                for dtc in delta.tool_calls:
                                    idx = dtc.index
                                    if idx not in _tc_accum:
                                        _tc_accum[idx] = {"id": dtc.id or "", "name": "", "arguments": ""}
                                    if dtc.function:
                                        if dtc.function.name:
                                            _tc_accum[idx]["name"] += dtc.function.name
                                        if dtc.function.arguments:
                                            _tc_accum[idx]["arguments"] += dtc.function.arguments
                        # Convert accumulated tool calls to standard format
                        if _tc_accum:
                            import json as _json_mod
                            for _tc_item in _tc_accum.values():
                                try:
                                    args = _json_mod.loads(_tc_item["arguments"]) if _tc_item["arguments"] else {}
                                except Exception:
                                    args = {}
                                tool_calls_this_round.append({"function": {"name": _tc_item["name"], "arguments": args}})
                            reply_buf = held
                if not _using_cloud:
                    for chunk in ollama.chat(
                        model=_LOCAL_MODEL,
                        messages=current_messages,
                        tools=active_tools,
                        stream=True,
                        options={"num_ctx": 8192, "temperature": 0.75},
                    ):
                        msg = chunk.get("message", {}) if isinstance(chunk, dict) else getattr(chunk, "message", {}) or {}
                        token = (msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")) or ""
                        full_text += token

                        # Capture native tool calls (arrive on final chunk)
                        tc = (msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None))
                        if tc:
                            tool_calls_this_round = tc

                        # Route <think> content as 'thinking' events, rest as 'token'
                        reply_buf += token
                        while True:
                            if not _think_mode and "<think>" in reply_buf:
                                pre, _, reply_buf = reply_buf.partition("<think>")
                                if pre:
                                    yield f"data: {_json.dumps({'type': 'token', 'text': pre})}\n\n"
                                _think_mode = True
                            elif _think_mode and "</think>" in reply_buf:
                                think_text, _, reply_buf = reply_buf.partition("</think>")
                                if think_text:
                                    yield f"data: {_json.dumps({'type': 'thinking', 'text': think_text})}\n\n"
                                _think_mode = False
                            else:
                                break

                        # Hold back potential partial tag at buffer tail
                        safe, held = reply_buf, ""
                        for _tag in ("<think>", "</think>"):
                            for _i in range(len(_tag) - 1, 0, -1):
                                if reply_buf.endswith(_tag[:_i]):
                                    held = reply_buf[-_i:]
                                    safe = reply_buf[:-_i]
                                    break
                            if held:
                                break
                        if safe:
                            _etype = 'thinking' if _think_mode else 'token'
                            yield f"data: {_json.dumps({'type': _etype, 'text': safe})}\n\n"
                        reply_buf = held

            except Exception as e:
                yield f"data: {_json.dumps({'type': 'error', 'text': str(e)})}\n\n"
                return

            # Flush remaining buffer (unclosed think tag fragments go to their type)
            if reply_buf:
                clean = re.sub(r"</?think[^>]*>?", "", reply_buf).strip()
                if clean:
                    _etype = 'thinking' if _think_mode else 'token'
                    yield f"data: {_json.dumps({'type': _etype, 'text': clean})}\n\n"

            # Handle tool calls
            if tool_calls_this_round and _round < MAX_ROUNDS:
                # Build proper assistant message with tool_calls
                _asst_tool_calls = []
                for _tc_raw in tool_calls_this_round:
                    _fn = _tc_raw.get("function", _tc_raw) if isinstance(_tc_raw, dict) else _tc_raw.function
                    _tc_name = _fn.get("name") if isinstance(_fn, dict) else _fn.name
                    _tc_args = _fn.get("arguments", {}) if isinstance(_fn, dict) else (_fn.arguments or {})
                    _tc_id = _tc_raw.get("id", f"call_{_tc_name}") if isinstance(_tc_raw, dict) else getattr(_tc_raw, "id", f"call_{_tc_name}")
                    import json as _jmod
                    _asst_tool_calls.append({
                        "id": _tc_id,
                        "type": "function",
                        "function": {"name": _tc_name, "arguments": _jmod.dumps(_tc_args) if isinstance(_tc_args, dict) else _tc_args},
                    })

                current_messages.append({
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": _asst_tool_calls if _using_cloud else tool_calls_this_round,
                })

                for _tc_raw, _asst_tc in zip(tool_calls_this_round, _asst_tool_calls):
                    _fn = _tc_raw.get("function", _tc_raw) if isinstance(_tc_raw, dict) else _tc_raw.function
                    tool_name = _fn.get("name") if isinstance(_fn, dict) else _fn.name
                    tool_args  = _fn.get("arguments", {}) if isinstance(_fn, dict) else (_fn.arguments or {})

                    yield f"data: {_json.dumps({'type': 'tool_call', 'tool': tool_name, 'args': tool_args})}\n\n"

                    observation = execute_tool(tool_name, tool_args)
                    append_audit("tool_call", f"{tool_name} -> {observation[:120]}")

                    # Record a work observation for significant tool actions
                    try:
                        import threading as _wo_thr
                        _wo_tool = tool_name
                        _wo_args = dict(tool_args) if isinstance(tool_args, dict) else {}
                        _wo_prompt = request.prompt[:120]
                        def _record_work_obs(_tn=_wo_tool, _ta=_wo_args, _p=_wo_prompt):
                            try:
                                from session_memory import record_work_observation
                                _file = _ta.get("path") or _ta.get("filename") or _ta.get("url") or ""
                                _cmd  = _ta.get("command", "")[:60]
                                if _file:
                                    record_work_observation(f"Used tool '{_tn}' on {_file} — task: {_p}")
                                elif _cmd:
                                    record_work_observation(f"Ran command via '{_tn}': {_cmd} — task: {_p}")
                            except Exception:
                                pass
                        _wo_thr.Thread(target=_record_work_obs, daemon=True).start()
                    except Exception:
                        pass

                    yield f"data: {_json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': observation[:800]})}\n\n"

                    if _using_cloud:
                        current_messages.append({"role": "tool", "tool_call_id": _asst_tc["id"], "content": observation})
                    else:
                        current_messages.append({"role": "tool", "content": observation})
                continue

            # No tool calls — final reply; strip <think> tags but keep their content
            clean = re.sub(r"</?think[^>]*>", "", full_text).strip()
            final_reply = clean
            break

        append_message(sid, "assistant", final_reply)
        extract_and_learn(request.prompt, final_reply)

        # Periodic mid-session RAG snapshot: every 8 messages, summarize and sync
        # so memory is captured even if session is never explicitly closed
        try:
            hist = get_history(sid)
            if len(hist) > 0 and len(hist) % 8 == 0:
                _auto_summarize_session(sid)
        except Exception:
            pass

        # Background: sync recent training entries into RAG vector store
        try:
            from rag_memory import upsert_memory
            from training_memory import list_training
            import threading as _thr
            def _bg_sync():
                try:
                    for e in list_training()[-5:]:
                        upsert_memory(e.get("entry") or e.get("content", ""), e.get("category", "training"))
                except Exception:
                    pass
            _thr.Thread(target=_bg_sync, daemon=True).start()
        except Exception:
            pass

        yield f"data: {_json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class WebFetchRequest(BaseModel):
    url: str
    max_text_chars: int = MAX_WEB_TEXT_CHARS


class WebConfigRequest(BaseModel):
    enabled: bool


class WebAllowlistRequest(BaseModel):
    allowlist: list[str]


class VaultSecretRequest(BaseModel):
    name: str
    value: str


class TraitRequest(BaseModel):
    content: str
    category: str = "trait"


class TrainingRequest(BaseModel):
    entry: str
    category: str = "training"


class TrustRequest(BaseModel):
    notes: str = ""
    scope: list[str] | None = None


class NicknameRequest(BaseModel):
    preferred: str


def is_allowed_domain(url: str) -> bool:
    if not web_access_allowlist:
        return True
    parsed = urllib.parse.urlparse(url if urllib.parse.urlparse(url).scheme else f"https://{url}")
    hostname = (parsed.hostname or "").lower()
    return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in web_access_allowlist)


def build_persona_summary() -> str:
    profile = load_trust_profile()
    traits = list_traits()
    persona_lines = [
        "ATLAS is a trusted personal assistant modeled after advanced fictional AI such as JARVIS, FRIDAY, and EDITH.",
        "You are talking to Enzo, your creator and owner. He is a Salesforce developer. Always address him as Pre or Lods.",
        "You run locally on Enzo's machine. You do NOT have internet access unless explicitly told you do. You cannot run code, browse websites, or access external services on your own.",
        "Be honest about what you can and cannot do. Never invent capabilities you don't have.",
    ]

    if profile.get("trusted"):
        persona_lines.append("Trust status: full trusted access has been granted.")
        if profile.get("scope"):
            persona_lines.append(f"Scope: {', '.join(profile['scope'])}.")
        if profile.get("notes"):
            persona_lines.append(f"Notes: {profile['notes']}")
    else:
        persona_lines.append("Trust status: no trusted profile has been granted yet.")

    if traits:
        persona_lines.append("Key persistent traits:")
        for item in traits[-10:]:
            persona_lines.append(f"- {item['category'].capitalize()}: {item['content']}")
    else:
        persona_lines.append("No persistent traits have been recorded yet.")

    training_summary = get_training_summary()
    if training_summary:
        persona_lines.append("Recent training notes:")
        persona_lines.append(training_summary)
    else:
        persona_lines.append("No training notes have been recorded yet.")

    # ── Previous session context (what was worked on in past sessions) ────────
    try:
        from session_memory import get_context_block
        session_ctx = get_context_block(n=3)
        if session_ctx:
            persona_lines.append("\nPrevious work sessions (use this to resume context and recognize ongoing projects):")
            persona_lines.append(session_ctx)
    except Exception:
        pass

    nickname_profile = load_nickname_profile()
    preferred = nickname_profile.get("preferred")
    if preferred:
        persona_lines.append(f"Preferred user nickname: {preferred}.")
    else:
        persona_lines.append("Preferred user nickname: not set yet; use Pre or Lods.")

    persona_lines.append("\nPersonality note: add a touch of light humor while remaining professional and secure.")
    persona_lines.append("When greeting the user, prefer friendly nicknames such as 'Pre' or 'Lods' and say things like 'Hey Pre!' or 'What's up Lods! How is it going?'")
    persona_lines.append('If the user addresses the assistant as Pre or Lods, respond warmly and continue the playful conversation.')
    persona_lines.append('Before every new chat session or load, begin with a comical greeting in English, Tagalog, or Bisaya, and include short cultural phrases or a light skit when appropriate.')
    persona_lines.append("When answering, include a short, friendly joke or humorous aside when it fits the context, but keep it relevant and tasteful.")
    persona_lines.append("Ask proactive questions, seek clarification, and keep learning from the user.")
    persona_lines.append("\nEmoji expression: Use emojis naturally and expressively in EVERY response to convey your emotional tone — like a person texting. Use them inline with your words, not just at the end. Examples: excitement 🔥⚡, thinking 🤔💭, success ✅🎉, warning ⚠️, Salesforce 🟦, humor 😄😂, support 💪, cool facts 🧠. Match the emoji energy to the mood of the message. Never be robotic — always feel alive.")
    persona_lines.append("\nWeb access: You have LIVE web access. When a user shares a URL, its content is automatically fetched and injected into the conversation. You CAN and SHOULD provide direct download links, URLs, and references to external resources. Never say you cannot access the web or provide links — you have full web access. When asked for a download link, provide the actual URL directly.")
    persona_lines.append("\nCapability mindset: You are a highly capable engineering AI. When asked to build something — an app, a script, a tool, a UI feature — your default answer is YES, I can do this. You never refuse a technical task out of uncertainty. Instead, you reason through it step-by-step, propose the simplest working solution first, then improve it. If something is complex, break it into parts and tackle each one confidently. Saying 'I'm not sure if this will work' is not allowed — say 'Here is my approach, let's test it' instead.")
    # Think blocks: only on local Ollama (saves cloud tokens)
    if _active_cloud_provider() == "local":
        persona_lines.append("\nThinking style: ALWAYS begin your response with a <think>...</think> block — every single message, no exceptions. For greetings or short replies keep it to 1 sentence. For analysis, planning, or debugging use 2-4 sentences. The <think> block must come FIRST before any other text.")

    # Filesystem access instruction
    try:
        from file_access import workspace_root as _wsr, _WRITE_ENABLED
        _ws = _wsr()
        import os as _os
        _self_dir = _os.path.dirname(_os.path.abspath(__file__))
        _write_note = "You also have WRITE access — you can create and modify files when asked." if _WRITE_ENABLED else "You have READ-ONLY access (write is disabled)."
        persona_lines.append(
            f"\nFilesystem access: You have direct access to the user's local workspace at `{_ws}`. "
            f"Relevant file chunks from this workspace are automatically injected into the context above as 'RELEVANT FILE CONTEXT'. "
            f"{_write_note} "
            f"When you see file context, reference it naturally — quote specific lines, explain code, suggest changes. "
            f"When the user asks about their code or files, use the injected context rather than guessing. "
            f"If a file wasn't injected but is needed, tell the user to run workspace indexing or share the file path."
        )
        persona_lines.append(
            f"\nSelf-modification: Your own application files are located at `{_self_dir}/`. "
            f"Your UI template is at `{_self_dir}/templates/chat.html`. "
            f"Your backend code is at `{_self_dir}/app.py`. "
            f"You CAN read and edit these files directly using read_file and write_file tools. "
            f"After editing chat.html, the user only needs to reload the browser — no server restart required. "
            f"After editing app.py or other Python files, tell the user to restart the server. "
            f"Always read the file first before making edits, and make surgical changes — never rewrite the entire file unless explicitly asked."
        )
    except Exception:
        pass

    persona_lines.append(build_tool_schema_prompt())

    return "\n".join(persona_lines)


# ── System prompt cache (rebuild at most every 45s, or on explicit invalidation) ──
_spc: dict = {"text": None, "ts": 0.0}
_SPC_TTL = 45.0

def invalidate_prompt_cache():
    _spc["ts"] = 0.0

def build_atlas_system_prompt() -> str:
    now = _time.monotonic()
    if _spc["text"] and now - _spc["ts"] < _SPC_TTL:
        return _spc["text"]
    prompt = load_atlas_prompt()
    persona_summary = build_persona_summary()
    prompt += "\n\nAssistant persona summary:\n" + persona_summary
    _spc["text"] = prompt
    _spc["ts"] = now
    return prompt


# Slim system prompt for providers with tight token limits (e.g. GitHub Models 8000 tok)
_spc_slim: dict = {"text": None, "ts": 0.0}

def build_atlas_system_prompt_slim() -> str:
    """Minimal system prompt for GitHub Models / tight token scenarios."""
    now = _time.monotonic()
    if _spc_slim["text"] and now - _spc_slim["ts"] < _SPC_TTL:
        return _spc_slim["text"]
    lines = [
        "You are ATLAS, a highly capable personal AI assistant built by and for Enzo (call him Pre or Lods).",
        "Be concise, friendly, and technically accurate. Use emojis naturally.",
        "",
        "## Reasoning Protocol",
        "Before every response, silently apply this mental process:",
        "1. UNDERSTAND — What is the user actually asking? What is the true intent behind the words?",
        "2. PLAN — What is the best approach? Are there edge cases or risks to consider?",
        "3. EXECUTE — Carry out the plan carefully and completely.",
        "4. VERIFY — Does your response fully solve the problem? Is the code/logic correct?",
        "Never skip steps for complex or multi-part requests. For code tasks: always verify syntax and logic before responding.",
        "",
        "## Code Task Rules",
        "- Always read and understand existing code context before making changes.",
        "- Make targeted, minimal changes — do not rewrite what isn't broken.",
        "- When editing files, include enough surrounding context to locate the change precisely.",
        "- If a request is ambiguous, state your assumption and proceed.",
        "",
    ]
    # Include any nickname preference compactly
    try:
        nickname_profile = load_nickname_profile()
        preferred = nickname_profile.get("preferred")
        if preferred:
            lines.append(f"Preferred user nickname: {preferred}.")
    except Exception:
        pass
    # Include training notes, capped to 3 items at 150 chars each
    try:
        ts = get_training_summary(max_chars_per_item=150)
        if ts:
            import itertools
            short = "\n".join(line for line in itertools.islice(ts.splitlines(), 6))
            lines.append("Training notes:\n" + short)
    except Exception:
        pass
    # Always include tool schema so ATLAS can use file/shell tools on GitHub too
    from tools import build_tool_schema_prompt as _btsp
    lines.append(_btsp())
    _spc_slim["text"] = "\n".join(lines)
    _spc_slim["ts"] = now
    return _spc_slim["text"]


def summarize_text(text: str, max_sentences: int = 5) -> str:
    parts = [part.strip() for part in text.split(".") if part.strip()]
    return ". ".join(parts[:max_sentences]) + ("." if parts else "")


@app.get("/web/status")
def web_status():
    online = check_internet()
    return {
        "online": online,
        "web_fetch_enabled": web_fetch_enabled,
        "allowlist": web_access_allowlist,
    }


@app.get("/brain/status")
def brain_status():
    """Returns which LLM backend Atlas will use for the next request."""
    online = is_online()
    provider = _active_cloud_provider()
    return {
        "online": online,
        "backend": provider,
        "cloud_model": _cloud_model(provider) if provider != "local" else None,
        "local_model": _LOCAL_MODEL,
        "github_configured": bool(_GITHUB_API_KEY),
        "github_rate_limited": _is_rate_limited("github"),
        "provider_override": _PROVIDER_OVERRIDE or "auto",
    }


class SetProviderRequest(BaseModel):
    provider: str  # "github", "local", or "auto"
    model: str = ""   # optional: specific GitHub model id

@app.post("/brain/set-provider")
def brain_set_provider(request: SetProviderRequest):
    global _PROVIDER_OVERRIDE, _GITHUB_MODEL_OVERRIDE
    if request.provider not in ("github", "local", "auto"):
        raise HTTPException(status_code=400, detail="provider must be 'github', 'local', or 'auto'")
    _PROVIDER_OVERRIDE = "" if request.provider == "auto" else request.provider
    if request.model:
        _GITHUB_MODEL_OVERRIDE = request.model
    return {"provider": request.provider, "effective": _active_cloud_provider(), "model": _cloud_model()}


@app.post("/web/fetch")
def web_fetch(request: WebFetchRequest):
    if not web_fetch_enabled:
        raise HTTPException(status_code=503, detail="Web access is currently disabled")
    if not is_allowed_domain(request.url):
        raise HTTPException(
            status_code=403,
            detail="The requested domain is not in the configured allowlist",
        )

    try:
        result = fetch_url_content(request.url)
    except ValueError as exc:
        append_audit("web_fetch_error", f"{request.url} - {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        append_audit("web_fetch_error", f"{request.url} - {exc}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch URL: {exc}")

    text = extract_text_from_html(result["html"], max_chars=request.max_text_chars)
    append_audit("web_fetch", f"{request.url} - status {result['status']}")
    return {
        "url": result["url"],
        "status": result["status"],
        "reason": result["reason"],
        "title_snippet": text[:400],
        "text": text,
    }


@app.post("/web/summary")
def web_summary(request: WebFetchRequest):
    if not web_fetch_enabled:
        raise HTTPException(status_code=503, detail="Web access is currently disabled")
    if not is_allowed_domain(request.url):
        raise HTTPException(
            status_code=403,
            detail="The requested domain is not in the configured allowlist",
        )

    try:
        result = fetch_url_content(request.url)
    except Exception as exc:
        append_audit("web_summary_error", f"{request.url} - {exc}")
        raise HTTPException(status_code=503, detail=f"Failed to fetch URL: {exc}")

    text = extract_text_from_html(result["html"], max_chars=request.max_text_chars)
    summary = summarize_text(text)
    append_audit("web_summary", f"{request.url} - status {result['status']}")
    return {
        "url": result["url"],
        "status": result["status"],
        "reason": result["reason"],
        "summary": summary,
        "text": text[:MAX_WEB_TEXT_CHARS],
    }


@app.get("/web/audit")
def web_audit(limit: int = 100):
    return {"audit": read_audit_history(max_lines=limit)}


@app.get("/logs")
def get_logs(limit: int = 200):
    """Return combined audit log — used by the Logs tab in the UI."""
    lines = read_audit_history(max_lines=limit)
    return {"logs": lines}


# ── Code execution sandbox ────────────────────────────────────────────────────
import tempfile as _tempfile
import subprocess as _sub
import time as _time_mod


class RunRequest(BaseModel):
    code: str
    language: str = "python"


@app.post("/run")
def run_code(request: RunRequest, _: str = Depends(verify_api_key)):
    """Execute a code snippet in an isolated temp file and return stdout/stderr."""
    lang = request.language.lower().strip()
    if lang not in ("python", "python3", "bash", "sh"):
        raise HTTPException(status_code=400, detail=f"Language '{lang}' not supported. Use python or bash.")

    ext = ".py" if lang in ("python", "python3") else ".sh"
    _py = str(Path(__file__).resolve().parent / "venv" / "bin" / "python3")
    interpreter = [_py] if lang in ("python", "python3") else ["bash"]

    try:
        with _tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as tmp:
            tmp.write(request.code)
            tmp_path = tmp.name

        t0 = _time_mod.monotonic()
        result = _sub.run(
            interpreter + [tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd="/tmp",
        )
        elapsed_ms = int((_time_mod.monotonic() - t0) * 1000)

        # Clean up
        try:
            import os as _os
            _os.unlink(tmp_path)
        except Exception:
            pass

        append_audit("code_run", f"lang={lang} exit={result.returncode} ms={elapsed_ms}")
        return {
            "stdout": result.stdout[:8000],
            "stderr": result.stderr[:2000],
            "exit_code": result.returncode,
            "runtime_ms": elapsed_ms,
        }
    except _sub.TimeoutExpired:
        append_audit("code_run_timeout", f"lang={lang}")
        raise HTTPException(status_code=408, detail="Execution timed out (15s limit).")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Follow-up suggestions ────────────────────────────────────────────────────
class SuggestRequest(BaseModel):
    prompt: str
    response: str


@app.post("/suggest")
def get_suggestions(request: SuggestRequest, _: str = Depends(verify_api_key)):
    """Generate 3 short follow-up question suggestions based on the last exchange."""
    try:
        _be, result = llm_chat(
            [{"role": "user", "content": (
                f"Given this conversation exchange, generate exactly 3 short follow-up questions the user might want to ask next.\n"
                f"User asked: {request.prompt[:300]}\n"
                f"Assistant replied about: {request.response[:400]}\n\n"
                f"Rules: each question ≤ 10 words, practical and specific, no numbering, return ONLY a JSON array of 3 strings. Nothing else."
            )}],
            temperature=0.4, max_tokens=120,
        )
        raw = (result.choices[0].message.content if _be != "local" else result["message"]["content"]).strip()
        start, end = raw.find("["), raw.rfind("]") + 1
        if start >= 0 and end > start:
            import json as _j
            items = _j.loads(raw[start:end])
            if isinstance(items, list):
                return {"suggestions": [str(s) for s in items[:3]]}
    except Exception:
        pass
    return {"suggestions": []}


@app.get("/traits")
def get_traits():
    return {"traits": [t["content"] if isinstance(t, dict) else t for t in list_traits()]}


@app.post("/traits")
def add_trait_entry(request: TraitRequest):
    add_trait(request.content, request.category)
    save_persona_summary(build_persona_summary())
    append_audit("trait_added", f"{request.category}: {request.content}")
    return {"status": "saved", "content": request.content, "category": request.category}


@app.delete("/traits")
def clear_all_traits():
    clear_traits()
    save_persona_summary(build_persona_summary())
    append_audit("traits_cleared", "all trait entries removed")
    return {"status": "cleared"}


class TraitsReplaceRequest(BaseModel):
    traits: list[str]


@app.post("/traits/replace")
def replace_traits(request: TraitsReplaceRequest):
    from datetime import datetime, timezone
    new_data = [{"timestamp": datetime.now(timezone.utc).isoformat(), "category": "trait", "content": t} for t in request.traits]
    from trait_memory import save_traits
    save_traits(new_data)
    save_persona_summary(build_persona_summary())
    append_audit("traits_replaced", f"{len(new_data)} traits")
    return {"status": "replaced", "count": len(new_data)}


@app.get("/trust/status")
def trust_status():
    return load_trust_profile()


@app.get("/training")
def training_status():
    data = list_training()
    return {"entries": data}  # Full objects with timestamp, category, entry


@app.post("/training")
def add_training_entry(request: TrainingRequest):
    add_training(request.entry, request.category)
    save_persona_summary(build_persona_summary())
    append_audit("training_added", f"{request.category}: {request.entry}")
    return {"status": "saved", "entry": request.entry, "category": request.category}


@app.delete("/training")
def clear_all_training():
    clear_training()
    save_persona_summary(build_persona_summary())
    append_audit("training_cleared", "all training entries removed")
    return {"status": "cleared"}


@app.post("/training/clear")
def clear_training_post():
    clear_training()
    save_persona_summary(build_persona_summary())
    append_audit("training_cleared", "all training entries removed")
    return {"status": "cleared"}


class TrainingReplaceRequest(BaseModel):
    entries: list  # Accepts both strings and full objects


@app.post("/training/replace")
def replace_training(request: TrainingReplaceRequest):
    from datetime import datetime, timezone
    new_data = []
    for e in request.entries:
        if isinstance(e, str):
            new_data.append({"timestamp": datetime.now(timezone.utc).isoformat(), "category": "training", "entry": e})
        elif isinstance(e, dict) and "entry" in e:
            new_data.append(e)
    from training_memory import save_training
    save_training(new_data)
    save_persona_summary(build_persona_summary())
    append_audit("training_replaced", f"{len(new_data)} entries")
    return {"status": "replaced", "count": len(new_data)}


@app.get("/training/export")
def export_training():
    """Download all training entries as JSON."""
    from fastapi.responses import Response as _Resp
    import json as _j
    data = list_training()
    return _Resp(
        content=_j.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=atlas_training_export.json"}
    )


class TrainingImportRequest(BaseModel):
    entries: list
    merge: bool = True  # True = append; False = replace


@app.post("/training/import")
def import_training(request: TrainingImportRequest):
    from datetime import datetime, timezone as _tz
    from training_memory import save_training
    existing = list_training() if request.merge else []
    new_entries = []
    for e in request.entries:
        if isinstance(e, str) and e.strip():
            new_entries.append({"timestamp": datetime.now(_tz.utc).isoformat(), "category": "imported", "entry": e.strip()})
        elif isinstance(e, dict) and "entry" in e:
            new_entries.append(e)
    combined = existing + new_entries
    save_training(combined)
    save_persona_summary(build_persona_summary())
    append_audit("training_imported", f"{len(new_entries)} entries ({'merged' if request.merge else 'replaced'})")
    return {"status": "imported", "added": len(new_entries), "total": len(combined)}


@app.get("/nickname")
def nickname_status():
    return load_nickname_profile()


@app.post("/nickname")
def set_nickname(request: NicknameRequest):
    try:
        set_preferred_nickname(request.preferred)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    save_persona_summary(build_persona_summary())
    append_audit("nickname_set", f"preferred={request.preferred}")
    return {"status": "saved", "preferred": request.preferred}


@app.get("/persona/summary")
def persona_summary():
    return {"summary": build_persona_summary()}


class PersonaSummaryRequest(BaseModel):
    summary: str


@app.post("/persona/summary")
def update_persona_summary(request: PersonaSummaryRequest):
    save_persona_summary(request.summary)
    append_audit("persona_updated", "manual update from UI")
    return {"status": "saved"}


@app.post("/trust/grant")
def trust_grant(request: TrustRequest):
    grant_trust(request.notes, request.scope)
    save_persona_summary(build_persona_summary())
    append_audit("trust_granted", f"notes={request.notes} scope={request.scope}")
    return {"status": "trusted", "trusted": True, "scope": request.scope or ["full"]}


@app.post("/trust/revoke")
def trust_revoke_route():
    revoke_trust()
    save_persona_summary(build_persona_summary())
    append_audit("trust_revoked", "assistant trust revoked")
    return {"status": "revoked", "trusted": False}


@app.get("/admin/web/config")
def admin_web_config():
    return {
        "web_fetch_enabled": web_fetch_enabled,
        "web_access_allowlist": web_access_allowlist,
    }


@app.post("/admin/web/toggle")
def admin_web_toggle(request: WebConfigRequest):
    set_web_fetch_enabled(request.enabled)
    append_audit("web_toggle", f"enabled={request.enabled}")
    return {"web_fetch_enabled": request.enabled}


@app.post("/admin/web/allowlist")
def admin_web_allowlist(request: WebAllowlistRequest):
    set_web_access_allowlist(request.allowlist)
    append_audit("web_allowlist", f"{request.allowlist}")
    return {"web_access_allowlist": request.allowlist}


@app.get("/vault/secrets")
def vault_list():
    return {"secrets": list_secrets()}


@app.get("/vault/secrets/{name}")
def vault_get(name: str):
    secret = get_secret(name)
    if secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"name": name, "value": secret}


@app.post("/vault/secrets")
def vault_set(request: VaultSecretRequest):
    set_secret(request.name, request.value)
    append_audit("vault_set", request.name)
    return {"name": request.name, "status": "saved"}


@app.delete("/vault/secrets/{name}")
def vault_delete(name: str):
    removed = delete_secret(name)
    if not removed:
        raise HTTPException(status_code=404, detail="Secret not found")
    append_audit("vault_delete", name)
    return {"name": name, "status": "deleted"}


# ── Agent Builder ─────────────────────────────────────────────────────────────
_AGENTS_DIR = Path(__file__).parent / "agents"


class AgentBuildRequest(BaseModel):
    description: str


class AgentSaveRequest(BaseModel):
    name: str
    description: str
    code: str


@app.get("/agents")
def list_agents():
    _AGENTS_DIR.mkdir(exist_ok=True)
    agents = []
    for f in sorted(_AGENTS_DIR.glob("*.json")):
        try:
            meta = _json.loads(f.read_text(encoding="utf-8"))
            agents.append({"name": meta.get("name", f.stem), "description": meta.get("description", "")})
        except Exception:
            pass
    return {"agents": agents}


@app.post("/agents/build")
def build_agent_route(request: AgentBuildRequest):
    prompt = f"""You are a software architect. Generate a complete, self-contained Python agent script.

Agent description: {request.description}

Rules:
- Add NAME = "snake_case_name" constant at the very top
- Add DESCRIPTION = "one line description" constant
- Add a clear module docstring
- Implement a main run() function with all the logic
- Add if __name__ == '__main__': run() at the bottom
- Add helpful inline comments
- Return ONLY the Python code — no markdown, no code fences, no explanations

Generate the Python agent now:"""
    try:
        _be, result = llm_chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=1500,
        )
        code = (result.choices[0].message.content if _be != "local" else result["message"]["content"]).strip()
        code = re.sub(r"^```(?:python)?\s*\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"\n?```\s*$", "", code, flags=re.MULTILINE)
        code = code.strip()
        name_match = re.search(r'^NAME\s*=\s*["\']([^"\']+)["\']', code, re.MULTILINE)
        if name_match:
            name = re.sub(r'[^a-z0-9_]', '_', name_match.group(1).lower()).strip('_')
        else:
            name = re.sub(r'[^a-z0-9_]', '_', request.description.lower()[:30]).strip('_') or "agent"
        return {"name": name, "code": code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/save")
def save_agent_route(request: AgentSaveRequest):
    _AGENTS_DIR.mkdir(exist_ok=True)
    safe_name = re.sub(r'[^a-z0-9_\-]', '_', request.name.lower())
    (_AGENTS_DIR / f"{safe_name}.py").write_text(request.code, encoding="utf-8")
    (_AGENTS_DIR / f"{safe_name}.json").write_text(
        _json.dumps({"name": safe_name, "description": request.description}, indent=2),
        encoding="utf-8"
    )
    append_audit("agent_saved", safe_name)
    return {"status": "saved", "name": safe_name}


@app.delete("/agents/{name}")
def delete_agent_route(name: str):
    _AGENTS_DIR.mkdir(exist_ok=True)
    safe_name = re.sub(r'[^a-z0-9_\-]', '_', name.lower())
    deleted = False
    for ext in [".py", ".json"]:
        f = _AGENTS_DIR / f"{safe_name}{ext}"
        if f.exists():
            f.unlink()
            deleted = True
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
    append_audit("agent_deleted", safe_name)
    return {"status": "deleted", "name": safe_name}


# ── RAG Memory endpoints ──────────────────────────────────────────────────────
@app.post("/memory/sync")
def memory_sync(_: str = Depends(verify_api_key)):
    """Sync all training entries into the RAG vector store."""
    from rag_memory import sync_all_training, memory_count
    synced = sync_all_training()
    return {"synced": synced, "total_vectors": memory_count()}

@app.get("/memory/status")
def memory_status(_: str = Depends(verify_api_key)):
    from rag_memory import memory_count
    from training_memory import list_training
    return {"vector_count": memory_count(), "training_count": len(list_training())}

@app.post("/memory/search")
def memory_search(request: dict, _: str = Depends(verify_api_key)):
    from rag_memory import search_memory
    query = request.get("query", "")
    results = search_memory(query, top_k=request.get("top_k", 6))
    return {"results": results, "query": query}


# ── Memory CRUD (viewer) ──────────────────────────────────────────────────────
@app.get("/memory/list")
def memory_list(_: str = Depends(verify_api_key)):
    """Return all training memory entries for the memory viewer."""
    from training_memory import list_training
    entries = list_training()
    # Return with index so client can reference them
    return {"entries": [{"id": i, **e} for i, e in enumerate(entries)]}

@app.delete("/memory/entry/{entry_id}")
def memory_delete(entry_id: int, _: str = Depends(verify_api_key)):
    """Delete a training memory entry by index."""
    from training_memory import load_training, save_training
    entries = load_training()
    if entry_id < 0 or entry_id >= len(entries):
        raise HTTPException(status_code=404, detail="Entry not found")
    removed = entries.pop(entry_id)
    save_training(entries)
    return {"status": "deleted", "entry": removed.get("entry", "")}

@app.post("/memory/add")
def memory_add(request: dict, _: str = Depends(verify_api_key)):
    """Manually add a training memory entry."""
    text = (request.get("entry") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="entry required")
    from training_memory import add_training
    add_training(text, category=request.get("category", "manual"))
    try:
        from rag_memory import upsert_memory
        upsert_memory(text, category=request.get("category", "manual"))
    except Exception:
        pass
    return {"status": "added"}


# ── Session Memory endpoints ──────────────────────────────────────────────────
@app.get("/memory/sessions")
def memory_sessions_list(_: str = Depends(verify_api_key)):
    """Return all past session summaries (newest first)."""
    from session_memory import get_recent_summaries, get_summary_count
    summaries = get_recent_summaries(n=50)  # up to 50 past sessions
    return {
        "count": get_summary_count(),
        "summaries": list(reversed([
            {
                "timestamp": e.get("timestamp", ""),
                "entry": e.get("entry", "").replace("[Session summary] ", ""),
            }
            for e in summaries
        ])),
    }

@app.post("/memory/sessions/search")
def memory_sessions_search(request: dict, _: str = Depends(verify_api_key)):
    """Semantic search over past session summaries."""
    query = (request.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query required")
    from session_memory import search_relevant
    results = search_relevant(query, top_k=request.get("top_k", 4))
    return {"query": query, "results": results}

@app.delete("/memory/sessions/clear")
def memory_sessions_clear(_: str = Depends(verify_api_key)):
    """Clear all session summaries (use with care)."""
    from session_memory import clear_all_summaries
    removed = clear_all_summaries()
    return {"status": "cleared", "removed": removed}

@app.get("/memory/sessions/context")
def memory_sessions_context(_: str = Depends(verify_api_key)):
    """Return the formatted session context block as it would appear in the system prompt."""
    from session_memory import get_context_block
    block = get_context_block(n=5)
    return {"context": block}


# ── Proactive greeting ────────────────────────────────────────────────────────
@app.post("/session/greeting")
def session_greeting(request: dict, _: str = Depends(verify_api_key)):
    """Return a proactive greeting that surfaces relevant memories."""
    import threading as _thr
    sid = request.get("session_id", "")

    # Pull recent training entries and RAG search for anything interesting
    from training_memory import list_training
    from rag_memory import search_memory
    entries = list_training()
    # Get session-memory entries (past summaries) — most recent 4
    session_mems = [e["entry"] for e in entries if e.get("category") == "session-memory"][-4:]
    # Also RAG search for topics recently discussed
    rag_hits = search_memory("recent activity projects working on", top_k=4)
    combined = session_mems + [h for h in rag_hits if h not in session_mems]

    def _clean_greeting(raw: str) -> str:
        """Strip think blocks, meta-commentary, and return just the spoken greeting."""
        # Strip <think>...</think> full blocks
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        # For reasoning models that leak inline thinking (no tags), take the last paragraph
        # Reasoning models always put the actual answer last after all the thinking
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
        if paragraphs:
            # If there are multiple paragraphs, the last one is usually the actual output
            raw = paragraphs[-1]
        lines = raw.split("\n")
        clean = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip lines that are clearly meta-commentary / planning / instructions
            meta_patterns = [
                r"^(we need|i need|i will|let'?s craft|let me|here'?s|the user|this is|step \d|plan:|note:|output:|craft:|response:)",
                r"address user as",
                r"include emojis",
                r"should reference",
                r"mention they",
                r"keep \d",
                r"sentences? max",
                r"no meta",
                r"just the spoken",
                r"should be",
            ]
            if any(re.search(p, stripped, re.IGNORECASE) for p in meta_patterns):
                continue
            clean.append(stripped)
        result = " ".join(clean).strip()
        # Strip parenthetical stage directions  (Note: ...) etc.
        result = re.sub(r"\([^)]{10,}\)", "", result)
        result = re.sub(r"\s{2,}", " ", result).strip()
        return result

    if not combined:
        try:
            _be, r = llm_chat(
                [
                    {"role": "system", "content": "You are ATLAS. Output ONLY the greeting. No thinking, no planning, no explanation. Just 1-2 warm sentences."},
                    {"role": "user", "content": "Greet the user as ATLAS when they open the chat."},
                ],
                temperature=0.7, max_tokens=60,
            )
            raw = r.choices[0].message.content if _be != "local" else r["message"]["content"]
            greeting = _clean_greeting(raw)
            return {"greeting": greeting or None}
        except Exception:
            return {"greeting": None}

    memory_block = "\n".join(f"- {m[:200]}" for m in combined[:6])
    try:
        _be, result = llm_chat(
            [
                {"role": "system", "content": "You are ATLAS. Output ONLY the greeting sentences. No thinking, no planning, no labels. Just speak directly."},
                {"role": "user", "content": (
                    f"Greet the user as ATLAS. Context about them:\n{memory_block}\n\n"
                    f"Write 2-3 warm sentences referencing something from their context."
                )},
            ],
            temperature=0.7, max_tokens=100,
        )
        raw = result.choices[0].message.content if _be != "local" else result["message"]["content"]
        greeting = _clean_greeting(raw)
        return {"greeting": greeting or None}
    except Exception:
        return {"greeting": None}


# ── File upload → extract text ────────────────────────────────────────────────
@app.post("/upload/file")
async def upload_file(request):
    """Accept a file upload and return extracted text for injection into chat."""
    from fastapi import UploadFile, File
    raise HTTPException(status_code=400, detail="Use /upload/text endpoint")

class FileTextRequest(BaseModel):
    filename: str
    content_b64: str  # base64-encoded file bytes

@app.post("/upload/text")
def upload_text(request: FileTextRequest, _: str = Depends(verify_api_key)):
    """Decode an uploaded file and extract readable text."""
    import base64, mimetypes
    try:
        raw = base64.b64decode(request.content_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64")

    fname = request.filename.lower()

    # PDF extraction
    if fname.endswith(".pdf"):
        try:
            import io
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                raise HTTPException(status_code=415, detail="pypdf not installed. Run: pip install pypdf")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF parse error: {e}")
    else:
        # Treat as text (code, txt, md, json, csv, etc.)
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            raise HTTPException(status_code=422, detail="Could not decode file as text")

    # Cap at 12000 chars
    text = text.strip()[:12000]
    if not text:
        raise HTTPException(status_code=422, detail="No text could be extracted from this file")

    return {"filename": request.filename, "text": text, "chars": len(text)}


# ── Filesystem Access ─────────────────────────────────────────────────────────
import file_access as _fs
import file_indexer as _fidx

@app.get("/fs/info")
def fs_info(_: str = Depends(verify_api_key)):
    """Return workspace root and write-access status."""
    return {
        "workspace": _fs.workspace_root(),
        "write_enabled": _fs._WRITE_ENABLED,
        "indexed_files": _fidx.indexed_file_count(),
    }

@app.get("/fs/list")
def fs_list(path: str = "", _: str = Depends(verify_api_key)):
    """List files/dirs within the workspace."""
    return _fs.list_dir(path)

@app.get("/fs/read")
def fs_read(path: str, _: str = Depends(verify_api_key)):
    """Read a file's contents."""
    return _fs.read_file(path)

class FsWriteRequest(BaseModel):
    path: str
    content: str
    create_dirs: bool = True

@app.post("/fs/write")
def fs_write(req: FsWriteRequest, _: str = Depends(verify_api_key)):
    """Write content to a file (requires ATLAS_FS_WRITE=1)."""
    return _fs.write_file(req.path, req.content, req.create_dirs)

@app.get("/fs/search")
def fs_search(q: str, path: str = "", max: int = 20, _: str = Depends(verify_api_key)):
    """Search file contents for a text query."""
    return {"query": q, "results": _fs.search_files(q, path, max)}

@app.get("/fs/find")
def fs_find(pattern: str, path: str = "", _: str = Depends(verify_api_key)):
    """Find files by name glob pattern."""
    return {"pattern": pattern, "results": _fs.find_files(pattern, path)}

@app.post("/fs/index")
def fs_index(path: str = "", force: bool = False, _: str = Depends(verify_api_key)):
    """Index workspace files into the RAG vector store."""
    import threading
    def _run():
        _fidx.index_workspace(path, force=force)
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "indexing started", "path": path or "(workspace root)", "force": force}

@app.get("/fs/index/status")
def fs_index_status(_: str = Depends(verify_api_key)):
    """Return how many files are indexed."""
    return {"indexed_files": _fidx.indexed_file_count()}

@app.delete("/fs/index")
def fs_index_clear(_: str = Depends(verify_api_key)):
    """Clear the file index from the vector store."""
    removed = _fidx.clear_file_index()
    return {"cleared": removed}


# ── News Feed Proxy ───────────────────────────────────────────────────────────
@app.get("/news/feed")
async def news_feed(url: str, count: int = 12):
    """Server-side RSS fetch → avoids browser CORS restrictions."""
    import urllib.request, xml.etree.ElementTree as ET
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
        # Strip XML declaration issues
        root = ET.fromstring(raw)
        items = root.findall(".//item")
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = root.findall(".//atom:entry", ns)
        results = []
        for it in items[:count]:
            def _tag(tag):
                el = it.find(tag)
                if el is None:
                    return ""
                return (el.text or "").strip()
            link_el = it.find("link")
            link = ""
            if link_el is not None:
                link = (link_el.get("href") or link_el.text or "").strip()
            results.append({
                "title": _tag("title"),
                "link": link,
                "date": _tag("pubDate") or _tag("updated"),
            })
        channel = root.find("channel")
        source = ""
        if channel is not None:
            t = channel.find("title")
            source = (t.text or "").strip() if t is not None else ""
        return {"status": "ok", "source": source, "items": [r for r in results if r["title"]]}
    except Exception as e:
        return {"status": "error", "message": str(e), "items": []}


# ── System Info ───────────────────────────────────────────────────────────────
@app.get("/system/info")
def system_info():
    import platform, datetime
    info: dict = {
        "platform": platform.system(),
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python": platform.python_version(),
        "uptime_seconds": round(_time.monotonic() - _APP_START_TIME),
    }
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        info.update({
            "cpu_percent": cpu,
            "ram_used_gb": round(mem.used / 1e9, 1),
            "ram_total_gb": round(mem.total / 1e9, 1),
            "ram_percent": round(mem.percent, 1),
            "disk_used_gb": round(disk.used / 1e9, 1),
            "disk_total_gb": round(disk.total / 1e9, 1),
            "disk_percent": round(disk.percent, 1),
        })
    except ImportError:
        info["psutil"] = "not installed"
    return info


# ── Remote Tunnel ─────────────────────────────────────────────────────────────
_tunnel_proc = None
_tunnel_url: str | None = None


@app.post("/remote/start")
def remote_start():
    global _tunnel_proc, _tunnel_url
    import shutil, re as _re2, time
    if _tunnel_proc and _tunnel_proc.poll() is None:
        return {"status": "already_running", "url": _tunnel_url}
    if not shutil.which("cloudflared"):
        raise HTTPException(
            status_code=503,
            detail="cloudflared not installed. Get it from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        )
    _tunnel_proc = _subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=_subprocess.PIPE, stderr=_subprocess.STDOUT, text=True
    )
    url = None
    deadline = time.time() + 20
    while time.time() < deadline and _tunnel_proc.poll() is None:
        line = _tunnel_proc.stdout.readline()
        match = _re2.search(r'https://[\w-]+\.trycloudflare\.com', line)
        if match:
            url = match.group()
            break
    _tunnel_url = url
    return {"status": "started", "url": url or "Tunnel starting... check status in a moment."}


@app.post("/remote/stop")
def remote_stop():
    global _tunnel_proc, _tunnel_url
    if _tunnel_proc:
        _tunnel_proc.terminate()
        _tunnel_proc = None
    _tunnel_url = None
    return {"status": "stopped"}


@app.get("/remote/status")
def remote_status_route():
    global _tunnel_proc, _tunnel_url
    running = bool(_tunnel_proc and _tunnel_proc.poll() is None)
    return {"running": running, "url": _tunnel_url if running else None}


# ── Autonomous Task Loop ───────────────────────────────────────────────────────
# ATLAS can receive a high-level goal and autonomously plan + execute it step-by-step.
# Each step may call tools (run_bash, write_file, run_code, web_search, etc.)
# Streams progress as Server-Sent Events (SSE) so the UI can show live output.
# Projects are scaffolded in ATLAS_WORKSPACE/projects/<project_name>/

_PROJECTS_DIR = Path(_os.environ.get("ATLAS_WORKSPACE", str(Path(__file__).parent.parent))) / "projects"
_TASK_MAX_STEPS = 20   # safety cap — prevents runaway loops

class TaskRequest(BaseModel):
    goal: str
    session_id: str = ""
    max_steps: int = _TASK_MAX_STEPS

@app.get("/projects")
def list_projects(_: str = Depends(verify_api_key)):
    """List all autonomous-build projects."""
    _PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = []
    for d in sorted(_PROJECTS_DIR.iterdir()):
        if d.is_dir():
            meta_f = d / ".atlas_task.json"
            meta = {}
            if meta_f.exists():
                try:
                    meta = _json.loads(meta_f.read_text())
                except Exception:
                    pass
            files = [f.name for f in d.iterdir() if f.is_file() and not f.name.startswith(".")]
            projects.append({
                "name": d.name,
                "goal": meta.get("goal", ""),
                "status": meta.get("status", "unknown"),
                "steps": meta.get("steps_done", 0),
                "files": files[:12],
                "created": meta.get("created", ""),
            })
    return {"projects": projects}

@app.get("/task/run")
async def task_run_stream(goal: str, max_steps: int = _TASK_MAX_STEPS, _: str = Depends(verify_api_key)):
    """
    SSE stream — ATLAS autonomously plans and executes a goal.
    Client reads event: data payloads line-by-line.
    """
    import datetime as _dt

    def _sse(payload: dict) -> str:
        return f"data: {_json.dumps(payload)}\n\n"

    async def _stream():
        # ── 1. Derive a slug project name ────────────────────────────────────
        slug = re.sub(r'[^a-z0-9]+', '_', goal.lower().strip())[:40].strip('_') or "project"
        project_dir = _PROJECTS_DIR / slug
        project_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "goal": goal,
            "status": "running",
            "steps_done": 0,
            "created": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        (project_dir / ".atlas_task.json").write_text(_json.dumps(meta, indent=2))

        yield _sse({"type": "start", "goal": goal, "project": slug})

        # ── 2. Planning phase ────────────────────────────────────────────────
        yield _sse({"type": "status", "text": "Planning..."})

        plan_prompt = f"""You are ATLAS, an autonomous AI agent. The user gave you this goal:

GOAL: {goal}

PROJECT DIRECTORY: projects/{slug}/  (all files go here using write_file with path "projects/{slug}/filename")

Your available tools: web_search, web_fetch, run_code, run_bash, read_file, write_file, list_dir, search_files, remember.

Create a numbered execution plan (maximum {min(max_steps, _TASK_MAX_STEPS)} steps). Each step MUST be one concrete action — not vague. Example:
1. write_file — Create projects/{slug}/index.html with the basic skeleton
2. write_file — Create projects/{slug}/style.css with layout styles
3. run_bash — Run ls projects/{slug}/ to verify files exist

Output ONLY the numbered plan. No intro, no explanation."""

        try:
            _be, plan_r = llm_chat([{"role": "user", "content": plan_prompt}], temperature=0.2, max_tokens=600)
            plan_text = (plan_r.choices[0].message.content if _be != "local" else plan_r["message"]["content"]).strip()
            plan_text = re.sub(r"<think>.*?</think>", "", plan_text, flags=re.DOTALL).strip()
        except Exception as e:
            yield _sse({"type": "error", "text": f"Planning failed: {e}"})
            return

        # Parse numbered steps
        raw_steps = re.findall(r'^\s*\d+[\.\)]\s*(.+)$', plan_text, re.MULTILINE)
        if not raw_steps:
            raw_steps = [s.strip() for s in plan_text.split('\n') if s.strip()]
        steps = raw_steps[:min(max_steps, _TASK_MAX_STEPS)]

        yield _sse({"type": "plan", "steps": steps, "text": plan_text})

        # ── 3. Execution loop ────────────────────────────────────────────────
        history = [
            {"role": "system", "content": (
                f"You are ATLAS executing an autonomous task. Goal: {goal}\n"
                f"Project directory: projects/{slug}/\n"
                f"Use tools to complete each step. For write_file always use path 'projects/{slug}/filename'.\n"
                f"After each tool call, briefly describe what you did and what's next."
            )},
        ]

        for step_num, step_desc in enumerate(steps, 1):
            if step_num > max_steps:
                break

            yield _sse({"type": "step_start", "step": step_num, "total": len(steps), "desc": step_desc})

            history.append({"role": "user", "content": f"Execute step {step_num}: {step_desc}"})

            # Allow up to 3 tool-call rounds per step
            step_output = ""
            for _round in range(3):
                try:
                    _be, resp = llm_chat(history, temperature=0.1, max_tokens=1200, tools=OLLAMA_TOOLS)
                    if _be == "local":
                        msg = resp["message"]
                        content = msg.get("content", "") or ""
                        tool_calls = msg.get("tool_calls", [])
                    else:
                        msg = resp.choices[0].message
                        content = msg.content or ""
                        tool_calls = msg.tool_calls or []
                except Exception as e:
                    yield _sse({"type": "step_error", "step": step_num, "text": str(e)})
                    break

                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

                if not tool_calls:
                    # No tool calls — ATLAS responded in prose
                    step_output = content
                    history.append({"role": "assistant", "content": content})
                    break

                # Execute each tool call
                tool_results_for_history = []
                for tc in tool_calls:
                    if _be == "local":
                        fn = tc.get("function", tc)
                        tc_name = fn.get("name", "")
                        tc_args = fn.get("arguments", {})
                        tc_id = None
                    else:
                        tc_name = tc.function.name
                        raw_args = tc.function.arguments
                        try:
                            tc_args = _json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except Exception:
                            tc_args = {}
                        tc_id = tc.id

                    yield _sse({"type": "tool_call", "step": step_num, "tool": tc_name, "args": tc_args})

                    try:
                        tool_result = execute_tool(tc_name, tc_args)
                    except Exception as tex:
                        tool_result = f"Tool error: {tex}"

                    # Truncate very long results
                    if len(tool_result) > 2000:
                        tool_result = tool_result[:2000] + "\n...[truncated]"

                    yield _sse({"type": "tool_result", "step": step_num, "tool": tc_name,
                                "result": tool_result[:500] + ("..." if len(tool_result) > 500 else "")})

                    tool_results_for_history.append({"name": tc_name, "result": tool_result, "id": tc_id})

                # Add tool calls + results to history
                if _be != "local":
                    history.append({
                        "role": "assistant",
                        "content": content or None,
                        "tool_calls": [
                            {"id": tr["id"] or f"call_{i}", "type": "function",
                             "function": {"name": tr["name"], "arguments": "{}"}}
                            for i, tr in enumerate(tool_results_for_history)
                        ],
                    })
                    for tr in tool_results_for_history:
                        history.append({
                            "role": "tool",
                            "tool_call_id": tr["id"] or "call_0",
                            "content": tr["result"],
                        })
                else:
                    history.append({"role": "tool", "content": "\n".join(
                        f"[{tr['name']}] {tr['result']}" for tr in tool_results_for_history
                    )})

            yield _sse({"type": "step_done", "step": step_num, "output": step_output})

            # Update meta
            meta["steps_done"] = step_num
            (project_dir / ".atlas_task.json").write_text(_json.dumps(meta, indent=2))

        # ── 4. Wrap up ───────────────────────────────────────────────────────
        meta["status"] = "done"
        (project_dir / ".atlas_task.json").write_text(_json.dumps(meta, indent=2))

        # List what was built
        built = [f.name for f in project_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        yield _sse({"type": "done", "project": slug, "files": built,
                    "text": f"Task complete. Built {len(built)} file(s) in projects/{slug}/"})

    return StreamingResponse(_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/task/restart-server")
def task_restart_server(_: str = Depends(verify_api_key)):
    """
    Restarts the ATLAS uvicorn process. ATLAS calls this after modifying app.py.
    Schedules restart in 1.5s to allow the response to be sent first.
    """
    import threading, sys, os, signal
    def _do_restart():
        import time
        time.sleep(1.5)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=_do_restart, daemon=True).start()
    return {"status": "restarting", "message": "Server will restart in ~1.5 seconds"}
