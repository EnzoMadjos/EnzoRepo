"""
Live Seller App — main entry point.
FastAPI + Uvicorn, port 8500.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from config import settings, BASE_DIR
from database import init_db
from pipeline.clipboard import ClipboardListener
from pipeline.batch import BatchCollector
from pipeline.order_brain import OrderBrain
from pipeline.dispatcher import ActionDispatcher
from services.product_service import ProductService, SessionService
from services.order_service import OrderService
from services.bid_service import BidService
from services.printer_service import PrinterService
from api.ws import manager
from api.routes import router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    log.info("Starting Live Seller App on port %d", settings.port)
    init_db()

    # Services
    printer = PrinterService()
    bid_svc = BidService()

    # App state
    app.state.active_session_id = None
    app.state.printer_service = printer
    app.state.bid_service = bid_svc

    # Wire broadcast into bid_service for countdown expiry events
    async def broadcast_fn(event_type, data):
        await manager.broadcast(event_type, data)

    bid_svc.set_broadcast(broadcast_fn)

    # Order Brain
    brain = OrderBrain(
        products_snapshot_fn=ProductService.get_active_snapshot,
        session_orders_fn=lambda: OrderService.get_recent_confirmed(
            app.state.active_session_id or 0
        ),
    )

    # Dispatcher
    dispatcher = ActionDispatcher(
        printer_service=printer,
        bid_service=bid_svc,
        get_active_session_id=lambda: app.state.active_session_id,
    )

    # Pipeline
    comment_queue: asyncio.Queue[str] = asyncio.Queue()

    async def flush_callback(batch):
        parsed = await brain.parse_batch(batch)
        await dispatcher.dispatch(parsed)
        # Broadcast raw comments to dashboard feed
        for c in batch:
            await manager.broadcast("comment", {"text": c.text, "ts": c.received_at_ms})

    collector = BatchCollector(flush_callback=flush_callback)
    app.state.batch_collector = collector

    clipboard = ClipboardListener(comment_queue)

    async def comment_queue_drain():
        while True:
            block = await comment_queue.get()
            await collector.ingest(block)

    # Launch background tasks
    tasks = [
        asyncio.create_task(printer.start(), name="printer"),
        asyncio.create_task(collector.start_timer(), name="batch_timer"),
        asyncio.create_task(clipboard.start(), name="clipboard"),
        asyncio.create_task(comment_queue_drain(), name="queue_drain"),
    ]

    log.info("✅ Live Seller App ready — http://localhost:%d", settings.port)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    log.info("Shutting down...")
    clipboard.stop()
    collector.stop()
    printer.stop()
    for t in tasks:
        t.cancel()


app = FastAPI(title="Live Seller", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(router, prefix="/api")


# ── WebSocket ─────────────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Send current state on connect
        session_stats = None
        if app.state.active_session_id:
            session_stats = SessionService.get_stats(app.state.active_session_id)
        await ws.send_json({
            "type": "init",
            "data": {
                "session": session_stats,
                "products": ProductService.list_all(),
            },
        })
        while True:
            await ws.receive_text()  # keep alive — client sends pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── Pages ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request):
    return templates.TemplateResponse("inventory.html", {"request": request})


@app.get("/health")
def health():
    return {"status": "ok", "port": settings.port}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
