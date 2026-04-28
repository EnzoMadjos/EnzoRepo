from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_
import app_logger

from api.deps import get_db
import auth
import config
from models import CertificateIssue, CertificateType
from node import get_node_id, get_node_short
from models import Resident, Household
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pathlib import Path
import mimetypes
import utils
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(config.BASE_DIR / "templates"))

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


class IssueRequest(BaseModel):
    certificate_type_code: Optional[str] = None
    certificate_type_id: Optional[str] = None
    resident_id: Optional[str] = None
    household_id: Optional[str] = None
    meta: dict = {}


class GenerateRequest(BaseModel):
        """Optional overrides to apply to the template context before generating final output.

        Example:
        {
            "overrides": {
                 "resident": {"first_name": "Corrected", "last_name": "Name"},
                 "household": {"address_line": "New address"},
                 "issued_by": "clerkuser",
                 "meta": {"purpose": "clearance"}
            }
        }
        """
        overrides: Optional[dict] = None


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


def _resident_dict(resident: Resident | None, issued_at=None) -> dict | None:
    if resident is None:
        return None
    dob = resident.birthdate
    age = None
    if dob:
        try:
            now = issued_at or datetime.utcnow()
            age = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
        except Exception:
            age = None
    full_name = " ".join(filter(None, [resident.first_name, resident.middle_name or "", resident.last_name])).strip()
    return {
        "id": resident.id,
        "first_name": resident.first_name,
        "last_name": resident.last_name,
        "middle_name": resident.middle_name,
        "full_name": full_name,
        "birthdate": dob.isoformat() if dob else None,
        "birthdate_fmt": dob.strftime("%B %d, %Y") if dob else None,
        "age": age,
        "contact_number": resident.contact_number,
        "national_id": resident.national_id,
    }


def _household_dict(household: Household | None) -> dict | None:
    if household is None:
        return None
    return {
        "id": household.id,
        "head_resident_id": household.head_resident_id,
        "address_line": household.address_line,
        "barangay": household.barangay,
        "city": household.city,
        "zip_code": household.zip_code,
    }


@router.get("/{cert_id}/preview")
def preview_certificate(cert_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
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
        resident_ctx = _resident_dict(resident, ci.issued_at)
        household_ctx = _household_dict(household)
        context = {
            "control_number": ci.control_number,
            "issued_by": ci.issued_by,
            "issued_at": ci.issued_at.strftime("%B %d, %Y"),
            "resident": resident_ctx,
            "household": household_ctx,
            "certificate_type": {"id": ct.id, "code": ct.code, "name": ct.name},
            "meta": ci.meta or {},
        }
        rendered = templates.get_template(template_name).render(**context)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"preview failed: {exc}")

    return JSONResponse({"html": rendered, "context": context})


