"""
Database helper for PITOGO app (SQLite + SQLAlchemy).

Provides `engine`, `SessionLocal`, and `init_db(Base)` to create tables.
"""
from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import config


DB_PATH = config.SECURE_DIR / "pitogo.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

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
        # best-effort; don't crash on pragma issues
        pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db(Base) -> None:
    """Create database tables for the provided SQLAlchemy `Base` metadata."""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()

