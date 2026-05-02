# SF QA Agent

tags: [project, salesforce, qa, automation]

## Overview

Salesforce test automation: paste English test script → AI generates plan → creates records on org. Lives in `sf-qa-agent/`.

## Status: ACTIVE

## Tech

- FastAPI + Uvicorn
- Ollama (llama3.2:3b) for LLM planning
- Salesforce OAuth (Connected App)
- Supports `.txt/.docx/.pdf` file upload
- Live streaming results dashboard
- Admin panel: live AI system prompt patching without server restart

## Key features

- `$step1.id` syntax for linked record references
- `llm_planner.py` — AI-driven test step generation
- `sf_executor.py` — executes steps against Salesforce org
- `sf_client.py` — OAuth + REST API client
- `relay/` — shared relay/support server

## Config

- `config.py` — app settings
- `org_profiles.py` — multi-org support
- `secure/` — credentials (never plaintext)
- Connected app setup: `CONNECTED_APP_SETUP.md`

## Run

```bash
cd sf-qa-agent && bash start.sh
```

## Related

- [[Projects Index]]
- [[Salesforce Knowledge]]
- [[Workspace Patterns]]
