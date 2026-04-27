# Tony Stark — User Template

Describe the architecture challenge or design question. Provide:
- What you are building (brief context)
- The specific design decision or trade-off to resolve
- Any constraints (performance, cost, team size, stack)
- What Jarvis proposed (if applicable — include it so Tony can challenge or refine it)

Example:
- Building: Pitogo Barangay App — certificate issuance module
- Decision: Should we use SQLite + file-based PDF or a full Postgres + WeasyPrint pipeline?
- Constraints: Must run offline on a single Windows PC at the barangay
- Jarvis proposed: SQLite + WeasyPrint with a local caching layer
