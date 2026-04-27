# Council of AppDev — Architect Plan
## Barangay Pitogo Management System (BrgyOS)
### Assessment Date: 2026-04-27 | Architect Agent Output

---

## 1. App Name & Vision

**App Name:** `BrgyOS — Barangay Pitogo Operations System`

**Vision:**
A fully web-based, LAN-deployable, open-source Barangay Management System that replaces Pitogo1.0.accdb with a multi-user, role-aware, audit-logged platform. It handles resident census management, document certificate generation, business permit tracking, and demographic reporting — all accessible from any device inside the barangay hall's network without any Windows dependency.

**Design Principles:**
- Zero-license cost (fully open-source stack)
- Offline-first for LAN; cloud-sync optional
- One-click certificate PDF generation for all 30+ document types
- Clean, Tagalog-friendly UI that non-technical staff can operate
- Full audit trail on every record creation, edit, and deletion

---

## 2. Recommended Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI | Async, auto-docs (Swagger), excellent PDF/template support, dev team fluency |
| **Frontend** | React 18 + TypeScript + Vite | Component reuse for 30+ cert forms, fast HMR, TailwindCSS for clean UI |
| **Database** | PostgreSQL 16 | ACID compliant, full-text search, JSONB for dynamic cert fields, free |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | Migration-safe, typed models |
| **Auth** | FastAPI-Users + JWT (HS256) | Session-based with refresh tokens, bcrypt hashing |
| **PDF Engine** | WeasyPrint + Jinja2 HTML templates | HTML→PDF pipeline, no MS Office dependency |
| **Containerization** | Docker + Docker Compose | Single `docker compose up` deployment at barangay hall |
| **Reverse Proxy** | Caddy (LAN) | Auto-HTTPS on LAN with self-signed cert, zero config |
| **Cache/Session** | Redis 7 | Session tokens, rate limiting |
| **Backup** | pg_dump → rclone → Google Drive (optional) | Automated nightly offsite backup |
| **Dev LLM Routing** | GPT-4.1 Mini (coding) / GPT-4.1 (review) via RTK | Cost-optimized agent loop |

---

## 3. Data Model

### 3.1 Core Entities

#### `residents` (replaces HouseholdMembers)
```
id                  UUID PK
household_id        FK → households
purok_id            FK → puroks
sitio               VARCHAR(100)
last_name           VARCHAR(100) NOT NULL
first_name          VARCHAR(100) NOT NULL
middle_name         VARCHAR(100)
suffix              VARCHAR(20)          -- Jr, Sr, III
place_of_birth      VARCHAR(200)
date_of_birth       DATE NOT NULL
sex                 ENUM('M','F','Other')
civil_status        ENUM('Single','Married','Widowed','Separated','Live-in')
blood_type          ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-','Unknown')
citizenship         VARCHAR(100) DEFAULT 'Filipino'
religion            VARCHAR(100)
education_id        FK → education_levels
occupation_id       FK → occupations
monthly_income      NUMERIC(12,2)
relationship_id     FK → relationships
illness             TEXT
is_uct              BOOLEAN DEFAULT FALSE   -- Unconditional Cash Transfer
is_sap              BOOLEAN DEFAULT FALSE   -- Social Amelioration Program
is_4ps              BOOLEAN DEFAULT FALSE
is_pwd              BOOLEAN DEFAULT FALSE
pwd_type            VARCHAR(100)
is_senior           BOOLEAN DEFAULT FALSE   -- derived: age >= 60 or manually tagged
is_single_parent    BOOLEAN DEFAULT FALSE
first_vax_date      DATE
first_vax_type      VARCHAR(100)
second_vax_date     DATE
second_vax_type     VARCHAR(100)
first_booster_date  DATE
first_booster_type  VARCHAR(100)
second_booster_date DATE
second_booster_type VARCHAR(100)
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()
created_by          FK → users
updated_by          FK → users
```

