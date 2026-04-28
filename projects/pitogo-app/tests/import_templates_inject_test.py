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
from models import Base


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
        token = auth.create_session("imptester2", "admin", "Import Tester 2")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        body = {"dry_run": True, "convert": False, "inject": True}
        r = client.post("/admin/templates/import", json=body, headers=headers)
        print("IMPORT_INJECT_RESP:", r.status_code, r.text)
        assert r.status_code == 200
        j = r.json()
        assert "simulated_changes" in j and isinstance(j["simulated_changes"], list)

    print("IMPORT_INJECT_TEST_DONE")


if __name__ == "__main__":
    run()
