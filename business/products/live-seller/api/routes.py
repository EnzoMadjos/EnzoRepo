import csv
import io
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from services.mine_service import MineService
from services.printer_service import print_mine
from services.tiktok_service import create_tiktok_task
from config import settings

router = APIRouter()


# ── TikTok ────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    username: str


@router.post("/connect")
async def connect_tiktok(req: ConnectRequest, request: Request):
    app = request.app
    if app.state.tiktok_task and not app.state.tiktok_task.done():
        raise HTTPException(400, "Already connected to a live stream")
    result = await create_tiktok_task(req.username, app.state.manager)
    if result is None:
        raise HTTPException(503, "TikTokLive library not available — check requirements")
    task, client = result
    app.state.tiktok_task = task
    app.state.tiktok_client = client
    return {"status": "connecting", "username": req.username.lstrip("@")}


@router.post("/disconnect")
async def disconnect_tiktok(request: Request):
    app = request.app
    if app.state.tiktok_client:
        try:
            await app.state.tiktok_client.disconnect()
        except Exception:
            pass
    if app.state.tiktok_task:
        app.state.tiktok_task.cancel()
    app.state.tiktok_task = None
    app.state.tiktok_client = None
    return {"status": "disconnected"}


@router.get("/status")
def get_status(request: Request):
    app = request.app
    task = app.state.tiktok_task
    tiktok_connected = task is not None and not task.done()
    return {
        "tiktok_connected": tiktok_connected,
        "session": app.state.active_session,
    }


# ── Sessions ──────────────────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    tiktok_user: str


@router.post("/sessions/start")
def start_session(req: SessionStartRequest, request: Request):
    if request.app.state.active_session:
        raise HTTPException(400, "Session already active — end it first")
    session = MineService.start_session(req.tiktok_user)
    request.app.state.active_session = session
    return session


@router.post("/sessions/end")
def end_session(request: Request):
    session = request.app.state.active_session
    if not session:
        raise HTTPException(400, "No active session")
    MineService.end_session(session["id"])
    request.app.state.active_session = None
    return {"status": "ended", "session_id": session["id"]}


@router.get("/sessions")
def list_sessions():
    return MineService.list_all_sessions()


@router.get("/sessions/{session_id}/mines")
def session_mines(session_id: int):
    return MineService.list_session_mines(session_id)


@router.get("/sessions/{session_id}/export.csv")
def export_session_csv(session_id: int):
    mines = MineService.list_session_mines(session_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Name", "Handle", "Product", "Price (PHP)", "Buyer Status", "Mine # in Session", "Time", "Printed"])
    for i, m in enumerate(reversed(mines), 1):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(m["mined_at"]))
        writer.writerow([
            i,
            m["display_name"],
            f"@{m['handle']}",
            m.get("product_name") or "",
            f"{m['price']:.2f}",
            m["status"],
            m["session_mine_count"],
            ts,
            "Yes" if m["printed"] else "No",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}.csv"'},
    )


# ── Inventory ─────────────────────────────────────────────────────────────

class ProductRequest(BaseModel):
    name: str
    price: float
    stock: int = 0


@router.get("/inventory")
def list_inventory():
    return MineService.list_all_products()


@router.get("/inventory/active")
def list_active_inventory():
    return MineService.list_active_products()


@router.post("/inventory")
def create_product(req: ProductRequest):
    if req.price <= 0:
        raise HTTPException(422, "Price must be greater than 0")
    if req.stock < 0:
        raise HTTPException(422, "Stock cannot be negative")
    return MineService.create_product(req.name.strip(), req.price, req.stock)


@router.put("/inventory/{product_id}")
def update_product(product_id: int, req: ProductRequest):
    if req.price <= 0:
        raise HTTPException(422, "Price must be greater than 0")
    if req.stock < 0:
        raise HTTPException(422, "Stock cannot be negative")
    MineService.update_product(product_id, req.name.strip(), req.price, req.stock)
    return {"status": "updated", "product_id": product_id}


@router.patch("/inventory/{product_id}/toggle")
def toggle_product(product_id: int):
    return MineService.toggle_product(product_id)


@router.delete("/inventory/{product_id}")
def delete_product(product_id: int):
    MineService.delete_product(product_id)
    return {"status": "deleted", "product_id": product_id}


# ── Mines ─────────────────────────────────────────────────────────────────

class MineRequest(BaseModel):
    tiktok_uid: str
    display_name: str
    handle: str
    price: float
    raw_comment: str = ""
    product_id: Optional[int] = None
    product_name: str = ""


@router.post("/mines")
def create_mine(req: MineRequest, request: Request):
    if req.price <= 0:
        raise HTTPException(422, "Price must be greater than 0")
    session = request.app.state.active_session
    if not session:
        raise HTTPException(400, "No active session — start a session first")

    buyer = MineService.upsert_buyer(req.tiktok_uid, req.display_name, req.handle)
    mine = MineService.create_mine(
        session["id"], buyer["id"], req.price, req.raw_comment,
        req.product_id, req.product_name,
    )

    # Decrement stock if a product was selected
    if req.product_id:
        MineService.decrement_stock(req.product_id)

    limit = settings.new_buyer_mine_limit
    flagged = buyer["status"] == "new" and mine["session_mine_count"] >= limit

    printed = print_mine(
        req.display_name, req.handle, req.price, mine["mined_at"],
        settings.printer_usb_vid, settings.printer_usb_pid,
        product_name=req.product_name,
    )
    if printed:
        MineService.mark_printed(mine["id"])
        mine["printed"] = 1

    return {**mine, "flagged": flagged, "print_ok": printed}