#### `households` (replaces HouseholdMain)
```
id                  UUID PK
purok_id            FK → puroks
house_number        VARCHAR(50)
owner_name          VARCHAR(200)
status              ENUM('Owner','Renter','Shared')
toilet_type         VARCHAR(100)   -- Flush, Pit, None
water_source        VARCHAR(100)   -- NAWASA, Well, Spring, etc.
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()
```

#### `puroks`
```
id          SERIAL PK
code        VARCHAR(20) UNIQUE NOT NULL
name        VARCHAR(100) NOT NULL
```

#### `purok_demographics` (replaces PurokDemo — now computed view + snapshot)
```
id              SERIAL PK
purok_id        FK → puroks
snapshot_date   DATE NOT NULL
total_pop       INTEGER
male_count      INTEGER
female_count    INTEGER
household_count INTEGER
senior_count    INTEGER
pwd_count       INTEGER
uct_count       INTEGER
sap_count       INTEGER
fourps_count    INTEGER
vaccinated_count INTEGER
generated_by    FK → users
```

---

#### `businesses` (replaces BrgyBusinessRecords)
```
id                  UUID PK
business_name       VARCHAR(200) NOT NULL
owner_name          VARCHAR(200) NOT NULL
owner_resident_id   FK → residents (nullable — owner may be external)
address             TEXT
line_of_business_id FK → lines_of_business
nature_id           FK → business_natures
registration_date   DATE
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

#### `business_clearances` (replaces BrgyBusClearancePermit)
```
id              UUID PK
business_id     FK → businesses
clearance_no    VARCHAR(50) UNIQUE NOT NULL
issued_date     DATE NOT NULL
expiry_date     DATE
issued_by       FK → users
fee_id          FK → clearance_fees
amount_paid     NUMERIC(10,2)
or_number       VARCHAR(50)
purpose         TEXT
pdf_path        VARCHAR(500)
```

#### `business_tax_clearances` (replaces BrgyBusTaxClearanceIssued)
```
id              UUID PK
business_id     FK → businesses
tax_clearance_no VARCHAR(50) UNIQUE NOT NULL
taxable_year    SMALLINT
issued_date     DATE
fee_id          FK → clearance_fees
amount_paid     NUMERIC(10,2)
or_number       VARCHAR(50)
pdf_path        VARCHAR(500)
issued_by       FK → users
```

#### `clearance_fees` (replaces BCFee)
```
id              SERIAL PK
certificate_type VARCHAR(100) NOT NULL
amount          NUMERIC(10,2) NOT NULL
effective_date  DATE NOT NULL
is_current      BOOLEAN DEFAULT TRUE
created_by      FK → users
```

---

#### `certificates` (unified issuance log for all 30+ types)
```
id                  UUID PK
cert_type           VARCHAR(100) NOT NULL  -- enum-like: 'CLEARANCE','RESIDENCY','INDIGENCY', etc.
control_no          VARCHAR(50) UNIQUE NOT NULL
resident_id         FK → residents (nullable for business certs)
business_id         FK → businesses (nullable)
issued_to           VARCHAR(200) NOT NULL   -- denormalized name for quick display
purpose             TEXT
validity_months     SMALLINT DEFAULT 6
issued_date         DATE NOT NULL
expiry_date         DATE
certifying_officer_id FK → barangay_officers
issued_by           FK → users
fee_id              FK → clearance_fees (nullable — some certs are free)
amount_paid         NUMERIC(10,2) DEFAULT 0
or_number           VARCHAR(50)
cert_data           JSONB NOT NULL          -- all cert-specific dynamic fields
pdf_path            VARCHAR(500)
is_void             BOOLEAN DEFAULT FALSE
void_reason         TEXT
void_by             FK → users
void_at             TIMESTAMPTZ
created_at          TIMESTAMPTZ DEFAULT NOW()
```

> **Design decision:** `cert_data` JSONB allows each of the 30+ certificate types to carry its own fields (e.g., cohabitation cert needs partner name + duration; construction clearance needs lot number + floor area) without separate tables per cert. A Pydantic schema per cert type enforces validation before write.

---

#### `barangay_officers` (replaces BrgyOfficers)
```
id              UUID PK
name            VARCHAR(200) NOT NULL
position        VARCHAR(100)    -- Barangay Captain, Kagawad, Secretary, Treasurer, etc.
term_start      DATE
term_end        DATE
signature_path  VARCHAR(500)    -- path to scanned signature image for PDF stamping
is_active       BOOLEAN DEFAULT TRUE
```

#### `users`
```
id              UUID PK
username        VARCHAR(100) UNIQUE NOT NULL
email           VARCHAR(200) UNIQUE
hashed_password VARCHAR(200) NOT NULL
role            ENUM('superadmin','admin','encoder','officer','viewer') NOT NULL
full_name       VARCHAR(200)
is_active       BOOLEAN DEFAULT TRUE
last_login      TIMESTAMPTZ
created_at      TIMESTAMPTZ
```

#### `audit_logs`
```
id              BIGSERIAL PK
user_id         FK → users
action          VARCHAR(50)     -- CREATE, UPDATE, DELETE, LOGIN, LOGOUT, PRINT
resource_type   VARCHAR(100)    -- 'resident', 'certificate', 'business', etc.
resource_id     UUID
old_data        JSONB
new_data        JSONB
ip_address      INET
user_agent      VARCHAR(500)
timestamp       TIMESTAMPTZ DEFAULT NOW()
```

### 3.2 Lookup Tables
All lookup tables follow the same minimal pattern:
```
id    SERIAL PK
code  VARCHAR(50) UNIQUE
name  VARCHAR(200) NOT NULL
```
- `education_levels` (replaces Education)
- `occupations` (replaces Occupation)
- `relationships` (replaces Relationship)
- `lines_of_business` (replaces LineOfBusiness)
- `business_natures` (replaces Nature)

---

## 4. Module Breakdown

### Module 1 — Authentication & User Management
- Login / Logout with JWT + refresh token
- User CRUD (superadmin only)
- Role assignment
- Session timeout (configurable, default 30 min)
- Audit log viewer (admin+)

### Module 2 — Resident Census (Core)
- Register new resident → household
- Search residents (name, purok, sitio, birthday, special tags)
- Edit/update resident profile
- Soft-delete (deactivate) with reason
- Bulk import from CSV (migration from Access data export)
- Resident detail view with all certificate history
- Tag management: 4Ps, PWD, Senior, Single Parent, UCT, SAP, vaccination status

### Module 3 — Household Management
- Register new household
- Assign/transfer household members
- View household composition
- Edit toilet/water source/status

### Module 4 — Certificate Issuance (30+ types)
- Unified certificate issuance form with per-type dynamic fields
- Auto-generate control number (format: `BRGY-PITOGO-{YEAR}-{TYPE_CODE}-{SEQ}`)
- Officer selection (populates certifying officer on PDF)
- Fee lookup + OR number entry
- One-click PDF generation and print
- Void/cancel with reason
- Certificate search and reprint
- Certificate type config (admin can toggle active types, set fees)

### Module 5 — Business Management
- Business registry CRUD
- Issue business clearance (forms + PDF)
- Issue business tax clearance
- Renewal tracking with expiry alerts
- Business search and status dashboard

### Module 6 — Barangay Officers
- Officer roster management with term tracking
- Upload/manage signature images (used in PDF footer)
- Active officer selection for certificate signing

### Module 7 — Demographics & Reports
- Live purok demographic summary (residents by sex, age group, tags)
- Vaccination coverage chart
- Monthly certificate issuance counts by type
- Business registry summary
- Export to Excel/CSV
- Snapshot: save current demographics for record

### Module 8 — System Administration
- Fee rate management (clearance fees by type)
- Lookup table CRUD (education, occupation, etc.)
- Backup trigger (manual pg_dump download)
- System settings (barangay name, logo, LGU, contact)
- User activity logs

---

## 5. Certificate Generation Strategy

### Architecture
```
React Form (per cert type)
  → POST /api/certificates/issue
    → Pydantic schema validation (per type)
    → Insert certificates row (cert_data JSONB)
    → Render Jinja2 HTML template
    → WeasyPrint → PDF bytes
    → Save to /data/certs/{year}/{type}/{control_no}.pdf
    → Return PDF stream to browser (opens print dialog)
