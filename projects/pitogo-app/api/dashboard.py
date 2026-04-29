"""Dashboard stats API."""
from __future__ import annotations

from datetime import datetime, timedelta

import auth
from api.deps import get_db
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from models import CertificateIssue, CertificateType, Household, Resident
from sqlalchemy import func

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(
    db=Depends(get_db),
    session: auth.SessionData = Depends(auth.require_auth),
):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)

    certs_today = (
        db.query(func.count(CertificateIssue.id))
        .filter(
            CertificateIssue.issued_at >= today_start,
            CertificateIssue.status != "voided",
        )
        .scalar()
        or 0
    )
    certs_month = (
        db.query(func.count(CertificateIssue.id))
        .filter(
            CertificateIssue.issued_at >= month_start,
            CertificateIssue.status != "voided",
        )
        .scalar()
        or 0
    )
    certs_total = (
        db.query(func.count(CertificateIssue.id))
        .filter(CertificateIssue.status != "voided")
        .scalar()
        or 0
    )
    residents_total = db.query(func.count(Resident.id)).scalar() or 0
    households_total = db.query(func.count(Household.id)).scalar() or 0

    recent = (
        db.query(CertificateIssue)
        .filter(CertificateIssue.status != "voided")
        .order_by(CertificateIssue.issued_at.desc())
        .limit(5)
        .all()
    )

    recent_list = []
    for ci in recent:
        ct = db.query(CertificateType).get(ci.certificate_type_id)
        resident = db.query(Resident).get(ci.resident_id) if ci.resident_id else None
        name = (
            f"{resident.first_name} {resident.last_name}" if resident else "—"
        )
        recent_list.append(
            {
                "id": ci.id,
                "control_number": ci.control_number,
                "certificate_type_name": ct.name if ct else "—",
                "resident_name": name,
                "issued_by": ci.issued_by,
                "issued_at": ci.issued_at.isoformat(),
                "status": ci.status,
            }
        )

    return JSONResponse(
        {
            "certs_today": certs_today,
            "certs_month": certs_month,
            "certs_total": certs_total,
            "residents_total": residents_total,
            "households_total": households_total,
            "recent_certs": recent_list,
        }
    )
