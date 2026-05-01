# Graph Report - sf-qa-agent  (2026-05-01)

## Corpus Check
- 21 files · ~31,399 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 276 nodes · 386 edges · 20 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 30 edges (avg confidence: 0.5)
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
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 21|Community 21]]

## God Nodes (most connected - your core abstractions)
1. `SalesforceClient` - 36 edges
2. `SalesforceClient` - 11 edges
3. `plan()` - 10 edges
4. `info()` - 9 edges
5. `_plan_for_direct_id_flow()` - 7 edges
6. `_load_all()` - 5 edges
7. `save_profile()` - 5 edges
8. `_load_all()` - 5 edges
9. `save_profile()` - 5 edges
10. `_fernet()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `Executor: runs an operation plan produced by llm_planner against Salesforce.  Re` --uses--> `SalesforceClient`  [INFERRED]
  sf_executor.py → SalesforceQA-Install/app/sf_client.py
- `Replace $stepN.id tokens in string values with the actual record ID.` --uses--> `SalesforceClient`  [INFERRED]
  sf_executor.py → SalesforceQA-Install/app/sf_client.py
- `Iterate through plan operations and yield progress event dicts:      {"type": "s` --uses--> `SalesforceClient`  [INFERRED]
  sf_executor.py → SalesforceQA-Install/app/sf_client.py
- `sf_app.py — main FastAPI application for the Salesforce QA Test Automation Agent` --uses--> `SalesforceClient`  [INFERRED]
  sf_app.py → SalesforceQA-Install/app/sf_client.py
- `Spawn a replacement uvicorn process, then terminate the current one.` --uses--> `SalesforceClient`  [INFERRED]
  sf_app.py → SalesforceQA-Install/app/sf_client.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (42): instance_url(), org_id(), Create a record and return {"id": "...", "url": "..."}., SalesforceClient, BaseModel, LogReport, admin_clear_logs(), admin_get_prompt() (+34 more)

### Community 1 - "Community 1"
Cohesion: 0.11
Nodes (28): _build_object_lookup(), _build_schema_context(), _call_ollama(), _canonicalize_ui_field_name(), _detect_mentioned_objects(), _extract_bullet_fields(), _extract_field_name(), _extract_json() (+20 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (10): instance_url(), org_id(), Create a record and return {"id": "...", "url": "..."}., Update an existing record. Returns {"id": "...", "url": "..."}., Permanently delete a record., Clone a record — fetches fields, strips read-only ones, creates a copy with opti, Lightweight list of all sObjects in the org: [{name, label, queryable}]., Retry transient Salesforce read timeouts before failing the step. (+2 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (14): admin_clear_logs(), admin_get_prompt(), admin_logs(), admin_set_prompt(), info(), login(), login_with_profile(), sf_app.py — main FastAPI application for the Salesforce QA Test Automation Agent (+6 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (16): _decrypt(), delete_profile(), _encrypt(), _fernet(), _get_key(), list_profiles(), _load_all(), load_profile() (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.2
Nodes (16): _decrypt(), delete_profile(), _encrypt(), _fernet(), _get_key(), list_profiles(), _load_all(), load_profile() (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.18
Nodes (7): _build_logger(), clear_logs(), get_recent(), _JsonFormatter, app_logger.py — structured logging for the SF QA Agent.  Writes JSON-lines to se, Truncate all log files., Return the N most-recent log entries as parsed dicts (newest first).

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (7): _build_logger(), clear_logs(), get_recent(), _JsonFormatter, app_logger.py — structured logging for the SF QA Agent.  Writes JSON-lines to se, Truncate all log files., Return the N most-recent log entries as parsed dicts (newest first).

### Community 8 - "Community 8"
Cohesion: 0.18
Nodes (7): ping(), relay_server.py — Enzo's on-demand support relay server.  Run this on your machi, Called by Vanessa's app after successfully applying the patch.     Renames patch, Receive a log report from Vanessa's app, save it, and print to console., Public endpoint — no token required.     Vanessa's app calls this to check if yo, receive_logs(), update_consumed()

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (7): _ollama_alive(), SalesforceQA Launcher --------------------- Compiled to SalesforceQA.exe via PyI, Fallback if tkinter is unavailable., _run_headless(), _server_alive(), _start_ollama(), _start_server()

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (7): _ollama_alive(), SalesforceQA Launcher --------------------- Compiled to SalesforceQA.exe via PyI, Fallback if tkinter is unavailable., _run_headless(), _server_alive(), _start_ollama(), _start_server()

### Community 11 - "Community 11"
Cohesion: 0.32
Nodes (7): parse_bytes(), _parse_docx(), _parse_pdf(), parse_text(), file_parser.py — extract plain text from uploaded files or raw paste.  Supported, Parse uploaded file bytes into plain text based on file extension., Sanitise and return raw pasted text.

### Community 12 - "Community 12"
Cohesion: 0.36
Nodes (6): create_session(), _expire_seconds(), get_session(), auth.py — Salesforce-credential-based session auth.  Flow:   1. POST /auth/login, require_auth(), SessionData

### Community 13 - "Community 13"
Cohesion: 0.32
Nodes (7): parse_bytes(), _parse_docx(), _parse_pdf(), parse_text(), file_parser.py — extract plain text from uploaded files or raw paste.  Supported, Parse uploaded file bytes into plain text based on file extension., Sanitise and return raw pasted text.

### Community 14 - "Community 14"
Cohesion: 0.36
Nodes (6): create_session(), _expire_seconds(), get_session(), auth.py — Salesforce-credential-based session auth.  Flow:   1. POST /auth/login, require_auth(), SessionData

### Community 15 - "Community 15"
Cohesion: 0.38
Nodes (6): _call_ollama(), _extract_json(), plan(), LLM Planner: converts a plain-English test script into a structured JSON operati, Convert a plain-English test script to a list of operation dicts.     Retries on, Strip markdown fences if present and parse JSON.

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (5): execute(), Executor: runs an operation plan produced by llm_planner against Salesforce.  Re, Replace $stepN.id tokens in string values with the actual record ID., Iterate through plan operations and yield progress event dicts:      {"type": "s, _resolve_refs()

### Community 17 - "Community 17"
Cohesion: 0.4
Nodes (5): execute(), Executor: runs an operation plan produced by llm_planner against Salesforce.  Re, Replace $stepN.id tokens in string values with the actual record ID., Iterate through plan operations and yield progress event dicts:      {"type": "s, _resolve_refs()

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Build a client from an auth.SessionData object.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Build a client from an auth.SessionData object.

## Knowledge Gaps
- **57 isolated node(s):** `org_profiles.py — save and load Salesforce org login profiles locally.  Profiles`, `Load or create the Fernet key for this machine.`, `Return a list of saved profiles with non-sensitive fields only.`, `Save a profile, encrypting sensitive fields.`, `Load a profile and decrypt sensitive fields.` (+52 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 19`** (1 nodes): `Build a client from an auth.SessionData object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Build a client from an auth.SessionData object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SalesforceClient` connect `Community 0` to `Community 16`, `Community 17`, `Community 3`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `LogReport` connect `Community 0` to `Community 8`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `sf_app.py — main FastAPI application for the Salesforce QA Test Automation Agent` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `SalesforceClient` (e.g. with `RelayConnectRequest` and `LogReportRequest`) actually correct?**
  _`SalesforceClient` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `org_profiles.py — save and load Salesforce org login profiles locally.  Profiles`, `Load or create the Fernet key for this machine.`, `Return a list of saved profiles with non-sensitive fields only.` to the rest of the system?**
  _57 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._