```

### Template Organization
```
/templates/certs/
  base_cert.html           ← header, barangay seal, officer footer, OR section
  clearance.html
  residency.html
  cohabitation.html
  no_flood.html
  construction_clearance.html
  indigency.html
  senior_citizen.html
  pwd.html
  ... (one per type, extends base_cert.html)
```

### Control Number Format
`BP-{YYYY}-{TYPE_CODE}-{NNNNNN}`
Example: `BP-2026-CLR-000047` (Clearance #47 in 2026)

### Key Design Decisions
1. **Base template** carries: barangay seal (image), LGU name, "Republic of the Philippines", certifying officer name+position+signature, date, OR number block, validity notice.
2. **Per-type templates** inherit base and only define the certificate body paragraph — keeping template maintenance simple.
3. **Dynamic fields** stored as `cert_data JSONB` allow future cert types to be added by adding one Pydantic schema + one HTML template, with zero DB migration.
4. **WeasyPrint** is chosen over ReportLab because HTML/CSS templates are maintainable by non-developers. Fonts: embedded Noto Sans Filipino.
5. Printed PDFs are stored locally on the server disk organized by year/type for reprints.

---

## 6. Authentication & Role-Based Access

### Roles

| Role | Access |
|---|---|
| `superadmin` | All modules, user management, system settings, audit logs |
| `admin` | All modules except user management; can void certificates |
| `encoder` | Resident/household CRUD, certificate issuance, business CRUD |
| `officer` | Read-only all data + issue certificates (their name appears as certifier) |
| `viewer` | Read-only: resident search, demographics, certificate lookup |

### Auth Implementation
- Passwords hashed with bcrypt (cost factor 12)
- JWT access token: 60-minute expiry
- JWT refresh token: 7-day expiry, stored in HttpOnly cookie
- Login rate-limit: 5 failed attempts → 15-minute lockout (Redis counter)
- All API routes protected by `Depends(get_current_user)` + role decorator
- HTTPS enforced by Caddy even on LAN (self-signed cert, shared with staff devices)

### Audit Trail
Every write operation (INSERT/UPDATE/DELETE on residents, certificates, businesses) fires a FastAPI background task that writes to `audit_logs` with old/new JSONB snapshots. Non-repudiable.

---

## 7. Deployment Architecture

### LAN Deployment (Primary)
```
Barangay Hall LAN (192.168.x.x)
  ┌────────────────────────────────────────────────────┐
  │  Server: Any PC/mini-PC with Ubuntu Server 22.04   │
  │  RAM: 4GB minimum, 8GB recommended                 │
  │  Storage: 120GB SSD                                │
  │                                                    │
  │  Docker Compose stack:                             │
  │  ┌────────────┐  ┌──────────┐  ┌───────────────┐  │
  │  │  Caddy     │  │ FastAPI  │  │  PostgreSQL   │  │
  │  │  :80/:443  │→ │  :8000   │  │  :5432        │  │
  │  └────────────┘  └──────────┘  └───────────────┘  │
  │                       ↑              ↑             │
  │                  ┌────────┐   ┌───────────┐        │
  │                  │ Redis  │   │  /data/   │        │
  │                  │  :6379 │   │  volume   │        │
  │                  └────────┘   └───────────┘        │
  └────────────────────────────────────────────────────┘
         ↑ accessed by any browser on the LAN
         Staff PCs, tablets, phones → https://brgyos.local
