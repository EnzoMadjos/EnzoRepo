from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_db
import auth
from models import CertificateType

router = APIRouter(prefix="/api/certificate-types", tags=["certificate-types"])


class CertificateTypeIn(BaseModel):
    code: str
    name: str
    template: str


def _to_dict(ct: CertificateType) -> dict:
    return {"id": ct.id, "code": ct.code, "name": ct.name, "template": ct.template}


@router.get("/")
def list_types(db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    rows = db.query(CertificateType).order_by(CertificateType.code).all()
    return [_to_dict(r) for r in rows]


@router.post("/", status_code=201)
def create_type(body: CertificateTypeIn, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    exists = db.query(CertificateType).filter_by(code=body.code).first()
    if exists:
        raise HTTPException(status_code=400, detail="code already exists")
    ct = CertificateType(code=body.code, name=body.name, template=body.template)
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return _to_dict(ct)
