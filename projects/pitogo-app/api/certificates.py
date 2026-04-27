from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from api.deps import get_db
import auth
import config
from models import CertificateIssue, CertificateType
from node import get_node_id, get_node_short

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


class IssueRequest(BaseModel):
    certificate_type_code: Optional[str] = None
    certificate_type_id: Optional[str] = None
    resident_id: Optional[str] = None
    household_id: Optional[str] = None
    meta: dict = {}


@router.post("/", status_code=201)
def create_certificate(body: IssueRequest, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    # resolve certificate type
    ct = None
    if body.certificate_type_id:
        ct = db.query(CertificateType).get(body.certificate_type_id)
    elif body.certificate_type_code:
        ct = db.query(CertificateType).filter_by(code=body.certificate_type_code).first()
    if not ct:
        raise HTTPException(status_code=400, detail="certificate type not found")

    issued_at = datetime.utcnow()
    node_id = get_node_id()
    date_start = datetime(issued_at.year, issued_at.month, issued_at.day)
    date_end = date_start + timedelta(days=1)
    max_seq = db.query(func.max(CertificateIssue.local_seq)).filter(
        CertificateIssue.node_id == node_id,
        CertificateIssue.issued_at >= date_start,
        CertificateIssue.issued_at < date_end,
    ).scalar()
    local_seq = (max_seq or 0) + 1

    node_short = get_node_short(6)
    date_str = issued_at.strftime("%Y%m%d")
    brgy = getattr(config, "BRGY_CODE", "PITOGO")
    control_number = f"{brgy}-{node_short}-{date_str}-{local_seq:04d}"

    ci = CertificateIssue(
        control_number=control_number,
        certificate_type_id=ct.id,
        resident_id=body.resident_id,
        household_id=body.household_id,
        issued_by=session.username,
        issued_at=issued_at,
        pdf_path="",
        node_id=node_id,
        local_seq=local_seq,
        meta=body.meta,
    )
    db.add(ci)
    db.commit()
    db.refresh(ci)
    return {"id": ci.id, "control_number": ci.control_number, "issued_at": ci.issued_at.isoformat()}