```

### Docker Compose Services
```yaml
services:
  caddy:      image: caddy:2-alpine
  api:        build: ./backend   (FastAPI)
  frontend:   build: ./frontend  (React, served as static via Caddy)
  db:         image: postgres:16-alpine
  redis:      image: redis:7-alpine
```

### Backup Strategy
1. **Daily automated:** `pg_dump` cron inside `api` container → compressed `.sql.gz` saved to `/data/backups/`
2. **Weekly offsite:** `rclone sync` to a shared Google Drive folder (configured once by admin)
3. **Manual on-demand:** Admin can trigger a backup download from the System Admin module
4. **Retention:** Keep last 30 daily + last 12 weekly backups

### Server Requirements (budget LGU-friendly)
- Any PC with 4-core CPU, 8GB RAM, 120GB SSD running Ubuntu Server 22.04 LTS
- Alternatively: Raspberry Pi 5 (8GB) for ultra-low power
- Cost: ~₱8,000–₱15,000 for mini-PC (secondhand eligible)

---

## 8. Agent Workflow

```
ARCHITECT (this document)
  ↓ hands off:
    - Full data model (Section 3)
    - Module specs (Section 4)
    - API route list (Appendix A)
    - DB migration scripts outline (Appendix B)

CODE ASSISTANT
  Phase 1: Backend scaffold
    - FastAPI project structure
    - SQLAlchemy models (all entities above)
    - Alembic initial migration
    - Auth module (JWT, roles, rate-limiting)
    - Residents CRUD API
    - Households CRUD API
    - Certificates issuance API + PDF generation
    rtk cargo|pytest → filtered test output

  Phase 2: Frontend scaffold
    - React + Vite + TailwindCSS project
    - Auth pages (login, session timeout)
    - Resident search + form pages
    - Certificate issuance flow (per-type forms)
    - Dashboard/demographics page
    rtk npm test → filtered output

  Phase 3: Integration
    - Docker Compose wiring
    - Caddy config
    - Data migration scripts (from Access CSV export)

