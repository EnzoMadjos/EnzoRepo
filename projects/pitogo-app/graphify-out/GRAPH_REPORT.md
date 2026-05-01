# Graph Report - pitogo-app  (2026-05-01)

## Corpus Check
- 40 files · ~224,506 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 302 nodes · 481 edges · 24 communities detected
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 94 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]

## God Nodes (most connected - your core abstractions)
1. `CertificateType` - 44 edges
2. `Resident` - 18 edges
3. `Household` - 17 edges
4. `CertificateIssue` - 15 edges
5. `ok()` - 9 edges
6. `main()` - 7 edges
7. `GenerateRequest` - 7 edges
8. `_resident_dict()` - 7 edges
9. `handleResidents()` - 7 edges
10. `handleHouseholds()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `app.py — main FastAPI application for PITOGO Barangay App.  Includes:   - Login` --uses--> `CertificateType`  [INFERRED]
  app.py → models.py
- `Simple issuance form: select resident and certificate type, preview and generate` --uses--> `CertificateType`  [INFERRED]
  app.py → models.py
- `Public demo landing page — no login required.` --uses--> `CertificateType`  [INFERRED]
  app.py → models.py
- `Archive logs into `config.LOG_ARCHIVE_DIR` and return a download URL.      Accep` --uses--> `CertificateType`  [INFERRED]
  app.py → models.py
- `Serve a signed short-lived download token without requiring auth.      Token ver` --uses--> `CertificateType`  [INFERRED]
  app.py → models.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (33): apply_templates_endpoint(), archive_logs(), clear_logs(), demo_landing(), demo_preview(), design_page(), download_signed(), get_logs() (+25 more)

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (41): GenerateRequest, IssueRequest, List issued certificates with optional filters for status, type, resident, and s, Stream all matching certificates as CSV. Accepts same filters as GET /., Render the certificate with optional overrides but do not persist anything., Optional overrides to apply to the template context before generating final outp, Return a paginated list of recent certificate issues for the UI dropdown.      O, Serve the generated certificate HTML/PDF stored under secure storage.      This (+33 more)

### Community 2 - "Community 2"
Cohesion: 0.31
Nodes (17): _buildDemoCertHtml(), ensureSeed(), handleAttachments(), handleAudit(), handleCertificates(), handleCertTypes(), handleDashboardStats(), handleHouseholds() (+9 more)

### Community 3 - "Community 3"
Cohesion: 0.21
Nodes (15): create_certificate(), create_signed_download(), export_certificates(), generate_certificate_file(), get_certificate_file(), _household_dict(), list_certificates(), list_recent_certificates() (+7 more)

### Community 4 - "Community 4"
Cohesion: 0.16
Nodes (10): _broadcast_discover(), _get_local_ip(), _heartbeat_sender(), _heartbeat_watcher(), discovery.py — UDP-based peer discovery and auto-election for PITOGO app.  How i, Start peer discovery. Calls one of:       on_elected_leader()            — this, Broadcast DISCOVER for DISCOVERY_TIMEOUT_SEC. Return (host, port) if leader foun, Leader broadcasts its address as a heartbeat. (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.19
Nodes (9): get_db(), FastAPI dependency that yields a SQLAlchemy session., get_session(), init_db(), Database helper for PITOGO app (SQLite + SQLAlchemy).  Provides `engine`, `Sessi, Create database tables for the provided SQLAlchemy `Base` metadata., create_admin_user(), main() (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.27
Nodes (11): change_password(), ChangePasswordIn, create_user(), CreateUserIn, delete_user(), list_users(), _load_users(), List users with optional search and pagination. Admin only. (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.31
Nodes (9): create_session(), _expire_seconds(), get_session(), _hash(), _load_users(), auth.py — simple username/password session auth for the PITOGO Barangay App.  No, require_auth(), SessionData (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (3): _build_logger(), _JsonFormatter, app_logger.py — structured rotating JSON logger for PITOGO Barangay App. Reused

### Community 9 - "Community 9"
Cohesion: 0.33
Nodes (7): authHeader(), authHeaders(), ensureConfirm(), ensureToast(), getToken(), showConfirm(), showToast()

### Community 10 - "Community 10"
Cohesion: 0.39
Nodes (6): create_resident(), get_resident(), list_residents(), ResidentIn, _to_dict(), update_resident()

### Community 11 - "Community 11"
Cohesion: 0.36
Nodes (7): demo_start(), FeedbackIn, list_feedbacks(), _load(), Return a demo marker token — actual data is handled client-side., _save(), submit_feedback()

### Community 12 - "Community 12"
Cohesion: 0.38
Nodes (6): _b64u_decode(), _b64u_encode(), create_signed_token(), Create a signed token for a path relative to `config.SECURE_DIR`.      Returns (, Verify token and return the payload dict. Raises ValueError on failure., verify_signed_token()

### Community 13 - "Community 13"
Cohesion: 0.43
Nodes (6): Simple PDF/HTML storage utilities for PITOGO.  Attempts to render HTML to PDF us, Store HTML and try to produce a PDF.      Returns the filesystem path (string) o, render_and_store(), _weasyprint_pdf(), _wkhtmltopdf(), _write_html()

### Community 14 - "Community 14"
Cohesion: 0.48
Nodes (5): create_household(), get_household(), list_households(), _to_dict(), update_household()

### Community 15 - "Community 15"
Cohesion: 0.47
Nodes (5): inject_into_file(), main(), Simulate placeholder injection for a single file.      Returns a dict: { 'patche, replace_in_text_node(), simulate_inject_into_file()

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (2): _ensure_storage_dir(), upload_attachment()

### Community 17 - "Community 17"
Cohesion: 0.47
Nodes (4): CertificateTypeIn, create_type(), list_types(), _to_dict()

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (4): load_public_key(), patch_signing.py — simple RSA SHA256 signature verification helper.  Expect a PE, Return True if signature verifies using the configured public key., verify_signature()

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (3): main(), start.py — launcher for PITOGO Barangay App. Checks venv/deps, then starts the a, _server_alive()

### Community 20 - "Community 20"
Cohesion: 0.83
Nodes (3): convert_file(), main(), slug_name()

### Community 21 - "Community 21"
Cohesion: 0.5
Nodes (1): Add certificate lifecycle fields (finalized_at, voided_at, voided_by, void_reaso

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): config.py — PITOGO Barangay App configuration.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): API package for PITOGO app.

## Knowledge Gaps
- **25 isolated node(s):** `start.py — launcher for PITOGO Barangay App. Checks venv/deps, then starts the a`, `Create a signed token for a path relative to `config.SECURE_DIR`.      Returns (`, `Verify token and return the payload dict. Raises ValueError on failure.`, `Pydantic schemas for top certificate types (draft).  These are minimal schemas t`, `Simple PDF/HTML storage utilities for PITOGO.  Attempts to render HTML to PDF us` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (6 nodes): `delete_attachment()`, `download_attachment()`, `_ensure_storage_dir()`, `list_attachments()`, `attachments.py`, `upload_attachment()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (4 nodes): `b7c3e1f82d40_cert_lifecycle_fields.py`, `downgrade()`, `Add certificate lifecycle fields (finalized_at, voided_at, voided_by, void_reaso`, `upgrade()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `config.py`, `config.py — PITOGO Barangay App configuration.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `__init__.py`, `API package for PITOGO app.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CertificateType` connect `Community 1` to `Community 0`, `Community 17`, `Community 5`?**
  _High betweenness centrality (0.183) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 5` to `Community 1`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `Resident` connect `Community 1` to `Community 10`, `Community 5`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 42 inferred relationships involving `CertificateType` (e.g. with `ArchiveRequest` and `ImportTemplatesRequest`) actually correct?**
  _`CertificateType` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Resident` (e.g. with `ResidentIn` and `HouseholdIn`) actually correct?**
  _`Resident` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Household` (e.g. with `HouseholdIn` and `IssueRequest`) actually correct?**
  _`Household` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `CertificateIssue` (e.g. with `IssueRequest` and `VoidRequest`) actually correct?**
  _`CertificateIssue` has 13 INFERRED edges - model-reasoned connections that need verification._