from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

import auth
import config
from api.deps import get_db
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from models import Attachment

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


def _ensure_storage_dir(owner_type: str) -> Path:
    today = datetime.utcnow()
    dest = (
        config.SECURE_DIR
        / "storage"
        / owner_type
        / today.strftime("%Y")
        / today.strftime("%m")
        / today.strftime("%d")
    )
    dest.mkdir(parents=True, exist_ok=True)
    return dest


@router.post("/upload", status_code=201)
async def upload_attachment(
    owner_type: str,
    owner_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),
    session: auth.SessionData = Depends(auth.require_auth),
):
    contents = await file.read()
    dest_dir = _ensure_storage_dir(owner_type)
    ext = Path(file.filename).suffix
    fname = f"{uuid.uuid4().hex}{ext}"
    dest_path = dest_dir / fname
    dest_path.write_bytes(contents)

    checksum = hashlib.sha256(contents).hexdigest()
    size = len(contents)

    a = Attachment(
        owner_type=owner_type,
        owner_id=owner_id,
        original_filename=file.filename,
        stored_path=str(dest_path),
        mime_type=file.content_type,
        size=size,
        checksum=checksum,
        uploaded_by=session.username,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {
        "id": a.id,
        "stored_path": a.stored_path,
        "size": a.size,
        "checksum": a.checksum,
    }


@router.get("/{attachment_id}")
def download_attachment(
    attachment_id: str,
    db=Depends(get_db),
    session: auth.SessionData = Depends(auth.require_auth),
):
    a = db.query(Attachment).get(attachment_id)
    if not a:
        raise HTTPException(status_code=404, detail="attachment not found")
    p = Path(a.stored_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing on disk")
    return FileResponse(
        path=str(p), filename=a.original_filename, media_type=a.mime_type
    )


@router.delete("/{attachment_id}")
def delete_attachment(
    attachment_id: str,
    db=Depends(get_db),
    session: auth.SessionData = Depends(auth.require_auth),
):
    a = db.query(Attachment).get(attachment_id)
    if not a:
        raise HTTPException(status_code=404, detail="attachment not found")
    # only uploader or admin can delete
    if session.role != "admin" and session.username != a.uploaded_by:
        raise HTTPException(status_code=403, detail="forbidden")
    p = Path(a.stored_path)
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass
    db.delete(a)
    db.commit()
    return {"status": "deleted"}
