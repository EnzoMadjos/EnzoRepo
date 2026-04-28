import sys
from pathlib import Path

# Ensure project imports work
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import discovery
discovery.start = lambda *args, **kwargs: None
discovery.stop = lambda *args, **kwargs: None

from app import app
import api.deps as deps
import auth
from models import Base
import config


def run():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
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

    dst = config.BASE_DIR / 'templates' / 'certs'
    target = 'barangay_clearance.html'
    bak = dst / (target + '.bak')

    with TestClient(app) as client:
        token = auth.create_session("imptester4", "admin", "Import Tester 4")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # require that a .bak exists from previous apply; if not, run apply for the file first
        if not bak.exists():
            ar = {"files": [target], "apply_all": False, "convert": False}
            a = client.post('/admin/templates/apply', json=ar, headers=headers)
            if a.status_code != 200:
                print('SETUP_APPLY_FAILED', a.status_code, a.text)
                return

        assert bak.exists(), 'setup failed to create backup'

        # perform undo
        ur = {"files": [target], "undo_all": False}
        u = client.post('/admin/templates/undo', json=ur, headers=headers)
        print('UNDO_RESP:', u.status_code, u.text)
        if u.status_code != 200:
            print('UNDO_FAILED')
            return
        uj = u.json()
        assert target in uj.get('restored', [])
        assert not bak.exists(), 'bak not removed after undo'

    print('IMPORT_UNDO_TEST_DONE')


if __name__ == '__main__':
    run()
