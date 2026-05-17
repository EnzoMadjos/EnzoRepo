"""
Product and Session services.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from database import get_connection

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Product Service
# ------------------------------------------------------------------ #

class ProductService:
    @staticmethod
    def create(name: str, base_price: float, description: str = "") -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO products (name, base_price, description) VALUES (?, ?, ?)",
                (name, base_price, description),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def add_variant(product_id: int, label: str, price_modifier: float = 0.0, stock: int = 0, sku: str = "") -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO variants (product_id, label, price_modifier, stock, sku) VALUES (?, ?, ?, ?, ?)",
                (product_id, label, price_modifier, stock, sku),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update_stock(variant_id: int, delta: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE variants SET stock = MAX(0, stock + ?) WHERE id=?",
                (delta, variant_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_active_snapshot() -> list[dict]:
        """Returns active products + variants for the Order Brain prompt."""
        conn = get_connection()
        try:
            products = conn.execute(
                "SELECT * FROM products WHERE is_active=1 ORDER BY name"
            ).fetchall()
            result = []
            for p in products:
                variants = conn.execute(
                    "SELECT id, label, price_modifier, stock, sku FROM variants WHERE product_id=?",
                    (p["id"],),
                ).fetchall()
                result.append({
                    "id": p["id"],
                    "name": p["name"],
                    "base_price": p["base_price"],
                    "variants": [dict(v) for v in variants],
                })
            return result
        finally:
            conn.close()

    @staticmethod
    def list_all() -> list[dict]:
        conn = get_connection()
        try:
            products = conn.execute("SELECT * FROM products ORDER BY is_active DESC, name").fetchall()
            result = []
            for p in products:
                variants = conn.execute(
                    "SELECT * FROM variants WHERE product_id=?", (p["id"],)
                ).fetchall()
                d = dict(p)
                d["variants"] = [dict(v) for v in variants]
                result.append(d)
            return result
        finally:
            conn.close()

    @staticmethod
    def get(product_id: int) -> Optional[dict]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if not row:
                return None
            variants = conn.execute(
                "SELECT * FROM variants WHERE product_id=?", (product_id,)
            ).fetchall()
            d = dict(row)
            d["variants"] = [dict(v) for v in variants]
            return d
        finally:
            conn.close()

    @staticmethod
    def toggle_active(product_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE products SET is_active = 1 - is_active WHERE id=?", (product_id,)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(product_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM variants WHERE product_id=?", (product_id,))
            conn.execute("DELETE FROM products WHERE id=?", (product_id,))
            conn.commit()
        finally:
            conn.close()


# ------------------------------------------------------------------ #
# Session Service
# ------------------------------------------------------------------ #

class SessionService:
    @staticmethod
    def start(title: str = "", platform: str = "manual") -> int:
        conn = get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO sessions (title, platform) VALUES (?, ?)",
                (title or f"Session {int(time.time())}", platform),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def end(session_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE sessions SET status='ended', ended_at=? WHERE id=?",
                (int(time.time()), session_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_active() -> Optional[dict]:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE status='active' ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get(session_id: int) -> Optional[dict]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def update_totals(session_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """
                UPDATE sessions SET
                    total_orders  = (SELECT COUNT(*) FROM orders WHERE session_id=? AND status IN ('confirmed','printed')),
                    total_revenue = (SELECT COALESCE(SUM(total_price),0) FROM orders WHERE session_id=? AND status IN ('confirmed','printed'))
                WHERE id=?
                """,
                (session_id, session_id, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_stats(session_id: int) -> dict:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if not row:
                return {}
            buyers = conn.execute(
                "SELECT COUNT(DISTINCT buyer_id) as cnt FROM orders WHERE session_id=? AND status IN ('confirmed','printed')",
                (session_id,),
            ).fetchone()
            return {
                "session_id": session_id,
                "title": row["title"],
                "platform": row["platform"],
                "status": row["status"],
                "total_orders": row["total_orders"],
                "total_revenue": row["total_revenue"],
                "unique_buyers": buyers["cnt"] if buyers else 0,
                "started_at": row["started_at"],
            }
        finally:
            conn.close()
