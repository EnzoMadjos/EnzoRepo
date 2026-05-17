"""
REST API routers — products, sessions, orders, bids, manual comment paste.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from services.product_service import ProductService, SessionService
from services.order_service import OrderService, BuyerService
from services.bid_service import BidService
from api.ws import manager


router = APIRouter()


# ------------------------------------------------------------------ #
# Products
# ------------------------------------------------------------------ #

class ProductCreate(BaseModel):
    name: str
    base_price: float
    description: str = ""


class VariantCreate(BaseModel):
    label: str
    price_modifier: float = 0.0
    stock: int = 0
    sku: str = ""


@router.get("/products")
def list_products():
    return ProductService.list_all()


@router.post("/products")
def create_product(body: ProductCreate):
    pid = ProductService.create(body.name, body.base_price, body.description)
    return {"id": pid}


@router.post("/products/{product_id}/variants")
def add_variant(product_id: int, body: VariantCreate):
    vid = ProductService.add_variant(product_id, body.label, body.price_modifier, body.stock, body.sku)
    return {"id": vid}


@router.patch("/products/{product_id}/toggle")
def toggle_product(product_id: int):
    ProductService.toggle_active(product_id)
    return {"ok": True}


class StockUpdate(BaseModel):
    delta: int


@router.patch("/products/variants/{variant_id}/stock")
def update_stock(variant_id: int, body: StockUpdate):
    ProductService.update_stock(variant_id, body.delta)
    return {"ok": True}


# ------------------------------------------------------------------ #
# Sessions
# ------------------------------------------------------------------ #

class SessionStart(BaseModel):
    title: str = ""
    platform: str = "manual"


@router.post("/sessions/start")
async def start_session(body: SessionStart, request: Request):
    app_state = request.app.state
    if app_state.active_session_id:
        raise HTTPException(400, "A session is already active")
    sid = SessionService.start(body.title, body.platform)
    app_state.active_session_id = sid
    await manager.broadcast("session_started", SessionService.get_stats(sid))
    return {"session_id": sid}


@router.post("/sessions/end")
async def end_session(request: Request):
    app_state = request.app.state
    sid = app_state.active_session_id
    if not sid:
        raise HTTPException(400, "No active session")
    SessionService.end(sid)
    app_state.active_session_id = None
    await manager.broadcast("session_ended", {"session_id": sid})
    return {"ok": True}


@router.get("/sessions/stats")
def session_stats(request: Request):
    sid = request.app.state.active_session_id
    if not sid:
        return {"active": False}
    return SessionService.get_stats(sid)


@router.get("/sessions/{session_id}/orders")
def session_orders(session_id: int):
    return OrderService.list_by_session(session_id)


# ------------------------------------------------------------------ #
# Orders — manual confirm / cancel
# ------------------------------------------------------------------ #

@router.post("/orders/{order_id}/confirm")
async def confirm_order(order_id: int, request: Request):
    ok = OrderService.confirm(order_id)
    if not ok:
        raise HTTPException(400, "Cannot confirm order (insufficient stock or not found)")
    order = OrderService.get(order_id)
    # Update session totals
    if request.app.state.active_session_id:
        SessionService.update_totals(request.app.state.active_session_id)
    # Enqueue print
    buyer = BuyerService.get(order["buyer_id"])
    await request.app.state.printer_service.enqueue_order(order, buyer)
    BuyerService.update_stats(order["buyer_id"], order["total_price"])
    await manager.broadcast("order_confirmed", order)
    return {"ok": True}


@router.post("/orders/{order_id}/cancel")
async def cancel_order(order_id: int):
    OrderService.cancel(order_id)
    await manager.broadcast("order_cancelled", {"order_id": order_id})
    return {"ok": True}


# ------------------------------------------------------------------ #
# Manual comment paste (fallback if clipboard listener is disabled)
# ------------------------------------------------------------------ #

class PasteComments(BaseModel):
    text: str


@router.post("/comments/paste")
async def paste_comments(body: PasteComments, request: Request):
    if not request.app.state.active_session_id:
        raise HTTPException(400, "Start a session first")
    await request.app.state.batch_collector.ingest(body.text)
    return {"ok": True, "chars": len(body.text)}


# ------------------------------------------------------------------ #
# Bidding
# ------------------------------------------------------------------ #

class BidOpen(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    starting_price: float
    min_increment: float
    countdown_seconds: int
    title: str = ""


@router.post("/bids/open")
async def open_bid(body: BidOpen, request: Request):
    sid = request.app.state.active_session_id
    if not sid:
        raise HTTPException(400, "Start a session first")
    bid_id = request.app.state.bid_service.open_bid(
        sid, body.product_id, body.variant_id,
        body.starting_price, body.min_increment,
        body.countdown_seconds, body.title,
    )
    await manager.broadcast("bid_opened", {
        "bid_session_id": bid_id, "title": body.title,
        "starting_price": body.starting_price,
        "countdown_seconds": body.countdown_seconds,
    })
    return {"bid_session_id": bid_id}


@router.post("/bids/{bid_session_id}/close")
async def close_bid(bid_session_id: int, request: Request):
    result = request.app.state.bid_service.close_bid_manual(bid_session_id)
    if not result:
        raise HTTPException(404, "Bid session not found or already closed")
    await manager.broadcast("bid_closed", result)
    return result


@router.get("/bids/active")
def active_bids(request: Request):
    sid = request.app.state.active_session_id
    if not sid:
        return []
    return request.app.state.bid_service.get_active_bids(sid)


@router.get("/bids/{bid_session_id}/leaderboard")
def bid_leaderboard(bid_session_id: int, request: Request):
    return request.app.state.bid_service.get_leaderboard(bid_session_id)


# ------------------------------------------------------------------ #
# Buyers
# ------------------------------------------------------------------ #

@router.get("/buyers")
def list_buyers():
    return BuyerService.list_all()
