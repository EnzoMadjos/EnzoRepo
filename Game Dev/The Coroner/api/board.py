"""
Board API — HTML5 canvas state sync with conflict detection.
Server is source of truth for version. Client debounces saves (3s).
Conflict: if client sends server_version < current → return 409 with latest state.

GET  /api/board/{case_id}        — load current board state
POST /api/board/{case_id}/sync   — save canvas state (with version check)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/board", tags=["board"])

# Max JSON size for board state — prevent runaway canvas data
MAX_BOARD_BYTES = 512_000  # 512 KB


class SyncRequest(BaseModel):
    case_id: int
    state_json: str          # full serialized canvas state from JS
    client_version: int      # client's last known server_version


# ── GET /api/board/{case_id} ──────────────────────────────────────────────────

@router.get("/{case_id}")
async def get_board(case_id: int, db: Session = Depends(get_db)):
    """Return current board state and version."""
    from models import BoardState
    board = db.query(BoardState).filter(BoardState.case_id == case_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found for this case")
    return {
        "case_id": case_id,
        "state_json": board.state_json,
        "server_version": board.server_version,
        "updated_at": board.updated_at.isoformat() if board.updated_at else None,
    }


# ── POST /api/board/{case_id}/sync ────────────────────────────────────────────

@router.post("/{case_id}/sync")
async def sync_board(
    case_id: int,
    body: SyncRequest,
    db: Session = Depends(get_db),
):
    """
    Save board state. Conflict detection via server_version.
    409 if client is behind — client must merge with returned state.
    """
    from models import BoardState

    if len(body.state_json.encode()) > MAX_BOARD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Board state exceeds {MAX_BOARD_BYTES // 1024}KB limit"
        )

    # Validate JSON
    try:
        json.loads(body.state_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="state_json must be valid JSON")

    board = db.query(BoardState).filter(BoardState.case_id == case_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found for this case")

    # Conflict check
    if body.client_version < board.server_version:
        logger.warning(
            f"Board conflict case {case_id}: client_v={body.client_version} server_v={board.server_version}"
        )
        return {
            "conflict": True,
            "server_version": board.server_version,
            "server_state_json": board.state_json,
        }

    # Save new state
    board.state_json = body.state_json
    board.server_version = board.server_version + 1
    board.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(board)

    return {
        "conflict": False,
        "server_version": board.server_version,
        "updated_at": board.updated_at.isoformat(),
    }
