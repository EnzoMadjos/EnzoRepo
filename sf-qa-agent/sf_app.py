"""
sf_app.py — main FastAPI application for the Salesforce QA Test Automation Agent.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from typing import Optional

import app_logger
import auth
import config
import file_parser
import httpx
import llm_planner
import org_profiles
import sf_executor
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sf_client import SalesforceClient
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceAuthenticationFailed
from sse_starlette.sse import EventSourceResponse

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------

app = FastAPI(title="SF QA Agent", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))

_static_dir = config.BASE_DIR / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


def _restart_server_process() -> None:
    """Spawn a replacement uvicorn process, then terminate the current one."""
    port = str(config.APP_PORT)
    host = "0.0.0.0"
    cwd = str(config.BASE_DIR)
    python_exe = sys.executable

    if os.name == "nt":
        delay_ticks = 3
        restart_cmd = (
            f"ping 127.0.0.1 -n {delay_ticks} > nul && "
            f'cd /d "{cwd}" && '
            f'"{python_exe}" -m uvicorn sf_app:app --host {host} --port {port}'
        )
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
        subprocess.Popen(
            ["cmd.exe", "/c", restart_cmd],
            cwd=cwd,
            creationflags=creationflags,
            close_fds=True,
        )
    else:
        restart_cmd = (
            f"sleep 1; cd {shlex.quote(cwd)} && exec "
            f"{shlex.quote(python_exe)} -m uvicorn sf_app:app --host {host} --port {port}"
        )
        subprocess.Popen(
            ["sh", "-c", restart_cmd],
            cwd=cwd,
            start_new_session=True,
            close_fds=True,
        )

    os._exit(0)


# ---------------------------------------------------------------------------
# Routes — public
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("qa.html", {"request": request})


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/info")
async def info(request: Request) -> JSONResponse:
    import socket

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        # Fallback: connect outward to get the real LAN IP (doesn't send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"
    port = config.APP_PORT
    return JSONResponse(
        {
            "hostname": hostname,
            "local_ip": local_ip,
            "port": port,
            "local_url": f"http://localhost:{port}",
            "network_url": f"http://{local_ip}:{port}",
        }
    )


# ---------------------------------------------------------------------------
# Routes — auth
# ---------------------------------------------------------------------------


@app.post("/auth/login")
async def login(body: dict) -> JSONResponse:
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")
    security_token: str = body.get("security_token", "")
    domain: str = body.get("domain", "login").strip() or "login"
    consumer_key: str = body.get("consumer_key", "").strip()
    consumer_secret: str = body.get("consumer_secret", "").strip()

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    base_url = f"https://{'test' if domain == 'test' else 'login'}.salesforce.com"

    # Attempt OAuth 2.0 password flow (requires Connected App)
    if consumer_key and consumer_secret:
        try:
            import httpx as _httpx

            resp = _httpx.post(
                f"{base_url}/services/oauth2/token",
                data={
                    "grant_type": "password",
                    "client_id": consumer_key,
                    "client_secret": consumer_secret,
                    "username": username,
                    "password": password + security_token,
                },
                timeout=20,
            )
            if resp.status_code != 200:
                err = resp.json().get("error_description", resp.text)
                app_logger.error("OAuth login failed", username=username, detail=err)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Salesforce OAuth failed: {err}",
                )
            oauth_data = resp.json()
            instance_url: str = oauth_data["instance_url"]
            access_token: str = oauth_data["access_token"]
            org_id: str = (
                oauth_data.get("id", "").split("/")[-2] if "id" in oauth_data else ""
            )
        except HTTPException:
            raise
        except Exception as exc:
            app_logger.error("OAuth connection error", exc=exc, username=username)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OAuth connection error: {exc}",
            )
    else:
        # Fall back to SOAP login via simple_salesforce
        try:
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain,
            )
            org_id = sf.sf_org_id or ""
            instance_url = sf.base_url.split("/services")[0]
            access_token = sf.session_id
        except SalesforceAuthenticationFailed as exc:
            app_logger.error("SOAP login failed", exc=exc, username=username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Salesforce authentication failed: {exc}",
            )
        except Exception as exc:
            app_logger.error("SOAP connection error", exc=exc, username=username)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not connect to Salesforce: {exc}",
            )

    token = auth.create_session(
        username=username,
        sf_password=password,
        sf_security_token=security_token,
        sf_domain=domain,
        org_id=org_id,
        instance_url=instance_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
    )
    app_logger.info("Login successful", username=username, instance_url=instance_url)
    return JSONResponse(
        {
            "token": token,
            "username": username,
            "org_id": org_id,
            "instance_url": instance_url,
        }
    )


@app.post("/auth/logout")
async def logout(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    return JSONResponse({"status": "logged out"})


# ---------------------------------------------------------------------------
# Routes — org profiles
# ---------------------------------------------------------------------------


@app.get("/profiles")
async def get_profiles() -> JSONResponse:
    return JSONResponse(org_profiles.list_profiles())


@app.post("/profiles/save")
async def save_profile_route(
    body: dict,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    name: str = body.get("name", "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile name is required"
        )
    profile = {
        "username": body.get("username", ""),
        "password": body.get("password", ""),
        "security_token": body.get("security_token", ""),
        "domain": body.get("domain", "login"),
        "consumer_key": body.get("consumer_key", ""),
        "consumer_secret": body.get("consumer_secret", ""),
    }
    org_profiles.save_profile(name, profile)
    return JSONResponse({"status": "saved", "name": name})


@app.get("/profiles/{name}")
async def get_profile_route(
    name: str,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    profile = org_profiles.load_profile(name)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    # Never return password/secret to frontend — auto-login instead
    return JSONResponse(
        {
            "username": profile.get("username", ""),
            "domain": profile.get("domain", "login"),
            "consumer_key": profile.get("consumer_key", ""),
            "has_password": bool(profile.get("password")),
            "has_security_token": bool(profile.get("security_token")),
            "has_consumer_secret": bool(profile.get("consumer_secret")),
        }
    )


@app.post("/profiles/{name}/login")
async def login_with_profile(name: str) -> JSONResponse:
    """Log in using a saved org profile (credentials retrieved from encrypted storage)."""
    profile = org_profiles.load_profile(name)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    # Re-use the same login logic by delegating to the login route body
    return await login(
        {
            "username": profile.get("username", ""),
            "password": profile.get("password", ""),
            "security_token": profile.get("security_token", ""),
            "domain": profile.get("domain", "login"),
            "consumer_key": profile.get("consumer_key", ""),
            "consumer_secret": profile.get("consumer_secret", ""),
        }
    )


@app.delete("/profiles/{name}")
async def delete_profile_route(
    name: str,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    found = org_profiles.delete_profile(name)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return JSONResponse({"status": "deleted", "name": name})


# ---------------------------------------------------------------------------
# Routes — protected
# ---------------------------------------------------------------------------


@app.post("/run-test")
async def run_test(
    scenario: Optional[str] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
    session: auth.SessionData = Depends(auth.require_auth),
) -> EventSourceResponse:
    """
    Accept either a pasted scenario (form field) or an uploaded file.
    Streams SSE events back to the browser as the test executes.
    Uses the logged-in user's Salesforce session.
    """
    if not scenario and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide scenario text or upload a file",
        )

    # Parse input
    if file:
        raw_bytes = await file.read()
        try:
            script_text = file_parser.parse_bytes(file.filename or "", raw_bytes)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            )
    else:
        script_text = file_parser.parse_text(scenario or "")

    if not script_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Test script is empty"
        )

    script_hash = hashlib.sha1(
        script_text.encode("utf-8", errors="ignore")
    ).hexdigest()[:12]
    script_preview = script_text[:2000]
    app_logger.info(
        "Run test received",
        username=session.username,
        script_hash=script_hash,
        script_len=len(script_text),
        script_preview=script_preview,
    )

    # Build SF client from this user's session
    sf_client = SalesforceClient.from_session(session)

    async def event_stream():
        yield {
            "data": json.dumps(
                {
                    "type": "status",
                    "message": f"Connected to org: {session.instance_url}",
                }
            )
        }
        yield {
            "data": json.dumps(
                {"type": "status", "message": "Planning test from script..."}
            )
        }

        plan_started = time.monotonic()
        try:
            plan = llm_planner.plan(script_text, client=sf_client)
            app_logger.info(
                "LLM planning completed",
                username=session.username,
                script_hash=script_hash,
                plan_steps=len(plan),
                planning_ms=int((time.monotonic() - plan_started) * 1000),
            )
        except Exception as exc:
            app_logger.error(
                "Planning failed",
                exc=exc,
                username=session.username,
                script_hash=script_hash,
                script_preview=script_preview,
            )
            yield {
                "data": json.dumps(
                    {"type": "error", "message": f"Planning failed: {exc}"}
                )
            }
            return

        yield {
            "data": json.dumps(
                {
                    "type": "status",
                    "message": f"Plan ready — {len(plan)} step(s). Executing...",
                }
            )
        }
        app_logger.info(
            "Executing test plan",
            username=session.username,
            steps=len(plan),
            script_hash=script_hash,
        )

        exec_started = time.monotonic()
        for event in sf_executor.execute(
            plan,
            sf_client,
            run_context={
                "username": session.username,
                "script_hash": script_hash,
                "script_preview": script_preview,
            },
        ):
            yield {"data": json.dumps(event)}

        app_logger.info(
            "Test run completed",
            username=session.username,
            script_hash=script_hash,
            execution_ms=int((time.monotonic() - exec_started) * 1000),
        )
        yield {"data": json.dumps({"type": "done"})}

    return EventSourceResponse(event_stream())


# ---------------------------------------------------------------------------
# Routes — admin (requires auth)
# ---------------------------------------------------------------------------


@app.get("/admin/logs")
async def admin_logs(
    n: int = 200,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Return the N most-recent log entries as JSON (newest first)."""
    return JSONResponse(app_logger.get_recent(n))


