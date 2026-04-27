"""
app.py — main FastAPI application for PITOGO Barangay App.

Includes:
  - Login / Logout (local users with audit trail)
  - Document printing (barangay clearance, certificate of residency, indigency)
  - Admin panel (logs, support relay, updates)
  - Peer discovery status endpoint
  - Support relay (reused from sf-qa-agent)
  - Update delivery (signed patch.zip)
"""
from __future__ import annotations

import platform
import sys
import time
import zipfile
import os
import shutil
from pathlib import Path
from typing import Optional

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import auth
import app_logger
import config
import discovery

# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))

_static_dir = config.BASE_DIR / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ── Discovery state (set at startup) ─────────────────────────────────────────

_server_role: str       = "unknown"   # "leader" | "client"
_leader_addr: Optional[tuple] = None


@app.on_event("startup")
async def _startup() -> None:
    global _server_role, _leader_addr

    def on_elected():
        global _server_role
        _server_role = "leader"
        app_logger.info("This instance is the LEADER (backend server for LAN)")

    def on_client(addr: tuple):
        global _server_role, _leader_addr
        _server_role = "client"
        _leader_addr = addr
        app_logger.info("This instance is a CLIENT", leader_host=addr[0], leader_port=addr[1])

    def on_leader_lost():
        global _server_role, _leader_addr
        _server_role = "unknown"
        _leader_addr = None
        app_logger.warn("Leader lost — re-running discovery")
        discovery.start(config.APP_PORT, on_elected, on_client, on_leader_lost)

    discovery.start(config.APP_PORT, on_elected, on_client, on_leader_lost)


@app.on_event("shutdown")
async def _shutdown() -> None:
    discovery.stop()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _relay_headers() -> dict:
    return {"Authorization": f"Bearer {config.RELAY_TOKEN}"} if config.RELAY_TOKEN else {}


