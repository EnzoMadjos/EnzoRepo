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

import json
import mimetypes
import os
import platform
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import app_logger
import auth
import config
import discovery
import httpx
import patch_signing
import utils
from api.attachments import router as attachments_router
from api.certificate_types import router as certificate_types_router
from api.feedback import router as feedback_router
from api.certificates import router as certificates_router
from api.dashboard import router as dashboard_router
from api.households import router as households_router
from api.residents import router as residents_router
from api.users import router as users_router
from fastapi import (
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# ── App init ──────────────────────────────────────────────────────────────────

app = FastAPI(title=config.APP_NAME, docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))

_static_dir = config.BASE_DIR / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ── Discovery state (set at startup) ─────────────────────────────────────────

_server_role: str = "unknown"  # "leader" | "client"
_leader_addr: Optional[tuple] = None


@app.on_event("startup")
async def _startup() -> None:
    global _server_role, _leader_addr

    # Ensure all tables exist first (handles fresh DB where init migration is a no-op)
    try:
        from db import engine
        from models import Base
        Base.metadata.create_all(engine)
        app_logger.info("Database tables ensured via create_all")
    except Exception as exc:
        app_logger.warn(f"create_all failed (non-fatal): {exc}")

    # Run database migrations automatically on startup
    try:
        from alembic import command
        from alembic.config import Config as AlembicConfig
        alembic_cfg = AlembicConfig(str(config.BASE_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(config.BASE_DIR / "alembic"))
        command.upgrade(alembic_cfg, "head")
        app_logger.info("Database migrations applied (alembic upgrade head)")
    except Exception as exc:
        app_logger.warn(f"Migration check failed (non-fatal): {exc}")

    # Seed default cert types if none exist
    try:
        from db import SessionLocal
        from models import CertificateType
        import uuid as _uuid
        _defaults = [
            ("BCL", "Barangay Clearance",           "barangay_clearance.html"),
            ("COR", "Certificate of Residency",     "certofresidency.html"),
            ("COI", "Certificate of Indigency",     "indigency.html"),
            ("BUS", "Business Clearance",           "business_clearance.html"),
            ("COH", "Cohabitation Certificate",     "cohabitation.html"),
            ("SSS", "SSS Membership Certificate",   "sss_membership.html"),
            ("SAM", "Same Person Certificate",      "same_person.html"),
            ("CON", "Construction Clearance",       "constructionclearance.html"),
            ("NFH", "No Flood History",             "no_flood_history.html"),
        ]
        _db = SessionLocal()
        try:
            if _db.query(CertificateType).count() == 0:
                for _code, _name, _tpl in _defaults:
                    _db.add(CertificateType(id=str(_uuid.uuid4()), code=_code, name=_name, template=_tpl))
                _db.commit()
                app_logger.info("Seeded default certificate types")
        finally:
            _db.close()
    except Exception as exc:
        app_logger.warn(f"Cert type seed failed (non-fatal): {exc}")

    def on_elected():
        global _server_role
        _server_role = "leader"
        app_logger.info("This instance is the LEADER (backend server for LAN)")

    def on_client(addr: tuple):
        global _server_role, _leader_addr
        _server_role = "client"
        _leader_addr = addr
        app_logger.info(
            "This instance is a CLIENT", leader_host=addr[0], leader_port=addr[1]
        )

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


# Register API routers
app.include_router(residents_router)
app.include_router(certificate_types_router)
app.include_router(certificates_router)
app.include_router(dashboard_router)
app.include_router(households_router)
app.include_router(attachments_router)
app.include_router(users_router)
app.include_router(feedback_router)


@app.get("/ui/dashboard", response_class=HTMLResponse)
async def ui_dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/dashboard.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/certificates", response_class=HTMLResponse)
async def ui_certificates(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/certificates.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/residents", response_class=HTMLResponse)
async def ui_residents(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/residents.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/households", response_class=HTMLResponse)
async def ui_households(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/households.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/certificate_preview", response_class=HTMLResponse)
async def ui_certificate_preview(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/certificate_preview.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/issue", response_class=HTMLResponse)
async def ui_issue(request: Request) -> HTMLResponse:
    """Simple issuance form: select resident and certificate type, preview and generate."""
    return templates.TemplateResponse(
        "ui/issue_certificate.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/users", response_class=HTMLResponse)
async def ui_users(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/users.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/account", response_class=HTMLResponse)
async def ui_account(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/account.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/audit", response_class=HTMLResponse)
async def ui_audit(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/audit.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/certificate-types", response_class=HTMLResponse)
async def ui_certificate_types(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/certificate_types.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/demo", response_class=HTMLResponse)
async def demo_landing(request: Request) -> HTMLResponse:
    """Public demo landing page — no login required."""
    return templates.TemplateResponse(
        "demo.html", {"request": request, "app_name": config.APP_NAME}
    )


@app.get("/ui/feedback", response_class=HTMLResponse)
async def ui_feedback(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "ui/feedback.html", {"request": request, "app_name": config.APP_NAME}
    )


class ArchiveRequest(BaseModel):
    q: Optional[str] = None
    level: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    format: str = "zip"
    clear_after: bool = False


class ImportTemplatesRequest(BaseModel):
    convert: bool = False
    inject: bool = False
    dry_run: bool = True


class ApplyTemplatesRequest(BaseModel):
    files: list[str] | None = None
    apply_all: bool = False
    convert: bool = False


class UndoTemplatesRequest(BaseModel):
    files: list[str] | None = None
    undo_all: bool = False


@app.post("/admin/logs/archive")
async def archive_logs(
    q: Optional[str] = None,
    level: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    format: str = "zip",
    clear_after: bool = False,
    body: Optional[ArchiveRequest] = Body(None),
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Archive logs into `config.LOG_ARCHIVE_DIR` and return a download URL.

    Accepts JSON body with fields: `q`, `level`, `start`, `end`, `format`, `clear_after`.
    Falls back to query params when body omitted for backward compatibility.
    """

    # prefer JSON body when provided (UI posts JSON). Keep query-param fallback.

    entries = app_logger.get_recent(10000)

    def parse_ts(s: Optional[str]):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
        return None

    # effective params: prefer body values, else use query params
    req_q = body.q if body and body.q is not None else q
    req_level = body.level if body and body.level is not None else level
    req_start = body.start if body and body.start is not None else start
    req_end = body.end if body and body.end is not None else end
    req_format = body.format if body and body.format is not None else format
    req_clear_after = (
        body.clear_after if body and body.clear_after is not None else clear_after
    )

    start_dt = parse_ts(req_start)
    end_dt = parse_ts(req_end)

    q_lower = req_q.lower() if req_q else None
    filtered = []
    for e in entries:
        ets = None
        try:
            ets = datetime.fromisoformat(e.get("ts")) if e.get("ts") else None
        except Exception:
            ets = None
        if start_dt and ets and ets < start_dt:
            continue
        if end_dt and ets and ets > end_dt:
            continue
        if req_level and e.get("level", "").upper() != req_level.upper():
            continue
        if q_lower:
            if not (
                (e.get("msg") and q_lower in str(e.get("msg")).lower())
                or q_lower in json.dumps(e).lower()
            ):
                continue
        filtered.append(e)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base_name = f"pitogo_logs_{timestamp}"
    LOG_ARCHIVE_DIR = config.LOG_ARCHIVE_DIR
    if req_format == "json":
        filename = f"{base_name}.json"
        out_path = LOG_ARCHIVE_DIR / filename
        out_path.write_text(json.dumps(filtered, ensure_ascii=False), encoding="utf-8")
    elif req_format == "csv":
        import csv
        import io

        filename = f"{base_name}.csv"
        out_path = LOG_ARCHIVE_DIR / filename
        sio = io.StringIO()
        writer = csv.writer(sio)
        writer.writerow(["ts", "level", "msg", "extra"])
        for it in filtered:
            extra = (
                it.get("extra")
                if isinstance(it.get("extra"), (dict, list))
                else {k: v for k, v in it.items() if k not in ("ts", "level", "msg")}
            )
            writer.writerow(
                [
                    it.get("ts", ""),
                    it.get("level", ""),
                    it.get("msg", ""),
                    json.dumps(extra, ensure_ascii=False),
                ]
            )
        out_path.write_text(sio.getvalue(), encoding="utf-8")
    else:
        # zip default
        import csv
        import io
        import zipfile

        filename = f"{base_name}.zip"
        out_path = LOG_ARCHIVE_DIR / filename
        # create a zip containing a CSV of logs
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            sio = io.StringIO()
            writer = csv.writer(sio)
            writer.writerow(["ts", "level", "msg", "extra"])
            for it in filtered:
                extra = (
                    it.get("extra")
                    if isinstance(it.get("extra"), (dict, list))
                    else {
                        k: v for k, v in it.items() if k not in ("ts", "level", "msg")
                    }
                )
                writer.writerow(
                    [
                        it.get("ts", ""),
                        it.get("level", ""),
                        it.get("msg", ""),
                        json.dumps(extra, ensure_ascii=False),
                    ]
                )
            zf.writestr(f"{base_name}.csv", sio.getvalue())

    # optionally clear live logs
    if req_clear_after:
        try:
            app_logger.clear_logs()
            app_logger.info(
                "Logs archived and cleared",
                username=session.username,
                archive=str(out_path),
            )
        except Exception:
            pass

    download_url = f"/admin/archives/{out_path.name}"
    return JSONResponse({"archive": str(out_path), "download_url": download_url})


@app.get("/admin/archives/{filename}")
async def serve_archive(
    filename: str, session: auth.SessionData = Depends(auth.require_auth)
):
    target = config.LOG_ARCHIVE_DIR / filename
    try:
        target_resolved = target.resolve()
        root = config.LOG_ARCHIVE_DIR.resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="not found")
    if not str(target_resolved).startswith(str(root)):
        raise HTTPException(status_code=403, detail="access denied")
    if not target_resolved.exists():
        raise HTTPException(status_code=404, detail="not found")
    mime = mimetypes.guess_type(str(target_resolved))[0] or "application/octet-stream"
    return FileResponse(
        path=str(target_resolved), media_type=mime, filename=target_resolved.name
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _relay_headers() -> dict:
    return (
        {"Authorization": f"Bearer {config.RELAY_TOKEN}"} if config.RELAY_TOKEN else {}
    )


def _restart_server() -> None:
    time.sleep(1.5)
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ── UI ────────────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html", {"request": request, "app_name": config.APP_NAME}
    )


# ── Auth ──────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class ArchiveRequest(BaseModel):
    q: Optional[str] = None
    level: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    format: str = "zip"
    clear_after: bool = False


@app.post("/auth/login")
async def login(body: LoginRequest) -> JSONResponse:
    user = auth.verify_user(body.username, body.password)
    if not user:
        app_logger.warn("Failed login attempt", username=body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = auth.create_session(
        body.username, user["role"], user.get("display_name", body.username)
    )
    app_logger.info("Login", username=body.username, role=user["role"])
    return JSONResponse(
        {
            "token": token,
            "username": body.username,
            "role": user["role"],
            "display_name": user.get("display_name", body.username),
        }
    )


@app.post("/auth/logout")
async def logout(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
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
    return JSONResponse(
        {
            "role": _server_role,
            "leader_addr": list(_leader_addr) if _leader_addr else None,
            "hostname": hostname,
            "local_ip": local_ip,
            "port": config.APP_PORT,
        }
    )


@app.get("/download/{token}")
async def download_signed(token: str):
    """Serve a signed short-lived download token without requiring auth.

    Token verification is HMAC-based and uses `config.DOWNLOAD_SECRET`.
    """
    try:
        payload = utils.verify_signed_token(token)
    except Exception:
        raise HTTPException(status_code=404, detail="invalid or expired token")

    rel_path = payload.get("path")
    if not rel_path:
        raise HTTPException(status_code=404, detail="invalid token payload")

    target = config.SECURE_DIR / Path(rel_path)
    try:
        target_resolved = target.resolve()
        secure_root = config.SECURE_DIR.resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="file not found")

    if not str(target_resolved).startswith(str(secure_root)):
        raise HTTPException(status_code=403, detail="access denied")
    if not target_resolved.exists():
        raise HTTPException(status_code=404, detail="file not found")

    mime = mimetypes.guess_type(str(target_resolved))[0] or "application/octet-stream"
    return FileResponse(
        path=str(target_resolved), media_type=mime, filename=target_resolved.name
    )


@app.post("/admin/templates/import")
async def import_templates_endpoint(
    body: ImportTemplatesRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Run the DOCX -> HTML importer and optional placeholder injector.

    - `convert`: run the DOCX converter (uses `tools/import_templates.py`)
    - `inject`: run the placeholder injector (uses `tools/auto_inject_placeholders.py`)
    - `dry_run`: when true, only report what would be done
    """
    root = config.BASE_DIR
    src = root / "templates" / "docs" / "source_documents"
    dst = root / "templates" / "certs"
    docx_files = sorted([p.name for p in src.glob("*.docx")]) if src.exists() else []
    cert_files = sorted([p.name for p in dst.glob("*.html")]) if dst.exists() else []

    result = {
        "docx_count": len(docx_files),
        "docx_files": docx_files,
        "cert_count": len(cert_files),
        "certs": cert_files,
        "actions": [],
    }

    if body.dry_run:
        # simulate placeholder injection if requested
        if body.inject:
            try:
                import tools.auto_inject_placeholders as injector

                simulated = []
                for p in sorted(dst.glob("*.html")):
                    res = injector.simulate_inject_into_file(p)
                    if res.get("patched"):
                        # include up to first 3 replacements as preview
                        simulated.append(
                            {
                                "file": p.name,
                                "replacements": res.get("replacements")[:3],
                            }
                        )
                result["simulated_changes"] = simulated
            except Exception as exc:
                app_logger.error(
                    "Placeholder simulation failed", exc=exc, username=session.username
                )
                raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")
        result["actions"].append("dry_run")
        return JSONResponse(result)

    # perform actions
    if body.convert:
        try:
            import tools.import_templates as importer

            importer.main()
            result["actions"].append("converted_docx")
            app_logger.info(
                "Templates converted", username=session.username, count=len(docx_files)
            )
        except Exception as exc:
            app_logger.error(
                "Template conversion failed", exc=exc, username=session.username
            )
            raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")

    if body.inject:
        try:
            import tools.auto_inject_placeholders as injector

            injector.main()
            result["actions"].append("injected_placeholders")
            app_logger.info(
                "Placeholder injection completed",
                username=session.username,
                count=len(cert_files),
            )
        except Exception as exc:
            app_logger.error(
                "Placeholder injection failed", exc=exc, username=session.username
            )
            raise HTTPException(status_code=500, detail=f"Injection failed: {exc}")

    return JSONResponse(result)


@app.post("/admin/templates/apply")
async def apply_templates_endpoint(
    body: ApplyTemplatesRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Apply placeholder injection to specified files or all files.

    - `files`: list of filenames under `templates/certs/` to process.
    - `apply_all`: when true, process all cert HTML files.
    - `convert`: when true, run the DOCX->HTML converter first.
    """
    root = config.BASE_DIR
    src = root / "templates" / "docs" / "source_documents"
    dst = root / "templates" / "certs"

    result = {"requested": body.dict(), "patched": [], "skipped": [], "errors": {}}

    if body.convert:
        try:
            import tools.import_templates as importer

            importer.main()
            app_logger.info("Templates converted (apply)", username=session.username)
        except Exception as exc:
            app_logger.error(
                "Conversion (apply) failed", exc=exc, username=session.username
            )
            raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")

    try:
        import tools.auto_inject_placeholders as injector
    except Exception as exc:
        app_logger.error("Injector import failed", exc=exc, username=session.username)
        raise HTTPException(status_code=500, detail=f"Injector unavailable: {exc}")

    targets = []
    if body.apply_all:
        targets = sorted(dst.glob("*.html"))
    elif body.files:
        for fn in body.files:
            p = dst / fn
            targets.append(p)
    else:
        raise HTTPException(
            status_code=400, detail="No files specified and apply_all is false"
        )

    for p in targets:
        try:
            if not p.exists():
                result["skipped"].append(str(p.name))
                continue
            ok = injector.inject_into_file(p)
            if ok:
                result["patched"].append(str(p.name))
            else:
                result["skipped"].append(str(p.name))
        except Exception as exc:
            result["errors"][str(p.name)] = str(exc)

    app_logger.info(
        "Apply templates completed",
        username=session.username,
        patched=result["patched"],
    )
    return JSONResponse(result)


@app.post("/admin/templates/undo")
async def undo_templates_endpoint(
    body: UndoTemplatesRequest,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Restore `.bak` backups for specified files or all files.

    - `files`: list of filenames under `templates/certs/` to restore.
    - `undo_all`: when true, restore all `*.html.bak` backups.
    Restores content from `file.html.bak` -> `file.html` and removes the `.bak` file.
    """
    root = config.BASE_DIR
    dst = root / "templates" / "certs"

    result = {"requested": body.dict(), "restored": [], "skipped": [], "errors": {}}

    targets = []
    if body.undo_all:
        targets = sorted(dst.glob("*.html.bak"))
    elif body.files:
        for fn in body.files:
            p = dst / fn
            targets.append(p.with_suffix(p.suffix + ".bak"))
    else:
        raise HTTPException(
            status_code=400, detail="No files specified and undo_all is false"
        )

    for bak in targets:
        try:
            if not bak.exists():
                result["skipped"].append(str(bak.name))
                continue
            orig_path = (
                Path(str(bak)[:-4])
                if str(bak).endswith(".bak")
                else bak.with_suffix("")
            )
            data = bak.read_text(encoding="utf-8")
            orig_path.write_text(data, encoding="utf-8")
            try:
                bak.unlink()
            except Exception:
                pass
            result["restored"].append(str(orig_path.name))
        except Exception as exc:
            result["errors"][str(bak.name)] = str(exc)

    app_logger.info(
        "Undo templates completed",
        username=session.username,
        restored=result["restored"],
    )
    return JSONResponse(result)


# ── Document printing ─────────────────────────────────────────────────────────


class DocumentRequest(BaseModel):
    doc_type: str  # "clearance" | "residency" | "indigency"
    full_name: str
    address: str
    purpose: str
    extra: dict = {}  # any additional fields per doc type


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
        raise HTTPException(
            status_code=400, detail=f"doc_type must be one of: {allowed}"
        )

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
async def get_logs(
    n: int = 200,
    q: Optional[str] = None,
    level: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    page: int = 1,
    per_page: int = 200,
    format: Optional[str] = None,
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    """Return recent logs with server-side filtering, pagination, and optional CSV export.

    Query params:
      - q: text search across message and fields
      - level: log level filter (INFO, WARNING, ERROR)
      - start / end: ISO timestamps to filter range (e.g. 2026-04-28T07:00:00)
      - page / per_page: pagination
      - format=csv: return a CSV attachment
    """
    # read generous number of recent entries for filtering
    raw = app_logger.get_recent(max(n, 1000))
    entries = list(raw)

    def parse_ts(s: Optional[str]):
        if not s:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    start_dt = parse_ts(start)
    end_dt = parse_ts(end)

    q_lower = q.lower() if q else None
    filtered = []
    for e in entries:
        # parse entry timestamp
        ets = None
        try:
            ets = datetime.fromisoformat(e.get("ts")) if e.get("ts") else None
        except Exception:
            ets = None
        if start_dt and ets and ets < start_dt:
            continue
        if end_dt and ets and ets > end_dt:
            continue
        if level and e.get("level", "").upper() != level.upper():
            continue
        if q_lower:
            # search in message and JSON representation
            if not (
                (e.get("msg") and q_lower in str(e.get("msg")).lower())
                or q_lower in json.dumps(e).lower()
            ):
                continue
        filtered.append(e)

    total = len(filtered)
    per_page = max(1, min(per_page or 200, 1000))
    page = max(1, page or 1)
    start_i = (page - 1) * per_page
    items = filtered[start_i : start_i + per_page]

    if format and format.lower() == "csv":
        import csv
        import io

        sio = io.StringIO()
        writer = csv.writer(sio)
        writer.writerow(["ts", "level", "msg", "extra"])
        for it in items:
            extra = (
                it.get("extra")
                if isinstance(it.get("extra"), (dict, list))
                else {k: v for k, v in it.items() if k not in ("ts", "level", "msg")}
            )
            writer.writerow(
                [
                    it.get("ts", ""),
                    it.get("level", ""),
                    it.get("msg", ""),
                    json.dumps(extra, ensure_ascii=False),
                ]
            )
        text = sio.getvalue()
        from fastapi.responses import Response

        fn = f"pitogo_logs_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
        return Response(
            content=text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{fn}"'},
        )

    return JSONResponse(
        {"items": items, "page": page, "per_page": per_page, "total": total}
    )


@app.delete("/admin/logs")
async def clear_logs(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
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
        "machine": platform.node(),
        "message": body.message,
        "logs": recent,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    if config.RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{config.RELAY_URL}/logs", json=payload, headers=_relay_headers()
                )
                r.raise_for_status()
        except Exception as exc:
            app_logger.error("Failed to send logs to relay", exc=exc)
            raise HTTPException(
                status_code=502, detail=f"Support server unreachable: {exc}"
            )
        app_logger.info("Log report sent via relay", username=session.username)
        return JSONResponse({"status": "sent", "via": "relay", "lines": len(recent)})

    raise HTTPException(
        status_code=503,
        detail="No support server configured. Use the Support button to connect first.",
    )


# ── Admin — relay ─────────────────────────────────────────────────────────────


class RelayConnectRequest(BaseModel):
    url: str


@app.get("/admin/relay/status")
async def relay_status(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    if not config.RELAY_URL:
        return JSONResponse(
            {"relay_configured": False, "online": False, "update_available": False}
        )
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{config.RELAY_URL}/ping")
            r.raise_for_status()
            data = r.json()
        return JSONResponse(
            {
                "relay_configured": True,
                "online": True,
                **data,
                "saved_url": config.RELAY_URL,
            }
        )
    except Exception as exc:
        return JSONResponse(
            {
                "relay_configured": True,
                "online": False,
                "update_available": False,
                "message": str(exc),
                "saved_url": config.RELAY_URL,
            }
        )


@app.post("/admin/relay/connect")
async def relay_connect(
    body: RelayConnectRequest, session: auth.SessionData = Depends(auth.require_auth)
) -> JSONResponse:
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
async def relay_disconnect(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    config.RELAY_URL = ""
    _update_env(config.BASE_DIR / ".env", "RELAY_URL", "")
    app_logger.info("Relay disconnected", username=session.username)
    return JSONResponse({"status": "disconnected"})


# ── Admin — updates ───────────────────────────────────────────────────────────


@app.get("/admin/update/check")
async def update_check(
    session: auth.SessionData = Depends(auth.require_auth),
) -> JSONResponse:
    if config.RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{config.RELAY_URL}/ping")
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
        {"available": bool(config.UPDATE_URL), "source": "static", "version": None}
    )


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
            r = await client.get(
                url, headers=_relay_headers() if config.RELAY_URL else {}
            )
            r.raise_for_status()
        patch_path.write_bytes(r.content)
    except Exception as exc:
        app_logger.error("Patch download failed", exc=exc)
        raise HTTPException(status_code=502, detail=f"Could not download patch: {exc}")

    # Download signature and verify (expecting URL + ".sig")
    sig_path = config.BASE_DIR / "patch.zip.sig"
    sig_ok = False
    try:
        sig_url = url + ".sig"
        async with httpx.AsyncClient(timeout=10) as client:
            r2 = await client.get(
                sig_url, headers=_relay_headers() if config.RELAY_URL else {}
            )
            if r2.status_code == 200 and r2.content:
                sig_path.write_bytes(r2.content)
                sig_ok = patch_signing.verify_signature(
                    patch_path.read_bytes(), r2.content
                )
    except Exception:
        sig_ok = False

    if not sig_ok:
        patch_path.unlink(missing_ok=True)
        if sig_path.exists():
            sig_path.unlink(missing_ok=True)
        app_logger.error(
            "Patch signature verification failed or missing", username=session.username
        )
        raise HTTPException(
            status_code=400, detail="Patch signature missing or verification failed."
        )

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
        if sig_path.exists():
            sig_path.unlink(missing_ok=True)

    app_logger.info("Patch applied", username=session.username, files=updated)

    if updated:
        background_tasks.add_task(_restart_server)

    if config.RELAY_URL:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                await client.post(
                    f"{config.RELAY_URL}/update/consumed", headers=_relay_headers()
                )
        except Exception:
            pass

    return JSONResponse(
        {
            "status": "applied",
            "updated": updated,
            "skipped": skipped,
            "restart_scheduled": bool(updated),
            "message": (
                f"{len(updated)} file(s) updated. Refresh in a moment."
                if updated
                else "No files were updated."
            ),
        }
    )


# ── Demo preview (dev-only) ─────────────────────────────────────────────────
@app.get("/demo/preview")
async def demo_preview(doc: str = "clearance") -> HTMLResponse:
    """Render a sample document for UI/UX preview without auth (development convenience)."""
    allowed = {"clearance", "residency", "indigency"}
    if doc not in allowed:
        raise HTTPException(status_code=400, detail=f"doc must be one of: {allowed}")
    sample = {
        "full_name": "Juan Dela Cruz",
        "address": "Purok 1, Brgy. Pitogo",
        "purpose": "For employment verification",
        "extra": {"years": "5"},
        "issued_by": "Punong Barangay Maria Santos",
        "issued_at": time.strftime("%B %d, %Y"),
    }
    template_name = f"docs/{doc}.html"
    try:
        rendered = templates.get_template(template_name).render(**sample)
    except Exception as exc:
        app_logger.error("Demo render error", exc=exc, doc=doc)
        raise HTTPException(status_code=500, detail=str(exc))
    return HTMLResponse(rendered)


# ── Design preview (server-rendered UI-only) ─────────────────────────────────
@app.get("/design", response_class=HTMLResponse)
async def design_page(request: Request) -> HTMLResponse:
    """Render the main UI shell server-side for visual review (no auth required)."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": config.APP_NAME, "demo_show_app": True},
    )


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
