from typing import Optional
from database import get_connection


class MineService:

    # ── Inventory ──────────────────────────────────────────────────────────

    @staticmethod
    def list_active_products() -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM products WHERE active = 1 ORDER BY name ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def list_all_products() -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM products ORDER BY name ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def create_product(name: str, price: float, stock: int) -> dict:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
                (name, price, stock),
            )
            row = conn.execute(
                "SELECT * FROM products WHERE id = last_insert_rowid()"
            ).fetchone()
            return dict(row)

    @staticmethod
    def update_product(product_id: int, name: str, price: float, stock: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
                (name, price, stock, product_id),
            )

    @staticmethod
    def toggle_product(product_id: int) -> dict:
        with get_connection() as conn:
            conn.execute(
                "UPDATE products SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (product_id,),
            )
            row = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            return dict(row)

    @staticmethod
    def delete_product(product_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    @staticmethod
    def decrement_stock(product_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE products SET stock = MAX(0, stock - 1) WHERE id = ?",
                (product_id,),
            )

    # ── Buyers ─────────────────────────────────────────────────────────────

    @staticmethod
    def upsert_buyer(tiktok_uid: str, display_name: str, handle: str) -> dict:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO buyers (tiktok_uid, display_name, handle)
                VALUES (?, ?, ?)
                ON CONFLICT(tiktok_uid) DO UPDATE SET
                    display_name = excluded.display_name,
                    handle       = excluded.handle,
                    last_seen    = unixepoch()
                """,
                (tiktok_uid, display_name, handle),
            )
            row = conn.execute(
                "SELECT * FROM buyers WHERE tiktok_uid = ?", (tiktok_uid,)
            ).fetchone()
            return dict(row)

    @staticmethod
    def list_all_buyers() -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM buyers ORDER BY last_seen DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def promote_buyer(buyer_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE buyers SET status = 'repeat' WHERE id = ?", (buyer_id,)
            )

    # ── Sessions ───────────────────────────────────────────────────────────

    @staticmethod
    def start_session(tiktok_user: str) -> dict:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (tiktok_user) VALUES (?)", (tiktok_user,)
            )
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = last_insert_rowid()"
            ).fetchone()
            return dict(row)

    @staticmethod
    def end_session(session_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET status = 'ended', ended_at = unixepoch() WHERE id = ?",
                (session_id,),
            )

    @staticmethod
    def get_active_session() -> Optional[dict]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE status = 'active' ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_all_sessions() -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Mines ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_mine(
        session_id: int, buyer_id: int, price: float, raw_comment: str,
        product_id: Optional[int] = None, product_name: str = "",
    ) -> dict:
        with get_connection() as conn:
            count_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM mines WHERE session_id = ? AND buyer_id = ?",
                (session_id, buyer_id),
            ).fetchone()
            session_mine_count = count_row["cnt"] + 1

            conn.execute(
                """
                INSERT INTO mines (session_id, buyer_id, price, session_mine_count, raw_comment, product_id, product_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, buyer_id, price, session_mine_count, raw_comment, product_id, product_name),
            )
            mine_id = conn.execute(
                "SELECT last_insert_rowid() AS id"
            ).fetchone()["id"]

            conn.execute(
                "UPDATE buyers SET total_mines = total_mines + 1, last_seen = unixepoch() WHERE id = ?",
                (buyer_id,),
            )
            conn.execute(
                "UPDATE sessions SET total_mines = total_mines + 1 WHERE id = ?",
                (session_id,),
            )

            row = conn.execute(
                """
                SELECT m.*, b.display_name, b.handle, b.status, b.total_mines
                FROM mines m JOIN buyers b ON b.id = m.buyer_id
                WHERE m.id = ?
                """,
                (mine_id,),
            ).fetchone()
            return dict(row)

    @staticmethod
    def get_mine(mine_id: int) -> Optional[dict]:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT m.*, b.display_name, b.handle, b.status
                FROM mines m JOIN buyers b ON b.id = m.buyer_id
                WHERE m.id = ?
                """,
                (mine_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def mark_printed(mine_id: int) -> None:
        with get_connection() as conn:
            conn.execute("UPDATE mines SET printed = 1 WHERE id = ?", (mine_id,))

    @staticmethod
    def list_session_mines(session_id: int) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.*, b.display_name, b.handle, b.status
                FROM mines m JOIN buyers b ON b.id = m.buyer_id
                WHERE m.session_id = ?
                ORDER BY m.mined_at DESC
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
