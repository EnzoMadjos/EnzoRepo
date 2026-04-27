# Steve Rogers — User Template

Describe the research task or the debate to adjudicate. Provide:
- The context (what app/feature is being designed)
- The two positions (Tony's vs Jarvis's, or your own vs a proposed solution)
- The specific question to resolve
- Any constraints that must be respected

Example (tiebreaker):
- Context: Pitogo Barangay App certificate module
- Tony's position: Use WeasyPrint + Postgres for full offline PDF pipeline
- Jarvis's position: Use SQLite + reportlab for simpler local-first deployment
- Question: Which is the better fit for a single-PC offline barangay deployment?

Example (research):
- Context: Pitogo app will need to sync data across 2-3 PCs on LAN
- Question: What is the most practical P2P sync strategy for a Python/FastAPI app with no internet dependency?
- Constraints: Must work on Windows 10/11, no Docker, no cloud.
