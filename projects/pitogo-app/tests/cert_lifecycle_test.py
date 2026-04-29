"""Certificate lifecycle tests: issue → list → generate → void."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discovery

discovery.start = lambda *args, **kwargs: None
discovery.stop = lambda *args, **kwargs: None

import api.deps as deps
import auth
from app import app
from fastapi.testclient import TestClient
from models import Base, CertificateType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def run():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_db

    with TestClient(app) as client:
        admin_token = auth.create_session("admin", "admin", "Admin User")
        clerk_token = auth.create_session("clerk1", "clerk", "Clerk One")
        adm = {"Authorization": f"Bearer {admin_token}"}
        clk = {"Authorization": f"Bearer {clerk_token}"}

        # Setup: seed certificate type
        db = Session()
        ct = CertificateType(code="CLR", name="Barangay Clearance", template="barangay_clearance.html")
        db.add(ct)
        db.commit()
        db.refresh(ct)
        ct_id = ct.id
        db.close()

        # Setup: create resident
        r = client.post("/api/residents/", json={"first_name": "Pedro", "last_name": "Santos"}, headers=adm)
        assert r.status_code == 201, f"create resident: {r.status_code} {r.text}"
        resident_id = r.json()["id"]

        # --- 1. Issue certificate ---
        r = client.post("/api/certificates/", json={
            "certificate_type_id": ct_id,
            "resident_id": resident_id,
            "meta": {"purpose": "employment"}
        }, headers=clk)
        assert r.status_code == 201, f"issue cert: {r.status_code} {r.text}"
        cert = r.json()
        cert_id = cert["id"]
        assert "control_number" in cert
        print(f"  ✓ Issued: {cert['control_number']}")

        # --- 2. List certificates (default: active only) ---
        r = client.get("/api/certificates/", headers=adm)
        assert r.status_code == 200, f"list certs: {r.status_code} {r.text}"
        data = r.json()
        assert data["total"] >= 1
        ids = [c["id"] for c in data["items"]]
        assert cert_id in ids
        print(f"  ✓ List: {data['total']} cert(s)")

        # --- 3. List with status filter ---
        r = client.get("/api/certificates/?status=issued", headers=adm)
        assert r.status_code == 200
        assert any(c["id"] == cert_id for c in r.json()["items"])
        print("  ✓ Status filter: issued")

        # --- 4. List with resident filter ---
        r = client.get(f"/api/certificates/?resident_id={resident_id}", headers=adm)
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        print("  ✓ Resident filter")

        # --- 5. Void: clerk cannot void another clerk's cert (same clerk can) ---
        r = client.post(f"/api/certificates/{cert_id}/void",
                        json={"reason": "Duplicate issuance"},
                        headers=clk)
        assert r.status_code == 200, f"void cert: {r.status_code} {r.text}"
        v = r.json()
        assert v["status"] == "voided"
        assert v["voided_by"] == "clerk1"
        assert v["void_reason"] == "Duplicate issuance"
        print(f"  ✓ Voided by issuer")

        # --- 6. Cannot void already-voided cert ---
        r = client.post(f"/api/certificates/{cert_id}/void",
                        json={"reason": "Again"},
                        headers=adm)
        assert r.status_code == 409, f"re-void should 409: {r.status_code}"
        print("  ✓ Re-void blocked (409)")

        # --- 7. Voided cert excluded from default list ---
        r = client.get("/api/certificates/", headers=adm)
        assert r.status_code == 200
        ids_after = [c["id"] for c in r.json()["items"]]
        assert cert_id not in ids_after
        print("  ✓ Voided cert excluded from default list")

        # --- 8. Voided cert appears with status=voided filter ---
        r = client.get("/api/certificates/?status=voided", headers=adm)
        assert r.status_code == 200
        assert any(c["id"] == cert_id for c in r.json()["items"])
        print("  ✓ Voided cert visible with status=voided filter")

        # --- 9. Issue second cert for generate test ---
        r = client.post("/api/certificates/", json={
            "certificate_type_id": ct_id,
            "resident_id": resident_id,
        }, headers=adm)
        assert r.status_code == 201
        cert2_id = r.json()["id"]

        # --- 10. Generate (finalize) certificate ---
        r = client.post(f"/api/certificates/{cert2_id}/generate", json={}, headers=adm)
        assert r.status_code == 200, f"generate: {r.status_code} {r.text}"
        gen = r.json()
        assert "pdf_path" in gen
        assert "download_url" in gen
        print(f"  ✓ Generated: {gen['pdf_path']}")

        # --- 11. Verify finalized_at is set ---
        r = client.get("/api/certificates/?status=issued", headers=adm)
        finalized = [c for c in r.json()["items"] if c["id"] == cert2_id]
        assert finalized and finalized[0]["finalized_at"] is not None
        print("  ✓ finalized_at set after generate")

    print("CERT_LIFECYCLE_TESTS_PASSED")


if __name__ == "__main__":
    run()