TEST ENGINEER
  - Unit tests: each API route (pytest + httpx AsyncClient)
  - Integration tests: certificate issuance end-to-end (form → PDF file created)
  - Auth tests: role enforcement, rate-limit, token expiry
  - DB tests: audit log writes on every mutation
  - Test coverage target: 80%+
  rtk pytest --cov → filtered coverage report

DEPLOYMENT OFFICER
  - docker-compose.prod.yml with health checks
  - Caddy Caddyfile for brgyos.local
  - Systemd unit: auto-start on boot
  - pg_dump backup cron + rclone config guide
  - Staff onboarding script: auto-creates default admin user on first start
  - Data migration runbook: export Access → CSV → run import script
  rtk docker compose up --build → filtered logs
```

---

## 9. Development Phases

### Phase 1 — Core Foundation (Weeks 1–4)
**Goal:** Running backend with auth + resident census + basic cert issuance

Deliverables:
- [ ] PostgreSQL schema deployed via Alembic
- [ ] FastAPI backend with JWT auth, all RBAC roles enforced
- [ ] Residents CRUD API (create, read, update, soft-delete, search)
- [ ] Households CRUD API
- [ ] Certificates: Barangay Clearance + Residency + Indigency (3 types as pilot)
- [ ] PDF generation working for those 3 types
- [ ] Basic React frontend: login + resident search + cert issuance form
- [ ] Docker Compose: all services running locally

**Success Criteria:** Staff can log in, search a resident, and print a Barangay Clearance as PDF.

---

### Phase 2 — Full Certificate Suite + Business Module (Weeks 5–9)
**Goal:** All 30+ cert types + business tracking

Deliverables:
- [ ] All 30+ certificate Jinja2 templates + Pydantic schemas
- [ ] Certificate control number auto-generation
- [ ] Certificate void/reprint workflow
- [ ] Business registry CRUD
- [ ] Business clearance + tax clearance issuance + PDF
- [ ] Fee management module
- [ ] Barangay Officers module (roster + signature upload)
- [ ] Full React UI for all modules
- [ ] Data migration script: Access CSV → PostgreSQL (import tool in admin panel)

**Success Criteria:** All legacy certificate types issuable; business records imported from Access.

---

### Phase 3 — Analytics, Hardening & LAN Deploy (Weeks 10–14)
**Goal:** Production-ready LAN deployment with full reports and audit

Deliverables:
- [ ] Demographics dashboard (charts: population by purok, sex, age group, vaccination)
- [ ] Monthly reports (cert issuance volume, business count)
- [ ] Audit log viewer in admin panel
- [ ] Automated daily backup (pg_dump + optional rclone)
- [ ] Caddy HTTPS on LAN (`brgyos.local`)
- [ ] Systemd auto-start on server reboot
- [ ] Staff training documentation (Tagalog user guide PDF)
- [ ] Security review: OWASP Top 10 checklist pass

**Success Criteria:** Live at barangay hall; old Access app retired; staff using system daily.

---

## 10. Token / Cost Optimization

### RTK CLI Usage
All agents **must** prefix shell commands with `rtk`:
```bash
rtk pytest -v                     # filtered test output (saves ~70% tokens)
rtk docker compose up --build     # filtered docker logs
rtk git status                    # compressed git state
rtk alembic upgrade head          # migration output filtered
rtk npm run build                 # Vite build output filtered
```

### LLM Routing Strategy

| Task | Model | Rationale |
|---|---|---|
| Boilerplate CRUD generation | GPT-4.1 Mini | Fast, cheap, templatable |
| Jinja2 cert template coding | GPT-4.1 Mini | Repetitive pattern |
| Pydantic schema per cert type | GPT-4.1 Mini | Schema pattern, 30+ iterations |
| Alembic migration scripts | GPT-4.1 Mini | Mechanical transformation |
| Security review (auth, RBAC) | GPT-4.1 | High-stakes, needs reasoning |
| Architecture decisions | GPT-4.1 | This document |
| Test strategy design | GPT-4.1 | Needs context + judgment |
| Code review before Phase deploy | GPT-4.1 | Final QA gate |

**Estimated savings:** Using Mini for ~70% of coding tasks cuts token cost by ~4x vs. using GPT-4.1 for everything.

### Practical Cost Tips
1. Pass only the relevant file/model to the Code Assistant, not the full codebase. Use `rtk gain` to verify.
2. During Phase 2's 30-cert loop: generate all Pydantic schemas in one batch prompt; generate all Jinja2 templates in one batch prompt.
3. Test Engineer uses `rtk pytest --tb=short` to minimize failure output tokens.
4. Use `rtk discover` weekly to catch any missed optimization opportunities.

---

## Appendix A — Key API Routes

```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh

