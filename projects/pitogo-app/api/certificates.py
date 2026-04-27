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
from models import Resident, Household
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))

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


@router.get("/{cert_id}/render", response_class=HTMLResponse)
def render_certificate(cert_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    ci = db.query(CertificateIssue).get(cert_id)
    if not ci:
        raise HTTPException(status_code=404, detail="certificate not found")
    ct = db.query(CertificateType).get(ci.certificate_type_id)
    if not ct:
        raise HTTPException(status_code=404, detail="certificate type not found")

    resident = None
    household = None
    if ci.resident_id:
        resident = db.query(Resident).get(ci.resident_id)
    if ci.household_id:
        household = db.query(Household).get(ci.household_id)

    template_name = f"certs/{ct.template}"
    try:
        rendered = templates.get_template(template_name).render(
            control_number=ci.control_number,
            issued_by=ci.issued_by,
            issued_at=ci.issued_at.strftime("%B %d, %Y"),
            resident=resident,
            household=household,
            meta=ci.meta or {},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"render failed: {exc}")

    return HTMLResponse(rendered)


@router.post("/{cert_id}/generate")
def generate_certificate_file(cert_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    """Render certificate HTML and save to disk. If WeasyPrint is available, also write a PDF.

    This is a conservative stub for Sprint 1 — stores HTML and updates `pdf_path`.
    """
    import os
    from datetime import datetime

    ci = db.query(CertificateIssue).get(cert_id)
    if not ci:
        raise HTTPException(status_code=404, detail="certificate not found")
    ct = db.query(CertificateType).get(ci.certificate_type_id)
    if not ct:
        raise HTTPException(status_code=404, detail="certificate type not found")

    resident = None
    household = None
    if ci.resident_id:
        resident = db.query(Resident).get(ci.resident_id)
    if ci.household_id:
        household = db.query(Household).get(ci.household_id)

    template_name = f"certs/{ct.template}"
    try:
        rendered = templates.get_template(template_name).render(
            control_number=ci.control_number,
            issued_by=ci.issued_by,
            issued_at=ci.issued_at.strftime("%B %d, %Y"),
            resident=resident,
            household=household,
            meta=ci.meta or {},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"render failed: {exc}")

    # persist to secure storage
    now = datetime.utcnow()
    dest_dir = config.SECURE_DIR / "storage" / "certificates" / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_base = ci.control_number.replace("/", "_")
    html_path = dest_dir / f"{safe_base}.html"
    html_path.write_text(rendered, encoding="utf-8")

    pdf_path = None
    try:
        # optional: convert to PDF if weasyprint is installed
        from weasyprint import HTML

        pdf_path = dest_dir / f"{safe_base}.pdf"
        HTML(string=rendered).write_pdf(str(pdf_path))
    except Exception:
        pdf_path = None

    ci.pdf_path = str(pdf_path if pdf_path else html_path)
    db.add(ci)
    db.commit()
    db.refresh(ci)
    return {"id": ci.id, "pdf_path": ci.pdf_path}
