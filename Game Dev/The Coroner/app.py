"""
The Coroner: Inquest — FastAPI application entry point.
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, warm up models, verify connectivity."""
    logger.info("Starting The Coroner: Inquest...")
    init_db()
    logger.info("Database initialised (WAL mode, all tables created).")

    # Warm-up checks run with tight timeout so they never block startup.
    # Ollama cold-loads the model into VRAM; this can take 20-30s — we fire it
    # as a background task so the server is ready for requests immediately.
    async def _warmup():
        import asyncio as _asyncio
        try:
            from llm.ollama_client import smoke_test as ollama_check
            ok = await _asyncio.wait_for(ollama_check(), timeout=45)
            if ok:
                logger.info(f"Ollama ({config.OLLAMA_MODEL}) — ready.")
            else:
                logger.warning(f"Ollama ({config.OLLAMA_MODEL}) — warm-up failed. Interviews may be slow on first call.")
        except Exception as e:
            logger.warning(f"Ollama warm-up: {e}")

        try:
            from llm.github_client import smoke_test as github_check
            ok = await _asyncio.wait_for(github_check(), timeout=15)
            if ok:
                logger.info(f"GitHub Models API ({config.GITHUB_MODEL}) — ready.")
            else:
                logger.warning("GitHub Models API not responding. Case generation may fail.")
        except Exception as e:
            logger.warning(f"GitHub Models API: {e}")

    import asyncio
    asyncio.create_task(_warmup())

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="The Coroner: Inquest",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/dev/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SESSION_COOKIE = "coroner_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def get_or_create_session(request: Request, response: Response) -> str:
    """Return existing session token from cookie, or create a new one."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        token = uuid.uuid4().hex
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
    return token


# ── Register API routers (added as phases are built) ──────────────────────
from api import case as case_router
from api import witness as witness_router
from api import evidence as evidence_router
from api import board as board_router
from api import consult as consult_router
from api import report as report_router

app.include_router(case_router.router)
app.include_router(witness_router.router)
app.include_router(evidence_router.router)
app.include_router(board_router.router)
app.include_router(consult_router.router)
app.include_router(report_router.router)


# ── Root route ─────────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request, response: Response):
    token = get_or_create_session(request, response)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "session_token": token},
    )


@app.get("/cases")
async def cases_page(request: Request, response: Response):
    """All past inquests list."""
    from database import get_db
    from models import Case, Report
    db = next(get_db())
    try:
        cases = db.query(Case).filter(Case.is_active == True).order_by(Case.id.desc()).all()
        import json
        case_list = []
        for c in cases:
            sk = json.loads(c.world_skeleton or "{}")
            core = sk.get("core", {})
            victim_name = core.get("victim", {}).get("name", "Unknown")
            case_title = core.get("case_title", f"Case #{c.id}")
            report = db.query(Report).filter(Report.case_id == c.id).first()
            score = None
            verdict = None
            if report:
                result = json.loads(report.result_json or "{}")
                score = result.get("score")
                verdict = result.get("verdict")
            case_list.append({
                "id": c.id,
                "title": case_title,
                "victim": victim_name,
                "is_closed": c.is_closed,
                "score": score,
                "verdict": verdict,
            })
    finally:
        db.close()
    return templates.TemplateResponse(
        "cases.html",
        {"request": request, "cases": case_list},
    )


@app.get("/case/{case_id}")
async def case_page(case_id: int, request: Request, response: Response):
    """Case investigation page — Phase 4 will flesh out the template."""
    token = get_or_create_session(request, response)
    return templates.TemplateResponse(
        "case.html",
        {"request": request, "case_id": case_id, "session_token": token},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "app": "The Coroner: Inquest"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=config.APP_PORT, reload=True)