@router.post("/{cert_id}/preview")
def preview_certificate_with_overrides(cert_id: str, body: Optional[GenerateRequest] = None, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    """Render the certificate with optional overrides but do not persist anything.

    This supports client-side edit -> preview -> confirm workflows.
    """
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

    # base contexts
    resident_ctx = _resident_dict(resident, ci.issued_at)
    household_ctx = _household_dict(household)
    issued_by = ci.issued_by
    meta_ctx = dict(ci.meta or {})

    # apply overrides (same logic as generate)
    if body and body.overrides:
        ov = body.overrides or {}
        if "issued_by" in ov:
            issued_by = ov["issued_by"]
        if "meta" in ov and isinstance(ov["meta"], dict):
            meta_ctx.update(ov["meta"])
        if "resident" in ov and isinstance(ov["resident"], dict):
            rc = dict(resident_ctx or {})
            rc.update(ov["resident"])
            fn = " ".join(filter(None, [rc.get("first_name"), rc.get("middle_name") or "", rc.get("last_name")])).strip()
            rc["full_name"] = fn
            bd = rc.get("birthdate")
            if bd:
                try:
                    dob = datetime.fromisoformat(bd).date()
                    rc["birthdate_fmt"] = dob.strftime("%B %d, %Y")
                    now_dt = ci.issued_at or datetime.utcnow()
                    rc["age"] = now_dt.year - dob.year - ((now_dt.month, now_dt.day) < (dob.month, dob.day))
                except Exception:
                    pass
            resident_ctx = rc
        if "household" in ov and isinstance(ov["household"], dict):
            hc = dict(household_ctx or {})
            hc.update(ov["household"])
            household_ctx = hc

    template_name = f"certs/{ct.template}"
    try:
        rendered = templates.get_template(template_name).render(
            control_number=ci.control_number,
            issued_by=issued_by,
            issued_at=ci.issued_at.strftime("%B %d, %Y"),
            resident=resident_ctx,
            household=household_ctx,
            meta=meta_ctx,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"preview failed: {exc}")

    context = {
        "control_number": ci.control_number,
        "issued_by": issued_by,
        "issued_at": ci.issued_at.strftime("%B %d, %Y"),
        "resident": resident_ctx,
        "household": household_ctx,
        "certificate_type": {"id": ct.id, "code": ct.code, "name": ct.name},
        "meta": meta_ctx,
    }
    return JSONResponse({"html": rendered, "context": context})


@router.get("/recent")
def list_recent_certificates(q: Optional[str] = None, certificate_type_id: Optional[str] = None, page: int = 1, per_page: int = 20, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    """Return a paginated list of recent certificate issues for the UI dropdown.

    Optional query params:
      - q: search string (control number or resident first/last name)
      - certificate_type_id: filter by certificate type id
      - page, per_page: pagination
    """
    # clamp per_page
    per_page = max(1, min(per_page or 20, 100))
    page = max(1, page or 1)

    query = db.query(CertificateIssue).outerjoin(Resident).order_by(CertificateIssue.issued_at.desc())
    if certificate_type_id:
        query = query.filter(CertificateIssue.certificate_type_id == certificate_type_id)
    if q:
        # tokenized fuzzy-ish matching across control number and resident name
        tokens = [t.strip() for t in q.split() if t.strip()]
        conds = []
        for tok in tokens:
            like = f"%{tok}%"
            conds.append(CertificateIssue.control_number.ilike(like))
            conds.append(Resident.first_name.ilike(like))
            conds.append(Resident.last_name.ilike(like))
            # also match concatenated first + last name
            conds.append(func.concat(Resident.first_name, ' ', Resident.last_name).ilike(like))
        if conds:
            query = query.filter(or_(*conds))

    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    out = []
    for ci in rows:
        resident = db.query(Resident).get(ci.resident_id) if ci.resident_id else None
        resident_ctx = _resident_dict(resident, ci.issued_at)
        out.append({
            "id": ci.id,
            "control_number": ci.control_number,
            "issued_at": ci.issued_at.isoformat(),
            "pdf_path": ci.pdf_path,
            "certificate_type_id": ci.certificate_type_id,
            "resident_full_name": resident_ctx.get("full_name") if resident_ctx else None,
        })

    return JSONResponse({"items": out, "page": page, "per_page": per_page, "total": total})


@router.get("/{cert_id}/file")
def get_certificate_file(cert_id: str, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    """Serve the generated certificate HTML/PDF stored under secure storage.

    This endpoint requires authentication and validates the file path is under the configured secure directory.
    """
    ci = db.query(CertificateIssue).get(cert_id)
    if not ci or not ci.pdf_path:
        raise HTTPException(status_code=404, detail="file not found")

    file_path = Path(ci.pdf_path)
    try:
        secure_root = config.SECURE_DIR.resolve()
        target = file_path.resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="file not found")

    if not str(target).startswith(str(secure_root)):
        raise HTTPException(status_code=403, detail="access denied")

    mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    return FileResponse(path=str(target), media_type=mime, filename=target.name)


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
        # build convenience dicts with computed fields for templates
        resident_ctx = _resident_dict(resident, ci.issued_at)
        household_ctx = _household_dict(household)
        rendered = templates.get_template(template_name).render(
            control_number=ci.control_number,
            issued_by=ci.issued_by,
            issued_at=ci.issued_at.strftime("%B %d, %Y"),
            resident=resident_ctx,
            household=household_ctx,
            certificate_type={"id": ct.id, "code": ct.code, "name": ct.name},
            meta=ci.meta or {},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"render failed: {exc}")

    return HTMLResponse(rendered)


@router.post("/{cert_id}/generate")
def generate_certificate_file(cert_id: str, body: Optional[GenerateRequest] = None, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    """Render certificate HTML and save to disk. If WeasyPrint is available, also write a PDF.

    This is a conservative stub for Sprint 1 — stores HTML and updates `pdf_path`.
    """
    import os

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
    # build base contexts
    resident_ctx = _resident_dict(resident, ci.issued_at)
    household_ctx = _household_dict(household)
    issued_by = ci.issued_by
    meta_ctx = dict(ci.meta or {})

    # apply any overrides provided by the client (for corrections before finalizing)
    if body and body.overrides:
        ov = body.overrides or {}
        if "issued_by" in ov:
            issued_by = ov["issued_by"]
        if "meta" in ov and isinstance(ov["meta"], dict):
            meta_ctx.update(ov["meta"])
        if "resident" in ov and isinstance(ov["resident"], dict):
            rc = dict(resident_ctx or {})
            rc.update(ov["resident"])
            # recompute convenience fields
            fn = " ".join(filter(None, [rc.get("first_name"), rc.get("middle_name") or "", rc.get("last_name")])).strip()
            rc["full_name"] = fn
            bd = rc.get("birthdate")
            if bd:
                try:
                    dob = datetime.fromisoformat(bd).date()
                    rc["birthdate_fmt"] = dob.strftime("%B %d, %Y")
                    now_dt = ci.issued_at or datetime.utcnow()
                    rc["age"] = now_dt.year - dob.year - ((now_dt.month, now_dt.day) < (dob.month, dob.day))
                except Exception:
                    pass
            resident_ctx = rc
        if "household" in ov and isinstance(ov["household"], dict):
            hc = dict(household_ctx or {})
            hc.update(ov["household"])
            household_ctx = hc

    try:
        rendered = templates.get_template(template_name).render(
            control_number=ci.control_number,
            issued_by=issued_by,
            issued_at=ci.issued_at.strftime("%B %d, %Y"),
            resident=resident_ctx,
            household=household_ctx,
            meta=meta_ctx,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"render failed: {exc}")

    # persist to secure storage (HTML + optional PDF)
    from pdf_renderer import render_and_store

    now = datetime.utcnow()
    dest_dir = config.SECURE_DIR / "storage" / "certificates" / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    safe_base = ci.control_number.replace("/", "_")
    # pass the same computed contexts to renderer so placeholders match
    resident_ctx = _resident_dict(resident, ci.issued_at)
    household_ctx = _household_dict(household)
    # Rendered HTML already uses Jinja; we stored it earlier during template.render
    stored = render_and_store(rendered, dest_dir, safe_base)

    ci.pdf_path = stored
    db.add(ci)
    db.commit()
    db.refresh(ci)
    download_url = f"/api/certificates/{ci.id}/file"

    # Audit log: record that the certificate was generated/finalized
    try:
        app_logger.info("Certificate generated", username=session.username, cert_id=ci.id, control_number=ci.control_number, issued_by=issued_by, path=ci.pdf_path)
    except Exception:
        # logging must not break generation
        pass

    return {"id": ci.id, "pdf_path": ci.pdf_path, "download_url": download_url}


@router.post("/{cert_id}/signed_url")
def create_signed_download(cert_id: str, ttl: int = 300, db=Depends(get_db), session: auth.SessionData = Depends(auth.require_auth)):
    """Create a short-lived signed URL to download the generated certificate file without further auth.

    Requires `DOWNLOAD_SECRET` to be set in config.
    """
    if not config.DOWNLOAD_SECRET:
        raise HTTPException(status_code=500, detail="DOWNLOAD_SECRET is not configured on the server")

    ci = db.query(CertificateIssue).get(cert_id)
    if not ci or not ci.pdf_path:
        raise HTTPException(status_code=404, detail="certificate file not found")

    target = Path(ci.pdf_path)
    try:
        target_resolved = target.resolve()
        secure_root = config.SECURE_DIR.resolve()
    except Exception:
        raise HTTPException(status_code=404, detail="file not found")

    if not str(target_resolved).startswith(str(secure_root)):
        raise HTTPException(status_code=403, detail="access denied")

    rel_path = str(Path(target_resolved).relative_to(secure_root).as_posix())
    try:
        token, exp = utils.create_signed_token(rel_path, ttl)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    url = f"/download/{token}"
    expires_at = datetime.utcfromtimestamp(exp).isoformat() + 'Z'
    return {"url": url, "expires_at": expires_at}
