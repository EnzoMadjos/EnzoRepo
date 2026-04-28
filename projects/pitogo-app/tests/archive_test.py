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

import os

import api.deps as deps
import app_logger
import auth
import config
from app import app
from models import Base


def run():
    # Setup in-memory DB
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

    # clear any existing archives/logs to keep test deterministic
    try:
        app_logger.clear_logs()
    except Exception:
        pass
    # ensure archive dir exists and is clean
    config.LOG_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # remove old archives
    for p in config.LOG_ARCHIVE_DIR.glob("pitogo_logs_*"):
        try:
            p.unlink()
        except Exception:
            pass

    with TestClient(app) as client:
        token = auth.create_session("archivertester", "admin", "Archive Tester")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # write some logs
        app_logger.info("alpha entry", tag="alpha")
        app_logger.info("special match entry", category="special")
        app_logger.warn("a warning", reason="test")

        # POST archive request with JSON body filters
        body = {"q": "special", "format": "json", "clear_after": False}
        r = client.post("/admin/logs/archive", json=body, headers=headers)
        print("ARCHIVE_RESP:", r.status_code, r.text)
        if r.status_code != 200:
            print("ARCHIVE_FAILED")
            return
        j = r.json()
        archive_path = j.get("archive")
        download_url = j.get("download_url")
        print("ARCHIVE_PATH:", archive_path)
        assert archive_path and Path(archive_path).exists(), "archive file not created"

        # verify archive content contains the filtered entry
        txt = Path(archive_path).read_text(encoding="utf-8")
        assert "special match entry" in txt or "special" in txt, (
            "filtered log not present in archive"
        )

        # try to download via archive endpoint (requires auth)
        if download_url:
            g = client.get(download_url, headers=headers)
            print("DOWNLOAD_RESP:", g.status_code)
            assert g.status_code == 200, "failed to GET archive via download_url"

    print("ARCHIVE_TEST_DONE")


if __name__ == "__main__":
    run()
