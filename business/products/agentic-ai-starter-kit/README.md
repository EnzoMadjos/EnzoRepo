# Agentic AI Starter Kit

> A production-ready multi-agent Python framework — research, write, and code with AI agents that plan, collaborate, and execute tasks automatically.

---

## What's Inside

```
agentic-ai-starter-kit/
├── agent_core/           # Core framework: orchestrator, LLM abstraction, memory
│   ├── orchestrator.py   # Plans goals → delegates tasks to agents
│   ├── llm.py            # Unified LLM caller (OpenAI / Anthropic / Ollama)
│   └── memory.py         # Stores agent results with JSON persistence
├── agents/               # Specialized agents
│   ├── researcher.py     # Searches the web + synthesizes findings
│   ├── writer.py         # Writes reports, blogs, emails, summaries
│   └── coder.py          # Writes Python, JS, Apex code with explanations
├── tools/                # Plug-and-play tools agents can call
│   ├── search.py         # DuckDuckGo web search (no API key needed)
│   ├── file_ops.py       # Safe file read/write/list
│   └── calculator.py     # AST-safe math evaluator (no eval() risk)
├── examples/             # 3 working end-to-end pipelines
│   ├── 01_research_assistant.py
│   ├── 02_blog_post_generator.py
│   └── 03_multi_agent_pipeline.py
├── prompts/              # Reusable system prompt templates
├── output/               # Where examples save their results
├── config.py             # Your API keys and provider settings
└── requirements.txt
```

---

## Quick Start (5 minutes)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your LLM provider

Open `config.py` and set your provider:

**Option A — Ollama (free, runs locally):**
```python
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL = "llama3.2"   # or "phi4-mini", "mistral"
```
Install Ollama at https://ollama.com, then: `ollama pull llama3.2`

**Option B — OpenAI:**
```python
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = "sk-..."
```

**Option C — Anthropic:**
```python
DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-3-haiku-20240307"
ANTHROPIC_API_KEY = "sk-ant-..."
```

### 3. Run an example

```bash
# Research any topic and get a report
python examples/01_research_assistant.py "What is agentic AI?"

# Generate a full blog post
python examples/02_blog_post_generator.py "How to automate tasks with Python agents"

# Full orchestrated multi-agent run
python examples/03_multi_agent_pipeline.py "Build a Python script that sends daily email digests"
```

Results are saved to the `output/` folder.

---

## Core Concepts

### Orchestrator

The `Orchestrator` is the brain. You give it a goal, it:
1. Calls the LLM to break the goal into a list of tasks
2. Routes each task to the right agent (`researcher`, `writer`, or `coder`)
3. Passes context from one step to the next
4. Stores results in `Memory`

```python
from agent_core.orchestrator import Orchestrator
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent

orchestrator = Orchestrator(provider="ollama", model="llama3.2")
agents = {
    "researcher": ResearcherAgent(provider="ollama", model="llama3.2"),
    "writer": WriterAgent(provider="ollama", model="llama3.2"),
}
results = orchestrator.run(goal="Write a report about AI trends", agents=agents)
```

### Agents

Each agent has a `run(task, context)` method:

```python
from agents.researcher import ResearcherAgent

agent = ResearcherAgent(provider="openai", model="gpt-4o-mini")
result = agent.run(task="What are the top AI frameworks in 2026?")
print(result)
```

### LLM Abstraction

Call any LLM with one function:

```python
from agent_core.llm import call_llm

result = call_llm(
    provider="anthropic",
    model="claude-3-haiku-20240307",
    system="You are an expert Python developer.",
    user="Write a function to parse JSON safely."
)
```

### Memory

Agents automatically save results. You can read them back:

```python
from agent_core.memory import Memory

mem = Memory()
mem.add(agent="researcher", task="AI trends", result="...")
context = mem.get_context(agent="researcher", last_n=3)
```

Results persist to `memory.json` between runs.

---

## Adding Your Own Agent

Create `agents/my_agent.py`:

```python
from agent_core.llm import call_llm

class MyAgent:
    def __init__(self, provider="ollama", model="llama3.2"):
        self.provider = provider
        self.model = model
        self.name = "my_agent"

    def run(self, task: str, context: str = "") -> str:
        system = "You are a specialist in [your domain]. Be precise and practical."
        user = f"Context:\n{context}\n\nTask:\n{task}" if context else task
        return call_llm(self.provider, self.model, system=system, user=user)
```

Add it to `agents/__init__.py` and pass it in the agents dict — that's it.

---

## Adding Your Own Tool

Create `tools/my_tool.py`:

```python
def my_tool(input: str) -> str:
    # Your logic here
    return f"Result for: {input}"
```

Import it in your agent's `run()` method — agents call tools like regular Python functions.

---

## Security Notes

- API keys are set in `config.py` — **never commit this file to a public repo**
- `file_ops.py` uses path traversal protection — agents can only read/write within the current directory
- `calculator.py` uses AST evaluation — no `eval()` is called anywhere
- No credentials are stored in memory or logged to disk

---

## Requirements

- Python 3.10+
- One of: Ollama (free), OpenAI API key, Anthropic API key

---

## License

MIT License. Build freely, sell freely, modify freely. Attribution appreciated.

---

## Made by MadjosBuilds

Questions? Suggestions? Found this useful?  
Drop a review on Gumroad — it helps more builders find this kit.
