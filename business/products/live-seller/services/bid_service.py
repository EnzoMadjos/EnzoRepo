"""
Bidding service — manages bid sessions, incoming bids, countdowns, and winner resolution.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from database import get_connection
from services.order_service import OrderService
from services.order_service import BuyerService

log = logging.getLogger(__name__)


class BidService:
    def __init__(self, ws_broadcast_fn=None) -> None:
        """ws_broadcast_fn: async callable(event_type, data) to push WS updates."""
        self._broadcast = ws_broadcast_fn
        self._timers: dict[int, asyncio.Task] = {}  # bid_session_id → countdown task

    def set_broadcast(self, fn) -> None:
        self._broadcast = fn

    # ------------------------------------------------------------------ #
    # Create / manage bid sessions
    # ------------------------------------------------------------------ #

    def open_bid(
        self,
        session_id: int,
        product_id: int,
        variant_id: Optional[int],
        starting_price: float,
        min_increment: float,
        countdown_seconds: int,
        title: str = "",
    ) -> int:
        ends_at = int(time.time()) + countdown_seconds
        conn = get_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO bid_sessions
                  (session_id, product_id, variant_id, title,
                   starting_price, min_increment, countdown_seconds, ends_at,
                   current_highest_bid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, product_id, variant_id, title,
                 starting_price, min_increment, countdown_seconds, ends_at,
                 starting_price),
            )
            conn.commit()
            bid_session_id = cur.lastrowid
        finally:
            conn.close()

        # Start countdown
        task = asyncio.create_task(self._countdown(bid_session_id, countdown_seconds))
        self._timers[bid_session_id] = task
        log.info("Bid session %d opened — %s starting ₱%.0f, %ds countdown",
                 bid_session_id, title, starting_price, countdown_seconds)
        return bid_session_id

    def close_bid_manual(self, bid_session_id: int) -> Optional[dict]:
        """Seller manually closes bid — cancel countdown, resolve winner."""
        task = self._timers.pop(bid_session_id, None)
        if task:
            task.cancel()
        return self._resolve_winner(bid_session_id)

    async def _countdown(self, bid_session_id: int, seconds: int) -> None:
        await asyncio.sleep(seconds)
        log.info("Bid session %d countdown expired", bid_session_id)
        result = self._resolve_winner(bid_session_id)
        if self._broadcast and result:
            await self._broadcast("bid_closed", result)

    # ------------------------------------------------------------------ #
    # Place a bid
    # ------------------------------------------------------------------ #

    def place_bid(
        self,
        bid_session_id: int,
        buyer_id: int,
        amount: float,
        raw_comment: str,
        received_at_ms: int,
        platform_comment_id: Optional[str] = None,
    ) -> dict:
        conn = get_connection()
        try:
            bs = conn.execute(
                "SELECT * FROM bid_sessions WHERE id=? AND status='active'",
                (bid_session_id,),
            ).fetchone()
            if not bs:
                return {"accepted": False, "reason": "bid_session_not_active"}

            current_high = bs["current_highest_bid"] or bs["starting_price"]
            min_required = current_high + bs["min_increment"]

            if amount < min_required:
                return {
                    "accepted": False,
                    "reason": f"Bid too low — minimum ₱{min_required:.0f}",
                }

            # Check for tie — first comment (lowest ms) wins
            existing_same = conn.execute(
                "SELECT id FROM bids WHERE bid_session_id=? AND amount=? ORDER BY placed_at_ms ASC LIMIT 1",
                (bid_session_id, amount),
            ).fetchone()
            if existing_same:
                return {
                    "accepted": False,
                    "reason": "Tie — first comment already registered at this amount",
                }

            # Clear previous winning flag
            conn.execute(
                "UPDATE bids SET is_winning=0 WHERE bid_session_id=?",
                (bid_session_id,),
            )
            # Insert new bid
            conn.execute(
                """
                INSERT INTO bids
                  (bid_session_id, buyer_id, amount, raw_comment,
                   placed_at_ms, is_winning, platform_comment_id)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (bid_session_id, buyer_id, amount, raw_comment, received_at_ms, platform_comment_id),
            )
            # Update bid session current high
            conn.execute(
                "UPDATE bid_sessions SET current_highest_bid=?, current_winner_buyer_id=? WHERE id=?",
                (amount, buyer_id, bid_session_id),
            )
            conn.commit()
        finally:
            conn.close()

        return {"accepted": True, "amount": amount, "buyer_id": buyer_id}

    # ------------------------------------------------------------------ #
    # Resolve winner
    # ------------------------------------------------------------------ #

    def _resolve_winner(self, bid_session_id: int) -> Optional[dict]:
        conn = get_connection()
        try:
            bs = conn.execute(
                "SELECT * FROM bid_sessions WHERE id=?", (bid_session_id,)
            ).fetchone()
            if not bs or bs["status"] != "active":
                return None

            # Get winning bid
            winning = conn.execute(
                """
                SELECT b.*, by.display_name, by.handle
                FROM bids b JOIN buyers by ON b.buyer_id = by.id
                WHERE b.bid_session_id=? AND b.is_winning=1
                LIMIT 1
                """,
                (bid_session_id,),
            ).fetchone()

            conn.execute(
                "UPDATE bid_sessions SET status='closed', closed_at=? WHERE id=?",
                (int(time.time()), bid_session_id),
            )
            conn.commit()
        finally:
            conn.close()

        if not winning:
            log.info("Bid session %d closed with no bids", bid_session_id)
            return {"bid_session_id": bid_session_id, "winner": None}

        return {
            "bid_session_id": bid_session_id,
            "winner": {
                "buyer_id": winning["buyer_id"],
                "display_name": winning["display_name"],
                "handle": winning["handle"],
                "amount": winning["amount"],
            },
        }

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def get_active_bids(self, session_id: int) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT bs.*, p.name as product_name, v.label as variant_label,
                       b.display_name as winner_name, b.handle as winner_handle
                FROM bid_sessions bs
                JOIN products p ON bs.product_id = p.id
                LEFT JOIN variants v ON bs.variant_id = v.id
                LEFT JOIN buyers b ON bs.current_winner_buyer_id = b.id
                WHERE bs.session_id=? AND bs.status='active'
                ORDER BY bs.started_at DESC
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_leaderboard(self, bid_session_id: int, limit: int = 5) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT b.amount, b.placed_at_ms, b.is_winning,
                       by.display_name, by.handle
                FROM bids b JOIN buyers by ON b.buyer_id = by.id
                WHERE b.bid_session_id=?
                ORDER BY b.amount DESC, b.placed_at_ms ASC
                LIMIT ?
                """,
                (bid_session_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
