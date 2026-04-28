"""
relay_server.py — Enzo's on-demand support relay server.

Run this on your machine when you want to receive logs from Vanessa or push an update.
Expose it publicly using ngrok (see start_relay.sh).

Endpoints
---------
GET  /ping              → health check, returns online status + whether patch.zip is ready
POST /logs              → receives error log reports, prints them, saves to received_logs/
GET  /update/check      → alias for /ping (update_available flag)
GET  /update/patch      → serves the current patch.zip for download

All endpoints (except /ping) require the shared RELAY_TOKEN bearer token.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")
PATCH_FILE = BASE_DIR / os.getenv("PATCH_FILE", "patch.zip")
LOGS_DIR = BASE_DIR / "received_logs"
RELAY_PORT = int(os.getenv("RELAY_PORT", "9100"))
VERSION = os.getenv("APP_VERSION", "")  # optional — e.g. "1.2.0"

LOGS_DIR.mkdir(exist_ok=True)

if not RELAY_TOKEN:
    print("\n⚠  WARNING: RELAY_TOKEN is not set in relay/.env")
    print(
        "   Set a strong random token and copy it to Vanessa's .env (RELAY_TOKEN=...)\n"
    )

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="SF QA Relay", docs_url=None, redoc_url=None)
bearer = HTTPBearer(auto_error=False)


def require_token(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    if not RELAY_TOKEN:
        return  # token check disabled if not configured
    if not creds or creds.credentials != RELAY_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing relay token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── /ping — public health check ────────────────────────────────────────────────


@app.get("/ping")
async def ping() -> JSONResponse:
    """
    Public endpoint — no token required.
    Vanessa's app calls this to check if your server is reachable.
    """
    return JSONResponse(
        {
            "online": True,
            "update_available": PATCH_FILE.exists(),
            "version": VERSION or None,
            "message": "Relay online — support server is ready.",
        }
    )


# ── /update/check — alias ─────────────────────────────────────────────────────


@app.get("/update/check", dependencies=[Depends(require_token)])
async def update_check() -> JSONResponse:
    return JSONResponse(
        {
            "online": True,
            "update_available": PATCH_FILE.exists(),
            "version": VERSION or None,
        }
    )


# ── /update/patch — serve patch.zip ──────────────────────────────────────────


@app.get("/update/patch", dependencies=[Depends(require_token)])
async def update_patch() -> FileResponse:
    if not PATCH_FILE.exists():
        raise HTTPException(
            status_code=404, detail="No patch file is currently available."
        )
    return FileResponse(
        path=str(PATCH_FILE),
        media_type="application/zip",
        filename="patch.zip",
    )


# ── /update/consumed — mark patch as applied ──────────────────────────────────


@app.post("/update/consumed", dependencies=[Depends(require_token)])
async def update_consumed() -> JSONResponse:
    """Called by Vanessa's app after successfully applying the patch.
    Renames patch.zip so update_available becomes false."""
    if PATCH_FILE.exists():
        PATCH_FILE.rename(PATCH_FILE.with_suffix(".zip.applied"))
    return JSONResponse({"ok": True})


# ── /logs — receive error reports ────────────────────────────────────────────


class LogReport(BaseModel):
    username: str = "unknown"
    machine: str = "unknown"
    message: str = ""
    logs: list[dict] = []
    ts: str = ""


@app.post("/logs", dependencies=[Depends(require_token)])
async def receive_logs(report: LogReport) -> JSONResponse:
    """Receive a log report from Vanessa's app, save it, and print to console."""
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_pretty = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Print to console so Enzo sees it immediately ─────────────────────────
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  📋 LOG REPORT RECEIVED")
    print(f"  User:    {report.username}")
    print(f"  Machine: {report.machine}")
    print(f"  Time:    {ts_pretty}")
    if report.message:
        print(f"  Note:    {report.message}")
    print(sep)
    for entry in report.logs:
        lvl = entry.get("level", "").upper()
        msg = entry.get("msg", "")
        ts = entry.get("ts", "")
        tb = entry.get("traceback", "")
        print(f"  [{ts}] {lvl}: {msg}")
        if tb:
            for line in tb.strip().splitlines():
                print(f"    {line}")
    print(sep + "\n")

    # ── Save to file ──────────────────────────────────────────────────────────
    safe_user = "".join(c if c.isalnum() else "_" for c in report.username)
    out_file = LOGS_DIR / f"{ts_str}_{safe_user}.json"
    out_file.write_text(
        json.dumps(
            {
                "received_at": ts_pretty,
                "username": report.username,
                "machine": report.machine,
                "message": report.message,
                "logs": report.logs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  Saved → {out_file.name}\n")

    return JSONResponse({"status": "received", "saved": out_file.name})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SF QA Relay Server")
    print("=" * 60)
    print(f"  Listening on port : {RELAY_PORT}")
    print(
        f"  Token configured  : {'YES ✓' if RELAY_TOKEN else 'NO ✗  (set RELAY_TOKEN in .env)'}"
    )
    print(
        f"  Patch file ready  : {'YES ✓  ' + PATCH_FILE.name if PATCH_FILE.exists() else 'NO  (place patch.zip here to enable)'}"
    )
    print(f"  Log output folder : {LOGS_DIR}")
    print()
    print("  Next: run ngrok to expose this server publicly:")
    print(f"    ngrok http {RELAY_PORT}")
    print("  Then copy the https://... URL into her .env:")
    print("    RELAY_URL=https://xxxx.ngrok-free.app")
    print("=" * 60 + "\n")

    uvicorn.run("relay_server:app", host="0.0.0.0", port=RELAY_PORT, reload=False)
