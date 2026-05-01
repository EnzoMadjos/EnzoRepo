# Graph Report - local-chatbot  (2026-05-01)

## Corpus Check
- 28 files · ~32,973 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 561 nodes · 1016 edges · 18 communities detected
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 152 edges (avg confidence: 0.8)
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

## God Nodes (most connected - your core abstractions)
1. `w` - 26 edges
2. `append_audit()` - 25 edges
3. `se` - 22 edges
4. `build_persona_summary()` - 21 edges
5. `ask_ai_stream()` - 17 edges
6. `list_training()` - 16 edges
7. `save_persona_summary()` - 14 edges
8. `execute_tool()` - 13 edges
9. `b()` - 13 edges
10. `upsert_memory()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `web_fetch()` --calls--> `fetch_url_content()`  [INFERRED]
  app.py → web_fetcher.py
- `web_summary()` --calls--> `fetch_url_content()`  [INFERRED]
  app.py → web_fetcher.py
- `web_fetch()` --calls--> `extract_text_from_html()`  [INFERRED]
  app.py → web_fetcher.py
- `web_summary()` --calls--> `extract_text_from_html()`  [INFERRED]
  app.py → web_fetcher.py
- `build_persona_summary()` --calls--> `get_context_block()`  [INFERRED]
  app.py → session_memory.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (85): BaseModel, _active_cloud_provider(), AgentBuildRequest, AgentSaveRequest, brain_set_provider(), brain_status(), build_agent_route(), _cloud_client() (+77 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (15): list_all_sessions(), Return all active session IDs., b(), c(), ce(), d(), g(), ie (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (25): $(), a(), b(), c(), d(), e(), g(), i() (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (52): add_training_entry(), add_trait_entry(), admin_web_allowlist(), admin_web_toggle(), build_persona_summary(), clear_all_training(), clear_all_traits(), clear_training_post() (+44 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (54): export_training(), import_training(), memory_add(), memory_delete(), memory_list(), memory_sessions_clear(), memory_sessions_context(), memory_sessions_list() (+46 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (46): ask_ai(), ask_ai_stream(), _auto_summarize_session(), build_atlas_system_prompt(), memory_search(), memory_sync(), Sync all training entries into the RAG vector store., Summarize a session's history and store as a training entry before clearing. (+38 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (28): HTMLParser, _inject_web_context(), If the prompt contains URLs, fetch each one and prepend its content., web_status(), execute_tool(), ATLAS Tool Executor Native Ollama tool calling — uses the model's built-in funct, Execute a tool by name with args dict. Returns observation string., Rewrite known noisy commands to their rtk-compressed equivalents.     Only rewri (+20 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (27): find_files(), list_dir(), file_access.py — Secure sandboxed file system access for ATLAS.  ATLAS can read,, List files and subdirectories at rel_path within the workspace., Read a file's contents. Returns chunks if > MAX_READ_BYTES., Write content to a file. Only allowed if ATLAS_FS_WRITE=1., Search files under rel_path for text matching query.     Returns list of {path,, Find files by name pattern (glob) within rel_path. (+19 more)

### Community 8 - "Community 8"
Cohesion: 0.35
Nodes (11): vault_get(), vault_list(), delete_secret(), get_fernet(), get_secret(), get_secure_atlas_folder(), get_vault_file(), list_secrets() (+3 more)

### Community 9 - "Community 9"
Cohesion: 0.3
Nodes (11): auth_autokey(), auth_login(), auth_set(), auth_status(), Return the API key without passphrase — single-user local convenience., get_api_key(), _get_pass_file(), _get_secure_folder() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (10): build_atlas_system_prompt_slim(), nickname_status(), Minimal system prompt for GitHub Models / tight token scenarios., set_nickname(), get_nickname_file(), get_preferred_nickname(), get_secure_atlas_folder(), load_nickname_profile() (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.42
Nodes (10): append_log(), current_file_hashes(), ensure_monitor_files(), get_secure_atlas_folder(), get_windows_acl(), load_baseline(), main(), report_changes() (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (1): AtlasFace

### Community 13 - "Community 13"
Cohesion: 0.36
Nodes (6): main(), ATLAS Desktop App — Windows Native Starts the ATLAS server inside WSL, then open, Small splash window while server starts., _show_loading_window(), _stop_wsl_server(), _wait_for_server()

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (1): oe

### Community 15 - "Community 15"
Cohesion: 0.38
Nodes (4): main(), ATLAS Desktop App Starts the FastAPI server in the background and opens the chat, _stop_server(), _wait_for_server()

### Community 16 - "Community 16"
Cohesion: 0.7
Nodes (4): closeAtlasModal(), _initAtlasDialog(), openAtlasModal(), _populateDialog()

### Community 17 - "Community 17"
Cohesion: 0.83
Nodes (3): get_secure_atlas_folder(), load_api_key(), verify_api_key()

## Knowledge Gaps
- **87 isolated node(s):** `Session-scoped conversation history for ATLAS. Keeps a rolling window of message`, `Persist active sessions to disk.`, `Load persisted sessions on startup.`, `Create a new session and return its ID.`, `Return the message list for a session, creating one if needed.` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (9 nodes): `AtlasFace`, `._col()`, `.constructor()`, `.destroy()`, `._drawDots()`, `._drawWaveform()`, `._frame()`, `.setState()`, `atlas-face.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (8 nodes): `oe`, `.constructor()`, `.#e()`, `.parser()`, `.setOptions()`, `.#t()`, `.use()`, `.walkTokens()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `memory_sessions_list()` connect `Community 4` to `Community 0`, `Community 1`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Why does `upsert_memory()` connect `Community 5` to `Community 4`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `append_audit()` (e.g. with `_tool_remember()` and `_inject_web_context()`) actually correct?**
  _`append_audit()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `build_persona_summary()` (e.g. with `load_trust_profile()` and `list_traits()`) actually correct?**
  _`build_persona_summary()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Session-scoped conversation history for ATLAS. Keeps a rolling window of message`, `Persist active sessions to disk.`, `Load persisted sessions on startup.` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.03 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.04 - nodes in this community are weakly interconnected._