import sys
from pathlib import Path

# Ensure project package imports work
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
from models import Base, CertificateType


def run():
    # In-memory DB for tests
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

    original_get_db = deps.get_db
    app.dependency_overrides[original_get_db] = override_get_db

    with TestClient(app) as client:
        token = auth.create_session("tester", "admin", "Tester")
        headers = {"Authorization": f"Bearer {token}"}

        # Create resident
        r = client.post(
            "/api/residents/",
            json={"first_name": "Jane", "last_name": "Doe"},
            headers=headers,
        )
        assert r.status_code == 201, f"create resident failed: {r.status_code} {r.text}"
        resident = r.json()

        # Create certificate type in DB directly
        db = TestingSessionLocal()
        ct = CertificateType(code="RES", name="Residency", template="residency.html")
        db.add(ct)
        db.commit()
        db.refresh(ct)
        db.close()

        # Issue certificate
        c = client.post(
            "/api/certificates/",
            json={"certificate_type_code": "RES", "resident_id": resident["id"]},
            headers=headers,
        )
        assert c.status_code == 201, (
            f"issue certificate failed: {c.status_code} {c.text}"
        )
        data = c.json()
        assert "control_number" in data

    print("ALL_TESTS_PASSED")


if __name__ == "__main__":
    run()
