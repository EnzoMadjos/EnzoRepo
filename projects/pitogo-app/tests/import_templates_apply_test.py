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

    with TestClient(app) as client:
        token = auth.create_session("imptester3", "admin", "Import Tester 3")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # simulate
        body = {"dry_run": True, "convert": False, "inject": True}
        r = client.post('/admin/templates/import', json=body, headers=headers)
        if r.status_code != 200:
            print('SIM_FAILED', r.status_code, r.text); return
        j = r.json()
        simulated = j.get('simulated_changes', [])
        if not simulated:
            print('NO_SIMULATED_CHANGES, nothing to apply')
            print('IMPORT_APPLY_TEST_DONE')
            return
        target = simulated[0]['file']
        print('WILL_APPLY:', target)

        # ensure no pre-existing .bak (remove for test cleanliness)
        bak = config.BASE_DIR / 'templates' / 'certs' / (Path(target).name + '.bak')
        try:
            if bak.exists(): bak.unlink()
        except Exception:
            pass

        # apply single file
        ar = {"files": [target], "apply_all": False, "convert": False}
        a = client.post('/admin/templates/apply', json=ar, headers=headers)
        print('APPLY_RESP:', a.status_code, a.text)
        if a.status_code != 200:
            print('APPLY_FAILED')
            return
        aj = a.json()
        assert target in aj.get('patched', [])
        # check backup exists
        bak2 = config.BASE_DIR / 'templates' / 'certs' / (Path(target).name + '.bak')
        assert bak2.exists(), 'backup not created'

    print('IMPORT_APPLY_TEST_DONE')


if __name__ == '__main__':
    run()