GET    /api/residents              ?q=&purok_id=&tag=&page=
POST   /api/residents
GET    /api/residents/{id}
PUT    /api/residents/{id}
DELETE /api/residents/{id}         (soft delete)

GET    /api/households
POST   /api/households
GET    /api/households/{id}
PUT    /api/households/{id}

GET    /api/certificates           ?type=&resident_id=&date_from=&date_to=
POST   /api/certificates/issue
GET    /api/certificates/{id}
GET    /api/certificates/{id}/pdf  → streams PDF
POST   /api/certificates/{id}/void
GET    /api/certificates/types     → list of active cert types + fees

GET    /api/businesses
POST   /api/businesses
GET    /api/businesses/{id}
PUT    /api/businesses/{id}

POST   /api/businesses/{id}/clearance
GET    /api/businesses/{id}/clearance/{cid}/pdf
POST   /api/businesses/{id}/tax-clearance
GET    /api/businesses/{id}/tax-clearance/{tid}/pdf

GET    /api/reports/demographics
GET    /api/reports/purok/{id}
GET    /api/reports/certificates/monthly
GET    /api/reports/businesses

GET    /api/admin/users
POST   /api/admin/users
PUT    /api/admin/users/{id}
GET    /api/admin/audit-logs
GET    /api/admin/backup/download