def _restart_server() -> None:
    time.sleep(1.5)
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ── UI ────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "app_name": config.APP_NAME})


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
async def login(body: LoginRequest) -> JSONResponse:
    user = auth.verify_user(body.username, body.password)
    if not user:
        app_logger.warn("Failed login attempt", username=body.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    token = auth.create_session(body.username, user["role"], user.get("display_name", body.username))
    app_logger.info("Login", username=body.username, role=user["role"])
    return JSONResponse({"token": token, "username": body.username, "role": user["role"], "display_name": user.get("display_name", body.username)})


@app.post("/auth/logout")
async def logout(session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    app_logger.info("Logout", username=session.username)
    return JSONResponse({"status": "logged out"})


# ── Server status ─────────────────────────────────────────────────────────────

@app.get("/status")
async def server_status() -> JSONResponse:
    import socket as _sock
    hostname = _sock.gethostname()
    try:
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"
    return JSONResponse({
        "role":        _server_role,
        "leader_addr": list(_leader_addr) if _leader_addr else None,
        "hostname":    hostname,
        "local_ip":    local_ip,
        "port":        config.APP_PORT,
    })


# ── Document printing ─────────────────────────────────────────────────────────

class DocumentRequest(BaseModel):
    doc_type:    str        # "clearance" | "residency" | "indigency"
    full_name:   str
    address:     str
    purpose:     str
    extra:       dict = {}  # any additional fields per doc type


@app.post("/documents/print")
async def print_document(
    body: DocumentRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """
    Generate a printable barangay document.
    Returns the rendered HTML string ready to be opened/printed in browser.
    """
    allowed = {"clearance", "residency", "indigency"}
    if body.doc_type not in allowed:
        raise HTTPException(status_code=400, detail=f"doc_type must be one of: {allowed}")

    template_name = f"docs/{body.doc_type}.html"
    try:
        rendered = templates.get_template(template_name).render(
            full_name=body.full_name,
            address=body.address,
            purpose=body.purpose,
            extra=body.extra,
            issued_by=session.display_name,
            issued_at=time.strftime("%B %d, %Y"),
        )
    except Exception as exc:
        app_logger.error("Document render error", exc=exc, doc_type=body.doc_type)
        raise HTTPException(status_code=500, detail=f"Document render failed: {exc}")

    app_logger.info(
        "Document printed",
        username=session.username,
        doc_type=body.doc_type,
        full_name=body.full_name,
    )
    return JSONResponse({"html": rendered, "doc_type": body.doc_type})


# ── Admin — logs ──────────────────────────────────────────────────────────────

@app.get("/admin/logs")
async def get_logs(n: int = 200, session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    return JSONResponse(app_logger.get_recent(n))


@app.delete("/admin/logs")
async def clear_logs(session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    app_logger.clear_logs()
    app_logger.info("Logs cleared", username=session.username)
    return JSONResponse({"status": "cleared"})


class LogReportRequest(BaseModel):
    message: str = ""


@app.post("/admin/logs/report")
async def report_logs(
    body: LogReportRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Send recent logs to the relay server (or fallback webhook)."""
    recent = app_logger.get_recent(200)
    if not recent:
        raise HTTPException(status_code=400, detail="No logs to send.")

    payload = {
        "username": session.username,
        "machine":  platform.node(),
        "message":  body.message,
        "logs":     recent,
        "ts":       time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    if config.RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(f"{config.RELAY_URL}/logs", json=payload, headers=_relay_headers())
                r.raise_for_status()
        except Exception as exc:
            app_logger.error("Failed to send logs to relay", exc=exc)
            raise HTTPException(status_code=502, detail=f"Support server unreachable: {exc}")
        app_logger.info("Log report sent via relay", username=session.username)
        return JSONResponse({"status": "sent", "via": "relay", "lines": len(recent)})

    raise HTTPException(status_code=503, detail="No support server configured. Use the Support button to connect first.")


# ── Admin — relay ─────────────────────────────────────────────────────────────

class RelayConnectRequest(BaseModel):
    url: str


@app.get("/admin/relay/status")
async def relay_status(session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    if not config.RELAY_URL:
        return JSONResponse({"relay_configured": False, "online": False, "update_available": False})
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{config.RELAY_URL}/ping")
            r.raise_for_status()
            data = r.json()
        return JSONResponse({"relay_configured": True, "online": True, **data, "saved_url": config.RELAY_URL})
    except Exception as exc:
        return JSONResponse({"relay_configured": True, "online": False, "update_available": False, "message": str(exc), "saved_url": config.RELAY_URL})


@app.post("/admin/relay/connect")
async def relay_connect(body: RelayConnectRequest, session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    import re
    url = body.url.strip().rstrip("/")
    if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url):
        raise HTTPException(status_code=422, detail="Invalid URL format.")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{url}/ping")
            r.raise_for_status()
            data = r.json()
        if not data.get("online"):
            raise ValueError("Server responded but reported offline.")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach that URL: {exc}")

    config.RELAY_URL = url
    env_path = config.BASE_DIR / ".env"
    _update_env(env_path, "RELAY_URL", url)
    app_logger.info("Relay connected", username=session.username, url=url)
    return JSONResponse({"status": "connected", "url": url, **data})


@app.post("/admin/relay/disconnect")
async def relay_disconnect(session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    config.RELAY_URL = ""
    _update_env(config.BASE_DIR / ".env", "RELAY_URL", "")
    app_logger.info("Relay disconnected", username=session.username)
    return JSONResponse({"status": "disconnected"})


# ── Admin — updates ───────────────────────────────────────────────────────────

@app.get("/admin/update/check")
async def update_check(session: auth.SessionData = Depends(auth.require_auth)) -> JSONResponse:
    if config.RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{config.RELAY_URL}/ping")
                r.raise_for_status()
                data = r.json()
            return JSONResponse({"available": data.get("update_available", False), "source": "relay", "version": data.get("version")})
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Relay offline: {exc}")
    return JSONResponse({"available": bool(config.UPDATE_URL), "source": "static", "version": None})


@app.post("/admin/update/apply")
async def update_apply(
    background_tasks: BackgroundTasks,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Download and apply a signed patch.zip from the relay or static URL."""
    url = f"{config.RELAY_URL}/update/patch" if config.RELAY_URL else config.UPDATE_URL
    if not url:
        raise HTTPException(status_code=400, detail="No update source configured.")

    patch_path = config.BASE_DIR / "patch.zip"
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(url, headers=_relay_headers() if config.RELAY_URL else {})
            r.raise_for_status()
        patch_path.write_bytes(r.content)
    except Exception as exc:
        app_logger.error("Patch download failed", exc=exc)
        raise HTTPException(status_code=502, detail=f"Could not download patch: {exc}")

    updated, skipped = [], []
    try:
        with zipfile.ZipFile(patch_path) as zf:
            for name in zf.namelist():
                dest = config.BASE_DIR / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))
                updated.append(name)
    except Exception as exc:
        app_logger.error("Patch apply failed", exc=exc)
        raise HTTPException(status_code=500, detail=f"Patch apply failed: {exc}")
    finally:
        patch_path.unlink(missing_ok=True)

    app_logger.info("Patch applied", username=session.username, files=updated)

    if updated:
        background_tasks.add_task(_restart_server)

    if config.RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                await client.post(f"{config.RELAY_URL}/update/consumed", headers=_relay_headers())
        except Exception:
            pass

    return JSONResponse({
        "status": "applied",
        "updated": updated,
        "skipped": skipped,
        "restart_scheduled": bool(updated),
        "message": f"{len(updated)} file(s) updated. Refresh in a moment." if updated else "No files were updated.",
    })


# ── Utility ───────────────────────────────────────────────────────────────────

def _update_env(env_path: Path, key: str, value: str) -> None:
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    else:
        env_path.write_text(f"{key}={value}\n", encoding="utf-8")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=config.APP_PORT, reload=False)
