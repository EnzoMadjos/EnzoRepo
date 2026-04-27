from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_db
import auth
from models import Resident

router = APIRouter(prefix="/api/residents", tags=["residents"])


class ResidentIn(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birthdate: Optional[date] = None
    contact_number: Optional[str] = None
    national_id: Optional[str] = None
    household_id: Optional[str] = None


def _to_dict(r: Resident) -> dict:
    return {
        "id": r.id,
        "first_name": r.first_name,
        "last_name": r.last_name,
        "middle_name": r.middle_name,
        "birthdate": r.birthdate.isoformat() if r.birthdate else None,
        "contact_number": r.contact_number,
        "national_id": r.national_id,
        "household_id": r.household_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/")
def list_residents(q: Optional[str] = None, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    query = db.query(Resident)
    if q:
        qlike = f"%{q}%"
        query = query.filter(
            (Resident.first_name.ilike(qlike)) | (Resident.last_name.ilike(qlike)) | (Resident.national_id.ilike(qlike))
        )
    rows = query.order_by(Resident.last_name, Resident.first_name).limit(200).all()
    return [ _to_dict(r) for r in rows ]


@router.post("/", status_code=201)
def create_resident(body: ResidentIn, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    # prevent duplicate national_id
    if body.national_id:
        exists = db.query(Resident).filter_by(national_id=body.national_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="national_id already exists")
    r = Resident(
        first_name=body.first_name,
        last_name=body.last_name,
        middle_name=body.middle_name,
        birthdate=body.birthdate,
        contact_number=body.contact_number,
        national_id=body.national_id,
        household_id=body.household_id,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_dict(r)


@router.get("/{resident_id}")
def get_resident(resident_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    r = db.query(Resident).get(resident_id)
    if not r:
        raise HTTPException(status_code=404, detail="resident not found")
    return _to_dict(r)


@router.put("/{resident_id}")
def update_resident(resident_id: str, body: ResidentIn, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    r = db.query(Resident).get(resident_id)
    if not r:
        raise HTTPException(status_code=404, detail="resident not found")
    for k, v in body.dict().items():
        setattr(r, k, v)
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_dict(r)


@router.delete("/{resident_id}")
def delete_resident(resident_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    r = db.query(Resident).get(resident_id)
    if not r:
        raise HTTPException(status_code=404, detail="resident not found")
    db.delete(r)
    db.commit()
    return {"status": "deleted"}