GET    /api/lookup/puroks
GET    /api/lookup/education
GET    /api/lookup/occupations
GET    /api/lookup/relationships
GET    /api/lookup/lines-of-business
GET    /api/lookup/business-natures
GET    /api/lookup/fees
```

---

## Appendix B — Migration Plan (Access → PostgreSQL)

### Step-by-step

1. **Export from Access:** Export all tables to CSV via Access → External Data → Excel/CSV
2. **Run migration tool** (`/admin/import` in BrgyOS):
   - Upload CSVs per table
   - System maps columns to new schema (pre-built mapping config)
   - Validates data types, flags errors (e.g., invalid dates)
   - Shows preview + row count before committing
3. **Commit import:** Writes to PostgreSQL in a transaction; rolls back entirely on error
4. **Verify:** Spot-check 20 random residents in new system vs. Access
5. **Freeze Access:** Print final report from Access, then seal the .accdb file as archive

### Column Mapping (HouseholdMembers → residents)
| Access Column | New Column | Notes |
|---|---|---|
| Id | (discarded) | UUID auto-generated |
| SITIO | sitio | direct |
| PUROK | purok_id | lookup puroks.code |
| HseNum | household.house_number | join to households |
| lastname | last_name | direct |
| firstname | first_name | direct |
| middlename | middle_name | direct |
| PLACEOFBIRTH | place_of_birth | direct |
| DATEOFBIRTH | date_of_birth | parse multiple date formats |
| SEX | sex | normalize M/F/Male/Female |
| CIVILSTATUS | civil_status | normalize |
| BLOODTYPE | blood_type | normalize |
| ILLNESS | illness | direct |
| EDUCATION | education_id | lookup education_levels |
| RELIGION | religion | direct |
| OCCUPATION | occupation_id | lookup occupations |
| INCOMEMONTHLY | monthly_income | cast to NUMERIC |
| RELATIONSHIP | relationship_id | lookup relationships |
| UCT | is_uct | BOOLEAN |
| SAP | is_sap | BOOLEAN |
| 4PS | is_4ps | BOOLEAN |
| PWD | is_pwd | BOOLEAN |
| FIRSTDOSE + type | first_vax_date / first_vax_type | split |
| SECONDDOSE + type | second_vax_date / second_vax_type | split |
| FIRSTBOOSTER + type | first_booster_date / first_booster_type | split |
| SECONDBOOSTER + type | second_booster_date / second_booster_type | split |
| CITIZENSHIP | citizenship | direct |

### Rollback Plan
- Access `.accdb` file is **never deleted** — kept as read-only archive
- PostgreSQL migration runs **in a transaction** — any error rolls back 100%
- BrgyOS runs **alongside** Access for 2-week parallel period; staff verify data parity
- After parallel period approval by barangay captain: Access officially retired

---

## Appendix C — Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Staff resistance to new system | High | Tagalog UI, in-person training, parallel run period |
| Power outage during LAN use | Medium | UPS on server; PostgreSQL WAL ensures no data loss on dirty shutdown |
| Internet down = no cloud backup | Low | Primary data is on-site; cloud backup is optional supplement |
| Date format inconsistency in legacy data | Medium | Migration parser handles multiple formats; errors surfaced in review step |
| Signature images for all officers not available | Low | Cert PDFs work without signature image (placeholder "for signature" text) |
| WeasyPrint CSS rendering quirks | Low | Tested in Phase 1 pilot before all 30 templates are built |
| JSONB cert_data query performance | Low | Indexed on cert_type + issued_date; full-text rarely needed on cert_data |
| 30+ cert Pydantic schemas maintenance burden | Medium | Shared base schema + type-specific mixin pattern; documented in code |

---

*Plan produced by Architect Agent — Council of AppDev*
*Hand off to: Code Assistant (Phase 1 backend scaffold)*
*Reviewed by: GPT-4.1 (security + architecture review gate)*
