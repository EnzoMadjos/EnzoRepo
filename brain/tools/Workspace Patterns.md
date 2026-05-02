# Workspace Patterns

tags: [workspace, patterns, conventions]

## Tech Stack

- Language: Python 3.10+
- Web framework: FastAPI + Uvicorn
- UI: Jinja2 + vanilla HTML/CSS/JS
- Local LLM: Ollama
- Cloud LLM fallback: GitHub Models API
- Venv: `/home/enzo/ai-lab/.venv`

## Root paths

- Workspace: `/home/enzo/ai-lab`
- Venv activate: `source /home/enzo/ai-lab/.venv/bin/activate`
- Brain vault: `/home/enzo/ai-lab/brain/`
- MCP config: `/home/enzo/ai-lab/.vscode/mcp.json`

## Shell convention

- Always prefix shell commands with `rtk`: `rtk git status`, `rtk docker ps`
- RTK filters output and saves tokens

## Security patterns

- `vault.py` for encrypted secrets — no plaintext credentials ever
- Audit trails via `audit.py`
- Salesforce: OAuth only, no password storage
- Signed patch delivery for distributed updates
- OWASP Top 10 enforced on every delivery

## Dev philosophy

- Local-first; no cloud dep required
- Builder mindset: plan → build immediately
- DRY: always scan workspace before writing new code
- No over-engineering — only what's asked or clearly needed

## Active MCP servers

| Name | Type | Purpose |
|---|---|---|
| github | Docker | GitHub API |
| memory | Docker | Knowledge graph (node-based) |
| sequential-thinking | Docker | Chain-of-thought reasoning |
| context7 | SSE (port 8080) | Library docs lookup |
| playwright | Docker | Browser automation |
| fetch | Docker | Web fetch |
| git | Docker | Git operations |
| salesforce | uvx | Salesforce org API |
| brain | uvx | This vault — Zettelkasten MCP |

## Related

- [[Avengers Team]]
- [[Projects Index]]
