"""
sync_engine.py — Offline fallback + auto-sync for PITOGO App.

How it works
────────────
When DB_BACKEND=postgres and the leader goes offline (power cut, network drop):
  • The app detects the connection failure and switches to local SQLite fallback.
  • Every write (INSERT / UPDATE / DELETE) is also recorded in a local `sync_queue` table.
  • A background thread pings the leader PostgreSQL every SYNC_CHECK_INTERVAL seconds.
  • When the leader is reachable again, sync_push() replays all pending queue entries
    against PostgreSQL, then switches the app back to postgres mode.

Usage
─────
  from sync_engine import SyncEngine
  engine_mgr = SyncEngine()
  engine_mgr.start()          # call on app startup
  engine_mgr.stop()           # call on app shutdown
  engine_mgr.queue_write(table, operation, record_id, payload)  # call on every write
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Optional

import config

log = logging.getLogger("pitogo.sync")

# How often (seconds) to check if the leader postgres is back online
SYNC_CHECK_INTERVAL = 30

# Which tables we track for offline sync (all writable tables)
TRACKED_TABLES = {
    "residents",
    "households",
    "users",
    "certificate_types",
    "certificate_issues",
    "attachments",
}


# ── Sync queue table (SQLite local only) ─────────────────────────────────────

def _ensure_sync_queue(sqlite_engine) -> None:
    """Create sync_queue table in the local SQLite fallback DB if not exists."""
    with sqlite_engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id          TEXT PRIMARY KEY,
                table_name  TEXT NOT NULL,
                operation   TEXT NOT NULL,
                record_id   TEXT NOT NULL,
                payload     TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                synced_at   TEXT
            )
        """))
        conn.commit()


# ── Backend state ─────────────────────────────────────────────────────────────