@router.post("/mines/{mine_id}/reprint")
def reprint_mine(mine_id: int):
    mine = MineService.get_mine(mine_id)
    if not mine:
        raise HTTPException(404, "Mine not found")
    printed = print_mine(
        mine["display_name"], mine["handle"], mine["price"], mine["mined_at"],
        settings.printer_usb_vid, settings.printer_usb_pid,
        product_name=mine.get("product_name", ""),
    )
    if printed:
        MineService.mark_printed(mine_id)
    return {"print_ok": printed}


# ── Miners (buyers) ───────────────────────────────────────────────────────

@router.get("/miners")
def list_miners():
    return MineService.list_all_buyers()


@router.post("/miners/{buyer_id}/promote")
def promote_miner(buyer_id: int):
    MineService.promote_buyer(buyer_id)
    return {"status": "promoted", "buyer_id": buyer_id}


# Legacy aliases — keep old /buyers routes alive for any cached bookmarks
@router.get("/buyers")
def list_buyers_compat():
    return MineService.list_all_buyers()


@router.post("/buyers/{buyer_id}/promote")
def promote_buyer_compat(buyer_id: int):
    MineService.promote_buyer(buyer_id)
    return {"status": "promoted", "buyer_id": buyer_id}


# ── TikTok ────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    username: str


@router.post("/connect")
async def connect_tiktok(req: ConnectRequest, request: Request):
    app = request.app
    if app.state.tiktok_task and not app.state.tiktok_task.done():
        raise HTTPException(400, "Already connected to a live stream")
    result = await create_tiktok_task(req.username, app.state.manager)
    if result is None:
        raise HTTPException(503, "TikTokLive library not available — check requirements")
    task, client = result
    app.state.tiktok_task = task
    app.state.tiktok_client = client
    return {"status": "connecting", "username": req.username.lstrip("@")}


@router.post("/disconnect")
async def disconnect_tiktok(request: Request):
    app = request.app
    if app.state.tiktok_client:
        try:
            await app.state.tiktok_client.disconnect()
        except Exception:
            pass
    if app.state.tiktok_task:
        app.state.tiktok_task.cancel()
    app.state.tiktok_task = None
    app.state.tiktok_client = None
    return {"status": "disconnected"}


@router.get("/status")
def get_status(request: Request):
    app = request.app
    task = app.state.tiktok_task
    tiktok_connected = task is not None and not task.done()
    return {
        "tiktok_connected": tiktok_connected,
        "session": app.state.active_session,
    }


# ── Sessions ──────────────────────────────────────────────────────────────

class SessionStartRequest(BaseModel):
    tiktok_user: str


@router.post("/sessions/start")
def start_session(req: SessionStartRequest, request: Request):
    if request.app.state.active_session:
        raise HTTPException(400, "Session already active — end it first")
    session = MineService.start_session(req.tiktok_user)
    request.app.state.active_session = session
    return session


@router.post("/sessions/end")
def end_session(request: Request):
    session = request.app.state.active_session
    if not session:
        raise HTTPException(400, "No active session")
    MineService.end_session(session["id"])
    request.app.state.active_session = None
    return {"status": "ended", "session_id": session["id"]}


@router.get("/sessions")
def list_sessions():
    return MineService.list_all_sessions()


@router.get("/sessions/{session_id}/mines")
def session_mines(session_id: int):
    return MineService.list_session_mines(session_id)


@router.get("/sessions/{session_id}/export.csv")
def export_session_csv(session_id: int):
    mines = MineService.list_session_mines(session_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Name", "Handle", "Price (PHP)", "Buyer Status", "Mine # in Session", "Time", "Printed"])
    for i, m in enumerate(reversed(mines), 1):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(m["mined_at"]))
        writer.writerow([
            i,
            m["display_name"],
            f"@{m['handle']}",
            f"{m['price']:.2f}",
            m["status"],
            m["session_mine_count"],
            ts,
            "Yes" if m["printed"] else "No",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}.csv"'},
    )


# ── Mines ─────────────────────────────────────────────────────────────────

class MineRequest(BaseModel):
    tiktok_uid: str
    display_name: str
    handle: str
    price: float
    raw_comment: str = ""


@router.post("/mines")
def create_mine(req: MineRequest, request: Request):
    if req.price <= 0:
        raise HTTPException(422, "Price must be greater than 0")
    session = request.app.state.active_session
    if not session:
        raise HTTPException(400, "No active session — start a session first")

    buyer = MineService.upsert_buyer(req.tiktok_uid, req.display_name, req.handle)
    mine = MineService.create_mine(session["id"], buyer["id"], req.price, req.raw_comment)

    limit = settings.new_buyer_mine_limit
    flagged = buyer["status"] == "new" and mine["session_mine_count"] >= limit

    printed = print_mine(
        req.display_name, req.handle, req.price, mine["mined_at"],
        settings.printer_usb_vid, settings.printer_usb_pid,
    )
    if printed:
        MineService.mark_printed(mine["id"])
        mine["printed"] = 1

    return {**mine, "flagged": flagged, "print_ok": printed}


@router.post("/mines/{mine_id}/reprint")
def reprint_mine(mine_id: int):
    mine = MineService.get_mine(mine_id)
    if not mine:
        raise HTTPException(404, "Mine not found")
    printed = print_mine(
        mine["display_name"], mine["handle"], mine["price"], mine["mined_at"],
        settings.printer_usb_vid, settings.printer_usb_pid,
    )
    if printed:
        MineService.mark_printed(mine_id)
    return {"print_ok": printed}


# ── Buyers ────────────────────────────────────────────────────────────────

@router.get("/buyers")
def list_buyers():
    return MineService.list_all_buyers()


@router.post("/buyers/{buyer_id}/promote")
def promote_buyer(buyer_id: int):
    MineService.promote_buyer(buyer_id)
    return {"status": "promoted", "buyer_id": buyer_id}
