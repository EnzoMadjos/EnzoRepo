"""
Action dispatcher — receives parsed comments from Order Brain,
routes them by confidence and intent to the right services.
"""
from __future__ import annotations

import logging
from typing import Optional

from config import settings
from pipeline.order_brain import ParsedComment
from services.order_service import OrderService, BuyerService
from services.product_service import ProductService, SessionService
from services.bid_service import BidService
from services.printer_service import PrinterService
from api.ws import manager

log = logging.getLogger(__name__)


def _match_product(product_hint: Optional[str], variant_hint: Optional[str], products: list[dict]):
    """
    Simple fuzzy product/variant matcher.
    Returns (product, variant) dicts or (None, None).
    """
    if not product_hint or not products:
        return None, None

    hint = product_hint.lower()
    best_product = None
    for p in products:
        if hint in p["name"].lower() or p["name"].lower() in hint:
            best_product = p
            break

    if not best_product and products:
        # Fallback: first active product if no match
        best_product = None

    if not best_product:
        return None, None

    # Match variant
    best_variant = None
    if variant_hint and best_product.get("variants"):
        vh = variant_hint.lower()
        for v in best_product["variants"]:
            if vh in v["label"].lower() or v["label"].lower() in vh:
                best_variant = v
                break
        if not best_variant and best_product["variants"]:
            best_variant = best_product["variants"][0]
    elif best_product.get("variants"):
        best_variant = best_product["variants"][0]

    return best_product, best_variant


class ActionDispatcher:
    def __init__(
        self,
        printer_service: PrinterService,
        bid_service: BidService,
        get_active_session_id,
    ) -> None:
        self._printer = printer_service
        self._bid_service = bid_service
        self._get_session_id = get_active_session_id

    async def dispatch(self, parsed: list[ParsedComment]) -> None:
        session_id = self._get_session_id()
        if not session_id:
            log.warning("No active session — dropping %d parsed comments", len(parsed))
            return

        products = ProductService.get_active_snapshot()

        for item in parsed:
            if item.intent == "ignore" or item.confidence < settings.confidence_review_threshold:
                continue

            if item.intent == "bid":
                await self._handle_bid(item, session_id)
            elif item.intent == "order":
                await self._handle_order(item, session_id, products)
            # "question" intent → log for future reply feature, skip for now

    # ------------------------------------------------------------------ #
    # Order handling
    # ------------------------------------------------------------------ #

    async def _handle_order(
        self, item: ParsedComment, session_id: int, products: list[dict]
    ) -> None:
        product, variant = _match_product(item.product_hint, item.variant_hint, products)
        if not product:
            log.info("No product match for: %s", item.raw_text)
            await manager.broadcast("comment_unmatched", {
                "text": item.raw_text,
                "confidence": item.confidence,
                "hint": item.product_hint,
            })
            return

        unit_price = product["base_price"] + (variant["price_modifier"] if variant else 0.0)

        # Upsert buyer
        buyer_id = BuyerService.upsert(
            platform="manual",
            platform_user_id=item.handle or item.buyer_name or item.raw_text[:20],
            display_name=item.buyer_name or item.handle or "Customer",
            handle=item.handle or "",
        )

        order_id = OrderService.create(
            session_id=session_id,
            buyer_id=buyer_id,
            product_id=product["id"],
            variant_id=variant["id"] if variant else None,
            qty=item.qty,
            unit_price=unit_price,
            raw_comment=item.raw_text,
            confidence=item.confidence,
        )

        order = OrderService.get(order_id)
        buyer = BuyerService.get(buyer_id)

        if item.confidence >= settings.confidence_auto_confirm:
            # Auto-confirm
            OrderService.confirm(order_id)
            SessionService.update_totals(session_id)
            BuyerService.update_stats(buyer_id, order["total_price"])
            await self._printer.enqueue_order(order, buyer)
            await manager.broadcast("order_confirmed", {**order, "auto": True})
        else:
            # Queue for seller review
            await manager.broadcast("order_pending", {**order, "auto": False})

    # ------------------------------------------------------------------ #
    # Bid handling
    # ------------------------------------------------------------------ #

    async def _handle_bid(self, item: ParsedComment, session_id: int) -> None:
        if not item.bid_amount:
            return

        active_bids = self._bid_service.get_active_bids(session_id)
        if not active_bids:
            return  # No active bid session — ignore bid comments

        # For now: apply bid to the most recently opened bid session
        # TODO: multi-bid matching by product_hint when multiple bids active
        target = active_bids[0]
        bid_session_id = target["id"]

        buyer_id = BuyerService.upsert(
            platform="manual",
            platform_user_id=item.handle or item.buyer_name or item.raw_text[:20],
            display_name=item.buyer_name or item.handle or "Bidder",
            handle=item.handle or "",
        )

        result = self._bid_service.place_bid(
            bid_session_id=bid_session_id,
            buyer_id=buyer_id,
            amount=item.bid_amount,
            raw_comment=item.raw_text,
            received_at_ms=item.received_at_ms,
        )

        if result["accepted"]:
            leaderboard = self._bid_service.get_leaderboard(bid_session_id)
            await manager.broadcast("bid_updated", {
                "bid_session_id": bid_session_id,
                "amount": item.bid_amount,
                "buyer": buyer_id,
                "leaderboard": leaderboard,
            })
        else:
            log.debug("Bid rejected for session %d: %s", bid_session_id, result.get("reason"))
