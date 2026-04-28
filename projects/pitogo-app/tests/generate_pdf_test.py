import sys
from pathlib import Path

# Ensure project imports work
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discovery
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

discovery.start = lambda *args, **kwargs: None
discovery.stop = lambda *args, **kwargs: None

import api.deps as deps
import auth
from app import app
from models import Base, CertificateIssue, CertificateType


def run():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        token = auth.create_session("pdftester", "admin", "PDF Tester")
        headers = {"Authorization": f"Bearer {token}"}

        # create resident
        r = client.post(
            "/api/residents/",
            json={"first_name": "PDF", "last_name": "Tester"},
            headers=headers,
        )
        if r.status_code != 201:
            print("CREATE_RES_FAILED", r.status_code, r.text)
            return
        resident = r.json()

        # create certificate type in DB directly
        db = TestingSessionLocal()
        ct = CertificateType(code="PDFT", name="PDF Test", template="residency.html")
        db.add(ct)
        db.commit()
        db.refresh(ct)
        db.close()

        # issue certificate
        c = client.post(
            "/api/certificates/",
            json={"certificate_type_code": "PDFT", "resident_id": resident["id"]},
            headers=headers,
        )
        if c.status_code != 201:
            print("ISSUE_FAILED", c.status_code, c.text)
            return
        data = c.json()
        cert_id = data["id"]
        print("ISSUED:", data)

        # generate file (HTML + optional PDF)
        g = client.post(f"/api/certificates/{cert_id}/generate", headers=headers)
        print("GENERATE_RESP:", g.status_code, g.text)
        if g.status_code != 200:
            print("GENERATE_FAILED")
            return
        payload = g.json()
        path = payload.get("pdf_path")
        print("STORED_PATH:", path)

        # verify DB record
        db2 = TestingSessionLocal()
        ci = db2.get(CertificateIssue, cert_id)
        print("DB_PDF_PATH:", ci.pdf_path)
        db2.close()

        import os

        print("FILE_EXISTS:", os.path.exists(ci.pdf_path) if ci.pdf_path else False)

    print("PDF_TEST_DONE")


if __name__ == "__main__":
    run()
