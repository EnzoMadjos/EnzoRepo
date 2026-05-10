---
name: gemini-cli
description: 'Superpower: Use Gemini CLI (gemini-cli) as a second AI agent in the terminal. Use when: boss asks to run a task through Gemini, compare Gemini vs Copilot answers, use Gemini for file/shell/web tasks, leverage 1M context window for large codebase analysis, or when Jarvis wants a second opinion from Google Gemini. Triggers: "ask gemini", "run this through gemini", "gemini, do this", "gemini check", "gemini analyze", "gemini compare". Install: npm install -g @google/gemini-cli. Auth: gemini auth (Google account, free tier 60 req/min 1000 req/day).'
argument-hint: 'Task or question to run through Gemini CLI'
user-invocable: true
---

# Gemini CLI — Jarvis Superpower

**gemini-cli** is Google's open-source AI agent (v0.41.2 installed globally).  
Brings Gemini 2.5 Pro (1M token context) directly into the terminal.  
Free tier: 60 req/min, 1,000 req/day — no API key needed with Google account.

---

## When to Use

- Boss says "ask gemini", "gemini, do this", "run through gemini"
- Large codebase analysis (1M context window — paste entire files)
- Cross-checking Jarvis output against Gemini's reasoning
- Google Search grounding needed (real-time web search baked in)
- File/shell/web tasks that benefit from a second agent perspective
- Benchmarking: "what would Gemini do here?"

---

## Quick Reference

```bash
# Interactive REPL (default)
gemini

# One-shot prompt
gemini -p "your prompt here"

# Pipe file content into Gemini
cat somefile.py | gemini -p "review this for bugs"

# Point at a folder (uses 1M context)
gemini -p "summarize this codebase" --all_files

# Non-interactive / scripted output
gemini --no-interactive -p "explain this error: ..."

# Check version
gemini --version
```

## Auth

First-time setup (one-time):
```bash
gemini auth
# Opens browser → sign in with Google account → done
```

Free tier: 60 req/min, 1,000 req/day (personal Google account).  
For higher limits: set `GEMINI_API_KEY` env var with paid API key.

---

## Built-in Tools Gemini CLI Has

| Tool | What it does |
|------|-------------|
| File System | Read, write, search files |
| Shell | Execute terminal commands |
| Web Fetch | Fetch URLs, scrape pages |
| Google Search | Grounded web search (real-time) |
| MCP Servers | Custom tool extensions |

---

## Integration with Jarvis Workflow

### "Second Opinion" Pattern
```bash
# Jarvis implements → pipe to Gemini for review
cat Game\ Dev/Pokemon\ World/app.py | gemini -p "review for bugs and OWASP issues"
```

### "Large Context" Pattern
```bash
# Analyze entire project folder
cd local-chatbot && gemini -p "find all security vulnerabilities in this codebase" --all_files
```

### "Research" Pattern
```bash
# Use Gemini's Google Search grounding for up-to-date info
gemini -p "what is the latest FastAPI best practice for OAuth2 in 2026?"
```

### "Compare" Pattern
```bash
# Get Gemini's take on an architecture decision
gemini -p "compare FastAPI vs Flask for a local LLM chatbot with SSE streaming"
```

---

## GEMINI.md Context Files

Create a `GEMINI.md` in any project folder to give Gemini persistent context (like `.github/copilot-instructions.md`):

```bash
# Example: Game Dev/Pokemon World/GEMINI.md
echo "This is a Phaser 3 + FastAPI Pokemon game. Port 8300. Gen 3 battle engine." > "Game Dev/Pokemon World/GEMINI.md"
```

Gemini reads this automatically when run from that directory.

---

## Slash Commands (inside gemini REPL)

| Command | Action |
|---------|--------|
| `/help` | List all commands |
| `/chat save <name>` | Save conversation checkpoint |
| `/chat resume <name>` | Resume saved conversation |
| `/tools` | List available tools |
| `/mcp` | List connected MCP servers |
| `/clear` | Clear context |
| `/quit` | Exit |

---

## MCP Integration

Gemini CLI supports MCP servers — same protocol as Jarvis's MCP stack.  
Config: `~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp/memory"]
    }
  }
}
```

---

## Repo

- GitHub: https://github.com/google-gemini/gemini-cli
- NPM: `@google/gemini-cli`
- Docs: https://www.geminicli.com/docs
- License: Apache 2.0
