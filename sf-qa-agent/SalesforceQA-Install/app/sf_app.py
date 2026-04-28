"""
sf_app.py — main FastAPI application for the Salesforce QA Test Automation Agent.
"""

from __future__ import annotations

import json
from typing import Optional

import app_logger
import auth
import config
import file_parser
import llm_planner
import org_profiles
import sf_executor
from fastapi import (
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

        try:
            plan = llm_planner.plan(script_text)
        except Exception as exc:
            app_logger.error("Planning failed", exc=exc, username=session.username)
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
            "Executing test plan", username=session.username, steps=len(plan)
        )

        for event in sf_executor.execute(plan, sf_client):
            yield {"data": json.dumps(event)}

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

    return JSONResponse({"prompt": llm_planner._SYSTEM_PROMPT})


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
    llm_planner._SYSTEM_PROMPT = new_prompt
    app_logger.info(
        "System prompt updated by user",
        username=session.username,
        length=len(new_prompt),
    )
    return JSONResponse({"status": "updated", "length": len(new_prompt)})
