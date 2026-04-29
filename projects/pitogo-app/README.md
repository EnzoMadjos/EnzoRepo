# PITOGO Barangay App

FastAPI-based records management system for a Philippine barangay — residents, households, certificate issuance, PDF generation, and audit logging.

## Features

- Multi-user auth (admin / clerk roles, session tokens)
- Resident and household registry with fast search
- Certificate issuance: Barangay Clearance, Residency, Indigency, Business Clearance, and more
- PDF rendering via WeasyPrint
- Audit log viewer with CSV/JSON/ZIP export
- Peer discovery (LAN leader election — run multiple instances, one auto-becomes leader)
- Signed update delivery (`patch.zip`)
- Dockerized, deployed via GitHub Actions → Tailscale → SSH

---

## Quick Start (local dev)

### Prerequisites

```bash
python 3.12+
pip install -r requirements.txt
```

### Init and seed the database

```bash
python manage.py init-db
python manage.py seed        # inserts default certificate types + admin user
```

### Run the app

```bash
uvicorn app:app --host 0.0.0.0 --port 8300 --reload
```

Open http://localhost:8300 — default credentials: `admin` / `admin123` (change on first login).

### Run tests

```bash
python tests/run_tests.py        # core: residents, certificates
python tests/users_test.py       # user management
python tests/generate_pdf_test.py
```

---

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `PITOGO Barangay App` | App display name |
| `APP_PORT` | `8300` | Port to listen on |
| `SESSION_EXPIRE_HOURS` | `12` | Session token TTL |
| `BRGY_CODE` | `PITOGO` | Used in control number generation |
| `DISCOVERY_PORT` | `50300` | UDP port for peer discovery |
| `DISCOVERY_TIMEOUT_SEC` | `2.0` | Seconds before self-electing as leader |
| `HEARTBEAT_INTERVAL` | `5.0` | Leader heartbeat frequency |
| `HEARTBEAT_MISSES` | `3` | Misses before re-election |
| `RELAY_URL` | _(empty)_ | Support relay endpoint |
| `RELAY_TOKEN` | _(empty)_ | Bearer token for relay |
| `LOG_WEBHOOK_URL` | _(empty)_ | Discord/Slack webhook for error alerts |
| `UPDATE_URL` | _(empty)_ | URL for checking signed app updates |
| `DOWNLOAD_SECRET` | _(empty)_ | HMAC secret for signed download URLs |

---

## Docker

```bash
docker build -t pitogo-app .
docker run -p 80:8300 \
  -v $(pwd)/secure:/app/secure \
  --env-file .env \
  pitogo-app
```

Or use `docker-compose.yml`:

```bash
docker compose up -d
```

---

## Deployment (CI/CD)

Every push to `main` triggers `.github/workflows/deploy.yml`:

1. Build Docker image → push to GHCR (`ghcr.io/enzomadjos/enzo-repo:latest`)
2. Connect GitHub Actions runner to your machine via Tailscale
3. SCP updated `docker-compose.yml` to `~/enzo-app/`
4. SSH → `docker compose pull && docker compose up -d --remove-orphans`
5. Health check on `/status`
6. Notify result

### Required GitHub Secrets

| Secret | Value |
|---|---|
| `GHCR_TOKEN` | GitHub PAT with `write:packages` |
| `SSH_HOST` | Tailscale IP of deploy machine |
| `SSH_USER` | SSH username |
| `SSH_PRIVATE_KEY` | Ed25519 private key (passwordless) |
| `TAILSCALE_AUTHKEY` | Ephemeral reusable Tailscale auth key |

---

## API Reference

All endpoints (except `/status`, `/auth/login`, `/download/{token}`) require:

```
Authorization: Bearer <token>
```

Get a token from `POST /auth/login`.

---

### Auth

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/auth/login` | `{username, password}` | Returns `{token, username, role, display_name}` |
| `POST` | `/auth/logout` | — | Invalidates session |

---

### Residents — `/api/residents`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/residents/` | List residents (`?q=search&page=1&per_page=50`) |
| `POST` | `/api/residents/` | Create resident |
| `GET` | `/api/residents/{id}` | Get resident by ID |
| `PUT` | `/api/residents/{id}` | Update resident |
| `DELETE` | `/api/residents/{id}` | Delete resident |

**Resident fields:** `first_name`, `last_name`, `middle_name`, `birthdate` (ISO date), `contact_number`, `national_id`, `household_id`

---

### Households — `/api/households`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/households/` | List households (`?q=search`) |
| `POST` | `/api/households/` | Create household |
| `GET` | `/api/households/{id}` | Get household |
| `PUT` | `/api/households/{id}` | Update household |
| `DELETE` | `/api/households/{id}` | Delete household |

