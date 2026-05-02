"""
Database helper for PITOGO app.

Supports two backends via .env:
  DB_BACKEND=postgres  →  PostgreSQL (production, multi-machine LAN)
  DB_BACKEND=sqlite    →  SQLite (local dev / offline emergency fallback)

Provides `engine`, `SessionLocal`, `DATABASE_URL`, and helpers.
"""

from __future__ import annotations

import config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DATABASE_URL = config.get_database_url()

# ── Engine setup ──────────────────────────────────────────────────────────────
if config.DB_BACKEND == "postgres":
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,     # detect stale connections (handles power cuts / reconnect)
        pool_size=5,
        max_overflow=10,
        future=True,
    )
else:
    # SQLite fallback — only used during offline emergencies
    config.SECURE_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
        except Exception:
            pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(Base) -> None:
    """Create all tables for the provided SQLAlchemy Base."""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
