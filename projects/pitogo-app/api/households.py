from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_db
import auth
from models import Household, Resident

router = APIRouter(prefix="/api/households", tags=["households"])


class HouseholdIn(BaseModel):
    address_line: str
    barangay: str
    city: str
    zip_code: Optional[str] = None
    head_resident_id: Optional[str] = None


def _to_dict(h: Household) -> dict:
    return {
        "id": h.id,
        "head_resident_id": h.head_resident_id,
        "address_line": h.address_line,
        "barangay": h.barangay,
        "city": h.city,
        "zip_code": h.zip_code,
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
    }


@router.get("/")
def list_households(q: Optional[str] = None, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    query = db.query(Household)
    if q:
        qlike = f"%{q}%"
        query = query.filter(
            (Household.address_line.ilike(qlike)) | (Household.barangay.ilike(qlike)) | (Household.city.ilike(qlike))
        )
    rows = query.order_by(Household.created_at.desc()).limit(200).all()
    return [_to_dict(r) for r in rows]


@router.post("/", status_code=201)
def create_household(body: HouseholdIn, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    if body.head_resident_id:
        head = db.query(Resident).get(body.head_resident_id)
        if not head:
            raise HTTPException(status_code=400, detail="head_resident_id not found")
    h = Household(
        address_line=body.address_line,
        barangay=body.barangay,
        city=body.city,
        zip_code=body.zip_code,
        head_resident_id=body.head_resident_id,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return _to_dict(h)


@router.get("/{household_id}")
def get_household(household_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    h = db.query(Household).get(household_id)
    if not h:
        raise HTTPException(status_code=404, detail="household not found")
    return _to_dict(h)


@router.put("/{household_id}")
def update_household(household_id: str, body: HouseholdIn, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    h = db.query(Household).get(household_id)
    if not h:
        raise HTTPException(status_code=404, detail="household not found")
    h.address_line = body.address_line
    h.barangay = body.barangay
    h.city = body.city
    h.zip_code = body.zip_code
    h.head_resident_id = body.head_resident_id
    db.add(h)
    db.commit()
    db.refresh(h)
    return _to_dict(h)


@router.delete("/{household_id}")
def delete_household(household_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    h = db.query(Household).get(household_id)
    if not h:
        raise HTTPException(status_code=404, detail="household not found")
    # prevent deleting households that still have members
    members = db.query(Resident).filter_by(household_id=household_id).count()
    if members:
        raise HTTPException(status_code=400, detail="household has members; reassign or remove members first")
    db.delete(h)
    db.commit()
    return {"status": "deleted"}
