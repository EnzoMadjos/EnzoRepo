# Jarvis Brain — Vault

This is the **Jarvis team knowledge vault**. All notes are written and read by Jarvis (Copilot), Tony Stark, and Steve Rogers via the `brain` MCP server.

## Structure

| Folder | Purpose |
|---|---|
| `projects/` | One note per project — status, decisions, architecture |
| `salesforce/` | Salesforce patterns, Apex, LWC, Flow, security |
| `architecture/` | System design patterns, proposals, ADRs |
| `sessions/` | Session summaries — what was built, decided, or changed |
| `people/` | Team roles, agent system prompts, responsibilities |
| `tools/` | MCP servers, workspace tools, CLI patterns |

## How to use (in Obsidian)

- Open this folder as an **Obsidian vault** (`File > Open vault > Open folder as vault`)
- Enable **Graph View** (`Ctrl+G`) to see all notes and connections
- Links are `[[wikilink]]` format — Obsidian renders them as clickable edges in the graph

## Jarvis protocol

At session start, Jarvis queries this vault for project context. At session end, Jarvis writes a session summary note to `sessions/`. Tony and Steve read from here for design and deploy context.
