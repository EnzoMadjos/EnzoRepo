# Release v0.1.0 — 2026-04-28

Commit: b5e2996 (HEAD of main)

Summary
- Templates import/inject workflow:
  - DOCX → HTML importer (dry-run supported)
  - Heuristic placeholder injector with dry-run simulation
  - Admin endpoints: `/admin/templates/import` (dry-run), `/admin/templates/apply`, `/admin/templates/undo`
  - UI: Audit page import preview, per-file Apply, Apply All, Undo, Undo All
  - Backups: `*.html.bak` created before modifications (undo restores and removes `.bak`)

- Audit & logs:
  - `/admin/logs/archive` accepts JSON body filters (`q`, `level`, `start`, `end`, `format`, `clear_after`)
  - Archive download endpoint `/admin/archives/{filename}`

- Tests:
  - Added unit tests for import dry-run, inject-simulation, apply, undo, and archive flows.
  - Ran full test suite locally; all tests passed.

Notes
- Dry-run is safe and recommended before applying changes. Use the UI at `/ui/audit` or call the API.
- To apply injector to all files: POST `/admin/templates/apply` with `{ "apply_all": true }` (this will create `.bak` files).
- To revert changes: POST `/admin/templates/undo` with `{ "undo_all": true }` to restore and remove `.bak` backups.

Upgrade / Deploy
1. Pull `origin/main` to get these changes.
2. Run tests locally: `.venv/bin/python projects/pitogo-app/tests/run_tests.py` and the other tests under `projects/pitogo-app/tests/`.

Changelog
- See commits since previous release for detailed changes. This release focuses on template import and admin tooling.
