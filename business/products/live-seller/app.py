import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings, BASE_DIR
from database import init_db
from api.routes import router
from services.connection_manager import ConnectionManager
from services.mine_service import MineService

log = logging.getLogger("app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    app.state.manager = manager
    app.state.tiktok_task = None
    app.state.tiktok_client = None

    # Recover active session on restart
    recovered = MineService.get_active_session()
    app.state.active_session = recovered
    if recovered:
        log.info("♻️  Recovered active session #%d (@%s)", recovered["id"], recovered["tiktok_user"])

    log.info("✅ Mine Tracker ready — http://localhost:%d", settings.port)

    yield

    if app.state.tiktok_task:
        app.state.tiktok_task.cancel()


app = FastAPI(title="Mine Tracker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(router, prefix="/api")


# ── WebSocket ─────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── Pages ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/buyers", response_class=HTMLResponse)
async def buyers_page(request: Request):
    return templates.TemplateResponse("buyers.html", {"request": request})