**Household fields:** `address_line`, `barangay`, `city`, `zip_code`, `head_resident_id`

---

### Certificate Types — `/api/certificate-types`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/certificate-types/` | List all certificate types |
| `POST` | `/api/certificate-types/` | Create certificate type (admin) |
| `PUT` | `/api/certificate-types/{id}` | Update |
| `DELETE` | `/api/certificate-types/{id}` | Delete (admin) |

**Fields:** `code` (unique), `name`, `template` (HTML template filename)

Built-in codes: `CLEAR`, `RESID`, `INDIG`, `BUSINESS`, `COHAB`, `SSS`

---

### Certificates — `/api/certificates`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/certificates/` | Issue a certificate → returns `{id, control_number, …}` |
| `GET` | `/api/certificates/` | List issued certificates (`?q=&resident_id=&type_id=&page=&per_page=`) |
| `GET` | `/api/certificates/{id}` | Get certificate by ID |
| `GET` | `/api/certificates/{id}/preview` | Render HTML preview |
| `POST` | `/api/certificates/{id}/generate` | Generate and save PDF → returns download URL |
| `GET` | `/api/certificates/{id}/download` | Redirect to signed PDF download |

**Issue request body:**
```json
{
  "certificate_type_code": "CLEAR",
  "resident_id": "<uuid>",
  "household_id": "<uuid>",
  "meta": { "purpose": "Employment" }
}
```

Control number format: `{BRGY_CODE}-{YYYYMMDD}-{NODE_SHORT}-{seq:04d}`

---

### Users — `/api/users`

| Method | Path | Role | Description |
|---|---|---|---|
| `GET` | `/api/users/` | admin | List users (`?q=&page=&per_page=`) |
| `GET` | `/api/users/me` | any | Current user info |
| `POST` | `/api/users/` | admin | Create user |
| `PUT` | `/api/users/{username}` | admin | Update role / display name |
| `POST` | `/api/users/{username}/password` | admin or self | Change/reset password |
| `DELETE` | `/api/users/{username}` | admin | Delete user |

**Roles:** `admin`, `clerk`

---

### Attachments — `/api/attachments`

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/attachments/` | Upload a file (multipart, `owner_type` + `owner_id` required) |
| `GET` | `/api/attachments/` | List attachments (`?owner_type=&owner_id=`) |
| `GET` | `/api/attachments/{id}` | Get attachment metadata |
| `GET` | `/api/attachments/{id}/download` | Download file |
| `DELETE` | `/api/attachments/{id}` | Delete attachment |

---

### Admin

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/logs` | Get logs (`?q=&level=INFO&start=&end=&page=&per_page=&format=csv`) |
| `POST` | `/admin/logs/archive` | Archive logs to file, returns download URL |
| `GET` | `/admin/archives/{filename}` | Download log archive |
| `POST` | `/admin/templates/import` | Import DOCX → HTML templates |
| `POST` | `/admin/templates/apply` | Apply placeholder injection to cert templates |
| `POST` | `/admin/templates/undo` | Restore `.bak` backups |

---

### System

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/status` | none | Server role, hostname, IP |
| `GET` | `/download/{token}` | none (signed) | Time-limited file download |

---

## Project Structure

```
pitogo-app/
├── app.py                  # FastAPI entry point, startup/shutdown
├── models.py               # SQLAlchemy models (Resident, Household, User, …)
├── db.py                   # SQLite engine + session factory
├── auth.py                 # Session auth (users.json + in-memory sessions)
├── config.py               # Env-based configuration
├── manage.py               # CLI: init-db, seed, create-sample
├── discovery.py            # UDP peer discovery / leader election
├── pdf_renderer.py         # WeasyPrint PDF generation
├── schemas.py              # Shared Pydantic schemas
├── patch_signing.py        # Signed patch.zip verification
├── node.py                 # Node ID generation (per machine)
├── api/
│   ├── residents.py
│   ├── households.py
│   ├── certificate_types.py
│   ├── certificates.py
│   ├── attachments.py
│   ├── users.py
│   └── deps.py             # FastAPI dependency: get_db
├── tests/
│   ├── run_tests.py        # Core test runner (residents, certificates)
│   ├── users_test.py
│   ├── generate_pdf_test.py
│   └── …
├── templates/
│   ├── index.html
│   ├── ui/                 # UI pages (residents, households, certificates, …)
│   ├── docs/               # Document templates (clearance, residency, indigency)
│   └── certs/              # Cert HTML templates
├── secure/                 # Data dir (gitignored): DB, users.json, session files
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
