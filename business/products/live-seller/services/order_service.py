"""
Order and Buyer services — all DB writes go through here.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from database import get_connection

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Buyer Service
# ------------------------------------------------------------------ #

class BuyerService:
    @staticmethod
    def upsert(platform: str, platform_user_id: str, display_name: str, handle: str) -> int:
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO buyers (platform, platform_user_id, display_name, handle)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(platform, platform_user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    handle = excluded.handle
                """,
                (platform, platform_user_id, display_name, handle),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM buyers WHERE platform=? AND platform_user_id=?",
                (platform, platform_user_id),
            ).fetchone()
            return row["id"]
        finally:
            conn.close()

    @staticmethod
    def get(buyer_id: int) -> Optional[dict]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM buyers WHERE id=?", (buyer_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def update_stats(buyer_id: int, order_total: float) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE buyers SET
                    total_orders = total_orders + 1,
                    total_spend  = total_spend + ?,
                    is_vip = CASE WHEN total_orders + 1 >= 5 THEN 1 ELSE is_vip END
                WHERE id = ?
                """,
                (order_total, buyer_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def list_all() -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM buyers ORDER BY total_orders DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


# ------------------------------------------------------------------ #
# Order Service
# ------------------------------------------------------------------ #

class OrderService:
    @staticmethod
    def create(
        session_id: int,
        buyer_id: int,
        product_id: int,
        variant_id: Optional[int],
        qty: int,
        unit_price: float,
        raw_comment: str,
        confidence: float,
        platform_comment_id: Optional[str] = None,
    ) -> int:
        total = unit_price * qty
        conn = get_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO orders
                  (session_id, buyer_id, product_id, variant_id, qty,
                   unit_price, total_price, raw_comment, confidence, platform_comment_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, buyer_id, product_id, variant_id, qty,
                 unit_price, total, raw_comment, confidence, platform_comment_id),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def confirm(order_id: int) -> bool:
        conn = get_connection()
        try:
            # Deduct stock
            row = conn.execute(
                "SELECT product_id, variant_id, qty FROM orders WHERE id=?", (order_id,)
            ).fetchone()
            if not row:
                return False

            if row["variant_id"]:
                stock = conn.execute(
                    "SELECT stock FROM variants WHERE id=?", (row["variant_id"],)
                ).fetchone()
                if stock and stock["stock"] < row["qty"]:
                    log.warning("Insufficient stock for order %d", order_id)
                    return False
                conn.execute(
                    "UPDATE variants SET stock = stock - ? WHERE id=?",
                    (row["qty"], row["variant_id"]),
                )

            conn.execute(
                "UPDATE orders SET status='confirmed', confirmed_at=? WHERE id=?",
                (int(time.time()), order_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def cancel(order_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def mark_printed(order_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE orders SET status='printed', printed_at=? WHERE id=?",
                (int(time.time()), order_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get(order_id: int) -> Optional[dict]:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT o.*, p.name as product_name,
                       v.label as variant_label, v.price_modifier,
                       b.display_name as buyer_name, b.handle as buyer_handle
                FROM orders o
                JOIN products p ON o.product_id = p.id
                LEFT JOIN variants v ON o.variant_id = v.id
                JOIN buyers b ON o.buyer_id = b.id
                WHERE o.id = ?
                """,
                (order_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def list_by_session(session_id: int) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT o.*, p.name as product_name,
                       v.label as variant_label,
                       b.display_name as buyer_name, b.handle as buyer_handle
                FROM orders o
                JOIN products p ON o.product_id = p.id
                LEFT JOIN variants v ON o.variant_id = v.id
                JOIN buyers b ON o.buyer_id = b.id
                WHERE o.session_id = ?
                ORDER BY o.extracted_at DESC
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_recent_confirmed(session_id: int, limit: int = 5) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT o.id, p.name as product_name, v.label as variant_label,
                       o.qty, o.total_price, b.display_name as buyer_name
                FROM orders o
                JOIN products p ON o.product_id = p.id
                LEFT JOIN variants v ON o.variant_id = v.id
                JOIN buyers b ON o.buyer_id = b.id
                WHERE o.session_id = ? AND o.status IN ('confirmed', 'printed')
                ORDER BY o.confirmed_at DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
