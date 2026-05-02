# Atlas

tags: [project, atlas, ollama, local-ai]

## Overview

Personal offline AI assistant — local-first (Ollama), cloud fallback via GitHub Models API. Lives in `local-chatbot/`.

## Status: ACTIVE

## Tech

- FastAPI + Python 3.10+
- Browser UI (HTML/CSS/JS in `static/` and `templates/`)
- Persona: Bisaya/Tagalog flavored, calls user "Pre"
- TTS: Kokoro v1.0 int8 ONNX model
- Multi-platform: Linux native + WSL2, Windows via `windows-launchers/`

## Key modules

| Module | Purpose |
|---|---|
| `vault.py` | Encrypted secrets — never stored plaintext |
| `audit.py` | Audit trail for user actions |
| `auto_learn.py` | Passive knowledge accumulation |
| `rag_memory.py` | RAG over stored notes/docs |
| `conversation_memory.py` | Session + long-term conversation memory |
| `trust_profile.py` | Per-user trust levels |
| `trait_memory.py` | Behavioral trait persistence |
| `atlas_app.py` | Main app entrypoint |
| `atlas_monitor.py` | Health monitor |

## Run

```bash
cd local-chatbot && python atlas_app.py
```

## Related

- [[Projects Index]]
- [[Workspace Patterns]]
