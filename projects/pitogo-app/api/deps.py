from __future__ import annotations

from typing import Generator

from db import get_session


def get_db() -> Generator:
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()
