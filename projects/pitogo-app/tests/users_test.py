import sys
from pathlib import Path
import shutil

# Ensure imports from project work
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

    original_get_db = deps.get_db
    app.dependency_overrides[original_get_db] = override_get_db

    # backup users file if present
    users_path = auth._USERS_FILE
    bak = None
    if users_path.exists():
        bak = users_path.with_suffix('.json.bak')
        shutil.copy2(users_path, bak)

    try:
        with TestClient(app) as client:
            admin_token = auth.create_session('tester', 'admin', 'Tester')
            headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}

            # list users (should include admin)
            r = client.get('/api/users/', headers=headers)
            assert r.status_code == 200

            # create a new user
            r = client.post('/api/users/', json={'username': 'alice', 'password': 'alicepw', 'role': 'clerk', 'display_name': 'Alice'}, headers=headers)
            assert r.status_code == 201, r.text

            # search/list pagination
            r = client.get('/api/users/?q=alice&page=1&per_page=10', headers=headers)
            assert r.status_code == 200
            data = r.json()
            assert data.get('total', 0) >= 1

            # admin reset alice password
            r = client.post('/api/users/alice/password', json={'new_password': 'newalice'}, headers=headers)
            assert r.status_code == 200

            # login as alice with new password
            r = client.post('/auth/login', json={'username': 'alice', 'password': 'newalice'})
            assert r.status_code == 200
            alice_token = r.json().get('token')
            assert alice_token

            # alice change own password (needs current)
            r = client.post('/api/users/alice/password', json={'new_password': 'alice2', 'current_password': 'newalice'}, headers={'Authorization': f'Bearer {alice_token}', 'Content-Type': 'application/json'})
            assert r.status_code == 200

            # delete alice as admin
            r = client.delete('/api/users/alice', headers=headers)
            assert r.status_code == 200

    finally:
        # restore users file
        if bak and bak.exists():
            shutil.copy2(bak, users_path)
            bak.unlink()

    print('USERS_TESTS_PASSED')


if __name__ == '__main__':
    run()
