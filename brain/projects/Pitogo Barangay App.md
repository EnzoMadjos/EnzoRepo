# Pitogo Barangay App

tags: [project, pitogo, fastapi, barangay]

## Overview

Admin app for barangay (Philippine village) — document printing, clearances, certificates.

## Status: PAUSED — awaiting tester feedback (2026-05-02)

## Tech

- Python FastAPI + Uvicorn, Port 8300
- Jinja2 templates for document rendering
- P2P LAN leader/client auto-election (UDP broadcast, port 50300)
- Local auth: `secure/users.json` (hashed, default admin/admin123)
- SQLite DB: `secure/pitogo.db`
- Alembic migrations, psycopg2-binary, sync_engine.py (offline fallback)
- Signed patch delivery: `patch_signing.py` + `cryptography` dep

## Key paths

- App root: `projects/pitogo-app/`
- Templates: `projects/pitogo-app/templates/`
- Source docs: `projects/pitogo-app/templates/docs/source_documents/`
- Cert stubs: `projects/pitogo-app/templates/certs/`
- Schemas: `projects/pitogo-app/schemas.py`

## Run

```bash
cd projects/pitogo-app && uvicorn app:app --port 8300
```

## Live demo

- URL: https://enzo-wsl.tail99e322.ts.net
- Creds: demo/1234, role=clerk

## Pending

- [ ] Tester feedback
- [ ] Crypto patch signing enforcement
- [ ] Multi-machine discovery/failover test
- [ ] Windows installer
- [ ] User management UI

## Commits

- Scaffold (15925e9) — initial commit
- DB centralization (d84d2ae) — psycopg2, config.get_database_url(), sync_engine.py
- Docker compose (8d16989) — postgres+app profiles, .env.example, install scripts

## Related

- [[Projects Index]]
- [[Workspace Patterns]]