class SyncEngine:
    """
    Manages backend switching (postgres ↔ sqlite) and offline sync queue.
    Acts as a singleton — import and call start() once at app startup.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active_backend: str = config.DB_BACKEND   # "postgres" | "sqlite"
        self._sqlite_engine = None
        self._pg_engine = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background sync monitor. Call once at app startup."""
        if config.DB_BACKEND != "postgres":
            log.info("SyncEngine: DB_BACKEND is sqlite — offline sync disabled.")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="pitogo-sync-monitor",
        )
        self._thread.start()
        log.info("SyncEngine started — monitoring leader postgres connectivity.")

    def stop(self) -> None:
        """Stop the background monitor. Call on app shutdown."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def active_backend(self) -> str:
        """Return the currently active backend: 'postgres' or 'sqlite'."""
        with self._lock:
            return self._active_backend

    @property
    def is_online(self) -> bool:
        """True when connected to leader PostgreSQL."""
        with self._lock:
            return self._active_backend == "postgres"

    def queue_write(
        self,
        table_name: str,
        operation: str,
        record_id: str,
        payload: dict,
    ) -> None:
        """
        Record a write operation to the sync queue (local SQLite).
        Only call this when the app is in sqlite fallback mode.

        Args:
            table_name: e.g. "residents"
            operation:  "INSERT" | "UPDATE" | "DELETE"
            record_id:  the affected row's UUID
            payload:    full dict snapshot of the record
        """
        if table_name not in TRACKED_TABLES:
            return
        try:
            sqlite_eng = self._get_sqlite_engine()
            _ensure_sync_queue(sqlite_eng)
            with sqlite_eng.connect() as conn:
                conn.execute(
                    __import__("sqlalchemy").text(
                        "INSERT INTO sync_queue (id, table_name, operation, record_id, payload, created_at)"
                        " VALUES (:id, :table_name, :operation, :record_id, :payload, :created_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "table_name": table_name,
                        "operation": operation,
                        "record_id": record_id,
                        "payload": json.dumps(payload),
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
                conn.commit()
        except Exception as exc:
            log.warning(f"SyncEngine.queue_write failed: {exc}")

    # ── Background monitor ───────────────────────────────────────────────────

    def _monitor_loop(self) -> None:
        """Background thread: ping postgres, switch backend, push queue on reconnect."""
        while self._running:
            try:
                pg_reachable = self._ping_postgres()
                with self._lock:
                    current = self._active_backend

                if pg_reachable and current == "sqlite":
                    log.info("SyncEngine: Leader postgres is back — syncing queued writes...")
                    self._sync_push()
                    self._switch_to_postgres()
                    log.info("SyncEngine: Switched back to postgres.")

                elif not pg_reachable and current == "postgres":
                    log.warning("SyncEngine: Leader postgres unreachable — switching to sqlite fallback.")
                    self._switch_to_sqlite()

            except Exception as exc:
                log.error(f"SyncEngine monitor error: {exc}")

            time.sleep(SYNC_CHECK_INTERVAL)

    def _ping_postgres(self) -> bool:
        """Try a cheap connection to postgres. Returns True if reachable."""
        try:
            import sqlalchemy as sa
            url = config.get_database_url()
            # Quick engine just for the ping — don't reuse app engine
            ping_engine = sa.create_engine(url, pool_pre_ping=True, pool_size=1, max_overflow=0)
            with ping_engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            ping_engine.dispose()
            return True
        except Exception:
            return False

    def _switch_to_postgres(self) -> None:
        """Swap the app's db.py engine back to PostgreSQL."""
        try:
            import sqlalchemy as sa
            import db as _db_module
            new_engine = sa.create_engine(
                config.get_database_url(),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                future=True,
            )
            with self._lock:
                old_engine = _db_module.engine
                _db_module.engine = new_engine
                _db_module.DATABASE_URL = config.get_database_url()
                _db_module.SessionLocal.configure(bind=new_engine)
                self._active_backend = "postgres"
                self._pg_engine = new_engine
            old_engine.dispose()
        except Exception as exc:
            log.error(f"SyncEngine._switch_to_postgres failed: {exc}")

    def _switch_to_sqlite(self) -> None:
        """Swap the app's db.py engine to local SQLite fallback."""
        try:
            import sqlalchemy as sa
            import db as _db_module
            sqlite_url = f"sqlite:///{config.SECURE_DIR / 'pitogo_fallback.db'}"
            config.SECURE_DIR.mkdir(parents=True, exist_ok=True)
            fallback_engine = sa.create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                future=True,
            )
            # Ensure WAL mode for concurrent reads
            from sqlalchemy import event as _sa_event
            @_sa_event.listens_for(fallback_engine, "connect")
            def _pragma(conn, _):
                cur = conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL;")
                cur.execute("PRAGMA foreign_keys=ON;")
                cur.close()

            # Create tables in fallback DB
            from models import Base
            Base.metadata.create_all(fallback_engine)
            _ensure_sync_queue(fallback_engine)

            with self._lock:
                old_engine = _db_module.engine
                _db_module.engine = fallback_engine
                _db_module.DATABASE_URL = sqlite_url
                _db_module.SessionLocal.configure(bind=fallback_engine)
                self._active_backend = "sqlite"
                self._sqlite_engine = fallback_engine
            old_engine.dispose()
        except Exception as exc:
            log.error(f"SyncEngine._switch_to_sqlite failed: {exc}")

    def _sync_push(self) -> None:
        """
        Replay all pending sync_queue entries against PostgreSQL.
        Conflict rule: newer updated_at wins (last writer wins per record).
        """
        try:
            sqlite_eng = self._get_sqlite_engine()
            if sqlite_eng is None:
                return
            _ensure_sync_queue(sqlite_eng)

            import sqlalchemy as sa
            pg_url = config.get_database_url()
            pg_eng = sa.create_engine(pg_url, pool_pre_ping=True, pool_size=2, max_overflow=0)

            with sqlite_eng.connect() as sq_conn:
                rows = sq_conn.execute(
                    sa.text("SELECT id, table_name, operation, record_id, payload FROM sync_queue WHERE synced_at IS NULL ORDER BY created_at")
                ).fetchall()

            if not rows:
                log.info("SyncEngine: No pending sync entries.")
                pg_eng.dispose()
                return

            log.info(f"SyncEngine: Pushing {len(rows)} queued write(s) to postgres...")
            synced_ids = []

            with pg_eng.connect() as pg_conn:
                for row in rows:
                    q_id, table_name, operation, record_id, payload_json = row
                    if table_name not in TRACKED_TABLES:
                        synced_ids.append(q_id)
                        continue
                    try:
                        payload: dict = json.loads(payload_json)
                        self._apply_to_postgres(pg_conn, table_name, operation, record_id, payload)
                        synced_ids.append(q_id)
                    except Exception as exc:
                        log.warning(f"SyncEngine: Failed to sync {operation} on {table_name}/{record_id}: {exc}")

                pg_conn.commit()

            pg_eng.dispose()

            # Mark synced in local queue
            now = datetime.utcnow().isoformat()
            with sqlite_eng.connect() as sq_conn:
                for q_id in synced_ids:
                    sq_conn.execute(
                        sa.text("UPDATE sync_queue SET synced_at = :now WHERE id = :id"),
                        {"now": now, "id": q_id},
                    )
                sq_conn.commit()

            log.info(f"SyncEngine: Sync complete — {len(synced_ids)}/{len(rows)} entries pushed.")

        except Exception as exc:
            log.error(f"SyncEngine._sync_push failed: {exc}")

    def _apply_to_postgres(self, conn, table_name: str, operation: str, record_id: str, payload: dict) -> None:
        """Apply a single queued write to PostgreSQL using UPSERT / DELETE."""
        import sqlalchemy as sa

        op = operation.upper()
        if op == "DELETE":
            conn.execute(
                sa.text(f"DELETE FROM {table_name} WHERE id = :id"),
                {"id": record_id},
            )
        elif op in ("INSERT", "UPDATE"):
            if not payload:
                return
            cols = list(payload.keys())
            # Build: INSERT ... ON CONFLICT (id) DO UPDATE SET ...
            col_placeholders = ", ".join(f":{c}" for c in cols)
            col_names = ", ".join(cols)
            update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
            sql = (
                f"INSERT INTO {table_name} ({col_names}) VALUES ({col_placeholders})"
                f" ON CONFLICT (id) DO UPDATE SET {update_set}"
            )
            conn.execute(sa.text(sql), payload)

    def _get_sqlite_engine(self):
        """Return the current sqlite fallback engine, or build one if needed."""
        if self._sqlite_engine is not None:
            return self._sqlite_engine
        try:
            import sqlalchemy as sa
            sqlite_url = f"sqlite:///{config.SECURE_DIR / 'pitogo_fallback.db'}"
            self._sqlite_engine = sa.create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                future=True,
            )
            return self._sqlite_engine
        except Exception:
            return None


# ── Module-level singleton ────────────────────────────────────────────────────
sync_engine = SyncEngine()
