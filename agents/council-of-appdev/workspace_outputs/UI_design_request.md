# Urgent: UI Design Request — BrgyOS / PITOGO

From: Project Owner
Date: 2026-04-27

## Goal
Produce high-fidelity UI mockups (web) for review covering the core user flows for Barangay Pitogo:
- Login / role-aware dashboard (superadmin, admin, encoder, officer, viewer)
- Certificate issuance flows (top priority: `clearance`, `residency`, `indigency`, `business_clearance`, `cohabitation`, `sss_membership`)
- Logs / support modal / update banner
- Server status and leader/client view

## Deliverables (initial)
1. HTML/CSS mockups (Jinja2-ready) for the six priority certs, placed under `projects/pitogo-app/templates/certs/` as draft templates.
2. PNG screenshots (desktop 1366x768) of each screen placed in `agents/council-of-appdev/workspace_outputs/ui_screenshots/`.
3. A short mapping table (CSV/Markdown) mapping each source `.docx` in `projects/pitogo-app/templates/docs/source_documents/` to a target `cert_type` and list of fields.
4. Suggested field ordering and small copy edits (Tagalog-friendly) for each certificate.

## Constraints
- Must match the architect plan in `BRGY_PITOGO_ARCHITECT_PLAN.md` (data model, roles, cert types).
- Use the existing prototype at `projects/pitogo-app/templates/index.html` as the shell; mockups should drop into that layout.

## Timeline
- Initial HTML mockups + mapping table in 2 business days.
- PNG screenshots in 3 business days.

## Notes for designers
- Templates should be Jinja2-ready (use `{{ full_name }}`, `{{ address }}`, `{{ purpose }}`, `{{ issued_by }}`, `{{ issued_at }}` placeholders).
- Mark which templates require officer signature images. Add a default placeholder image path: `/static/signatures/default.png`.

---

Council of AppDev: please take this on and update `agents/council-of-appdev/workspace_outputs/document_mapping_review.md` when mapping is complete. Contact the Architect agent (architect role) for any clarifications.