@app.delete("/admin/logs")
async def admin_clear_logs(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    app_logger.clear_logs()
    app_logger.info("Logs cleared", username=session.username)
    return JSONResponse({"status": "cleared"})


@app.get("/admin/prompt")
async def admin_get_prompt(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Return the current LLM system prompt."""
    import llm_planner

    return JSONResponse({"prompt": llm_planner._SYSTEM_PROMPT_BASE})


@app.get("/schema/objects")
async def get_schema_objects(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Return all queryable sObjects from the connected org."""
    sf_client = SalesforceClient.from_session(session)
    objects = sf_client.describe_all_objects()
    return JSONResponse({"objects": objects})


@app.post("/admin/pull-model")
async def admin_pull_model(
    session: auth.SessionData = Depends(auth.require_auth),
) -> EventSourceResponse:
    """Pull the configured Ollama model, streaming progress."""

    async def _stream():
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama",
                "pull",
                config.OLLAMA_MODEL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            async for line in proc.stdout:
                text = line.decode(errors="replace").rstrip()
                if text:
                    yield {"data": json.dumps({"type": "progress", "message": text})}
            await proc.wait()
            if proc.returncode == 0:
                yield {
                    "data": json.dumps(
                        {
                            "type": "done",
                            "message": f"{config.OLLAMA_MODEL} pulled successfully",
                        }
                    )
                }
            else:
                yield {
                    "data": json.dumps(
                        {
                            "type": "error",
                            "message": f"ollama pull exited with code {proc.returncode}",
                        }
                    )
                }
        except Exception as exc:
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}

    return EventSourceResponse(_stream())


# ── Relay helpers ──────────────────────────────────────────────────────────────


def _relay_headers() -> dict:
    """Authorization header for outbound relay requests."""
    from config import RELAY_TOKEN

    return {"Authorization": f"Bearer {RELAY_TOKEN}"} if RELAY_TOKEN else {}


@app.get("/admin/relay/status")
async def admin_relay_status(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """
    Ping the relay server and return its online status + update_available flag.
    Called by the browser every ~30 s to keep the connection indicator current.
    Uses the runtime RELAY_URL which may have been set via /admin/relay/connect.
    """
    import config

    relay_url = config.RELAY_URL
    if not relay_url:
        return JSONResponse(
            {
                "relay_configured": False,
                "online": False,
                "update_available": bool(config.UPDATE_URL),
                "version": None,
                "saved_url": "",
            }
        )
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            r = await client.get(f"{relay_url}/ping")
            r.raise_for_status()
            data = r.json()
        return JSONResponse(
            {
                "relay_configured": True,
                "online": True,
                "update_available": data.get("update_available", False),
                "version": data.get("version"),
                "message": data.get("message", "Support server is online."),
                "saved_url": relay_url,
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "relay_configured": True,
                "online": False,
                "update_available": False,
                "version": None,
                "message": f"Could not reach server: {exc}",
                "saved_url": relay_url,
            }
        )


class RelayConnectRequest(BaseModel):
    url: str


@app.post("/admin/relay/connect")
async def admin_relay_connect(
    body: RelayConnectRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """
    Accept a relay URL pasted by the user, validate it by pinging /ping,
    then save it to the live config and persist it to .env.
    """
    import re

    import config

    url = body.url.strip().rstrip("/")

    # Basic URL sanity check
    if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url):
        raise HTTPException(
            status_code=422, detail="That doesn't look like a valid URL."
        )

    # Ping the relay to confirm it's live
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.get(f"{url}/ping")
            r.raise_for_status()
            data = r.json()
        if not data.get("online"):
            raise ValueError("Server responded but reported offline.")
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to that URL — make sure your admin is online. ({exc})",
        )

    # Save to live config so everything works immediately without restart
    config.RELAY_URL = url

    # Persist to .env so it survives a server restart
    env_path = config.BASE_DIR / ".env"
    if env_path.exists():
        text = env_path.read_text(encoding="utf-8")
        if "RELAY_URL=" in text:
            lines = []
            for line in text.splitlines():
                if line.startswith("RELAY_URL="):
                    lines.append(f"RELAY_URL={url}")
                else:
                    lines.append(line)
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            with env_path.open("a", encoding="utf-8") as f:
                f.write(f"\nRELAY_URL={url}\n")

    app_logger.info("Relay URL connected", username=session.username, url=url)
    return JSONResponse(
        {
            "status": "connected",
            "url": url,
            "update_available": data.get("update_available", False),
            "version": data.get("version"),
        }
    )


@app.post("/admin/relay/disconnect")
async def admin_relay_disconnect(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Clear the relay URL from live config and .env."""
    import config

    config.RELAY_URL = ""
    env_path = config.BASE_DIR / ".env"
    if env_path.exists():
        text = env_path.read_text(encoding="utf-8")
        lines = [
            l if not l.startswith("RELAY_URL=") else "RELAY_URL="
            for l in text.splitlines()
        ]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    app_logger.info("Relay URL disconnected", username=session.username)
    return JSONResponse({"status": "disconnected"})


@app.get("/admin/update/check")
async def admin_update_check(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Check for available update — via relay (if configured) or static UPDATE_URL."""
    from config import RELAY_URL, UPDATE_URL

    if RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                r = await client.get(f"{RELAY_URL}/ping")
                r.raise_for_status()
                data = r.json()
            return JSONResponse(
                {
                    "available": data.get("update_available", False),
                    "source": "relay",
                    "version": data.get("version"),
                }
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Relay offline: {exc}")
    return JSONResponse(
        {
            "available": bool(UPDATE_URL),
            "source": "static",
            "version": None,
        }
    )


class LogReportRequest(BaseModel):
    message: str = ""  # optional note from the user


@app.post("/admin/logs/report")
async def admin_logs_report(
    body: LogReportRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """
    Send log report to relay server (primary) or Discord/Slack webhook (fallback).
    """
    import datetime
    import platform

    from config import LOG_WEBHOOK_URL, RELAY_URL

    recent = app_logger.get_recent(100)

    # ── Try relay first ───────────────────────────────────────────────────────
    if RELAY_URL:
        payload = {
            "username": session.username,
            "machine": platform.node(),
            "message": body.message.strip(),
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "logs": list(reversed(recent)),  # chronological order
        }
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.post(
                    f"{RELAY_URL}/logs",
                    json=payload,
                    headers=_relay_headers(),
                )
                r.raise_for_status()
        except Exception as exc:
            app_logger.error("Failed to send log report to relay", error=str(exc))
            raise HTTPException(
                status_code=502,
                detail=f"Support server is offline or unreachable: {exc}",
            )

        app_logger.info("Log report sent via relay", username=session.username)
        return JSONResponse({"status": "sent", "via": "relay", "lines": len(recent)})

    # ── Fallback: Discord/Slack webhook ───────────────────────────────────────
    if not LOG_WEBHOOK_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Support server is offline and no fallback webhook is configured.",
        )

    lines = []
    for entry in reversed(recent):
        ts = entry.get("ts", "")
        lvl = entry.get("level", "").upper()
        msg = entry.get("msg", "")
        extra = {k: v for k, v in entry.items() if k not in ("ts", "level", "msg")}
        line = f"[{ts}] {lvl}: {msg}"
        if extra:
            line += f"  {extra}"
        lines.append(line)

    log_text = "\n".join(lines) if lines else "(no log entries)"
    user_note = body.message.strip()
    header = (
        f"🛠 **SF QA Agent — Error Log Report**\n"
        f"• User: `{session.username}`\n"
        f"• Machine: `{platform.node()}`\n"
        f"• Time: `{datetime.datetime.now().isoformat(timespec='seconds')}`\n"
    )
    if user_note:
        header += f"• Note: {user_note}\n"
    max_log_chars = 1900 - len(header) - 20
    if len(log_text) > max_log_chars:
        log_text = "…(truncated)\n" + log_text[-max_log_chars:]
    content = f"{header}\n```\n{log_text}\n```"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.post(
                LOG_WEBHOOK_URL, json={"content": content, "text": content}
            )
            r.raise_for_status()
    except Exception as exc:
        app_logger.error("Failed to send log report via webhook", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Webhook delivery failed: {exc}")

    app_logger.info("Log report sent via webhook", username=session.username)
    return JSONResponse({"status": "sent", "via": "webhook", "lines": len(recent)})


@app.post("/admin/update/apply")
async def admin_update_apply(
    background_tasks: BackgroundTasks,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """
    Download patch.zip from relay (primary) or static UPDATE_URL (fallback),
    extract into the app directory. Uvicorn --reload picks up changes automatically.
    """
    import io
    import zipfile
    from pathlib import Path

    from config import BASE_DIR, RELAY_URL, UPDATE_URL

    # Determine download URL
    if RELAY_URL:
        patch_url = f"{RELAY_URL}/update/patch"
        req_headers = _relay_headers()
    elif UPDATE_URL:
        patch_url = UPDATE_URL
        req_headers = {}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No update source configured and relay is offline.",
        )

    app_logger.info("Update apply requested", username=session.username, url=patch_url)

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            r = await client.get(patch_url, headers=req_headers)
            r.raise_for_status()
            data = r.content
    except Exception as exc:
        app_logger.error("Failed to download patch", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Download failed: {exc}")

    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise HTTPException(
            status_code=422, detail="Downloaded file is not a valid zip archive."
        )

    updated: list[str] = []
    skipped: list[str] = []
    ALLOWED_EXTS = {
        ".py",
        ".html",
        ".css",
        ".js",
        ".txt",
        ".json",
        ".md",
        ".env.example",
    }
    BLOCKED = {"auth.py", "config.py"}

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            name = member.filename.replace("\\", "/")
            for prefix in ("patch/", "app/", "SalesforceQA-Install/app/"):
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    break
            if ".." in name or name.startswith("/"):
                skipped.append(f"{member.filename} (path traversal blocked)")
                continue
            ext = Path(name).suffix.lower()
            if ext not in ALLOWED_EXTS and Path(name).name not in {"requirements.txt"}:
                skipped.append(f"{name} (extension not allowed)")
                continue
            if Path(name).name in BLOCKED:
                skipped.append(f"{name} (protected file)")
                continue
            dest = BASE_DIR / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(member))
            updated.append(name)

    app_logger.info("Patch applied", username=session.username, files=updated)

    if updated:
        background_tasks.add_task(_restart_server_process)

    # Notify relay so it clears update_available
    if RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                await client.post(
                    f"{RELAY_URL}/update/consumed", headers=_relay_headers()
                )
        except Exception:
            pass  # non-fatal

    return JSONResponse(
        {
            "status": "applied",
            "updated": updated,
            "skipped": skipped,
            "restart_scheduled": bool(updated),
            "message": (
                f"{len(updated)} file(s) updated. Refresh the page in a moment while the local server restarts."
                if updated
                else "No files were updated."
            ),
        }
    )


@app.post("/admin/prompt")
async def admin_set_prompt(
    body: dict,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """
    Replace the live LLM system prompt without restarting the server.
    Changes are in-memory only — they reset on server restart.
    """
    import llm_planner

    new_prompt: str = body.get("prompt", "").strip()
    if not new_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt cannot be empty"
        )
    llm_planner._SYSTEM_PROMPT_BASE = new_prompt
    app_logger.info(
        "System prompt updated by user",
        username=session.username,
        length=len(new_prompt),
    )
    return JSONResponse({"status": "updated", "length": len(new_prompt)})
