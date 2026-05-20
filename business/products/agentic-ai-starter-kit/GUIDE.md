# The Agentic AI Developer's Handbook
### Included with the Agentic AI Starter Kit by MadjosBuilds

---

## Introduction

Welcome to the Agentic AI Starter Kit.

If you bought this, you're ahead of 99% of developers who are still just using `chat.openai.com` and calling it AI integration.

**Agentic AI** is different. Instead of asking an AI one question at a time, you build systems where AI agents *plan*, *delegate*, *execute*, and *remember* — just like a team of specialists working toward a shared goal.

By the end of this guide, you'll have:
- A working multi-agent system you can extend for any project
- A clear mental model of how orchestration works
- The ability to add new agents, tools, and pipelines in minutes

No fluff. Let's build.

---

## Chapter 0: Choosing the Right LLM for Your Machine

> **Read this first.** The model you pick determines the quality of every output in this kit. Choosing wrong means slow responses or disappointing results.

### The Core Trade-off

Bigger models = smarter outputs, but need more RAM and CPU/GPU power.  
Smaller models = faster and lighter, but produce simpler, less nuanced output.

There is no single "best" model — the best model is the strongest one your machine can run *comfortably*.

---

### Ollama Model Picker (Local, Free)

| Your Machine | Recommended Model | `ollama pull` command | Quality |
|---|---|---|---|
| 8 GB RAM, no GPU | `phi4-mini` | `ollama pull phi4-mini` | ⭐⭐⭐ Good |
| 8 GB RAM, no GPU | `llama3.2:3b` | `ollama pull llama3.2:3b` | ⭐⭐ Decent |
| 16 GB RAM, no GPU | `llama3:latest` | `ollama pull llama3` | ⭐⭐⭐⭐ Recommended |
| 16 GB RAM, no GPU | `mistral` | `ollama pull mistral` | ⭐⭐⭐⭐ Great for writing |
| 16 GB RAM + GPU | `qwen2.5-coder:7b` | `ollama pull qwen2.5-coder:7b` | ⭐⭐⭐⭐ Best for code |
| 32 GB RAM + GPU | `llama3:70b` | `ollama pull llama3:70b` | ⭐⭐⭐⭐⭐ Near GPT-4 quality |

> ⚠️ **Higher model = higher specs required.** Running `llama3:70b` on 8 GB RAM will cause your machine to freeze or crash. Always match the model to your specs.

---

### Cloud Models (No GPU Needed — Pay Per Use)

If you have limited hardware or want the best possible output quality, use a cloud provider. You pay only for what you use — a typical pipeline run costs less than $0.01 with the mini models.

| Provider | Model | Cost | Best For |
|---|---|---|---|
| OpenAI | `gpt-4o-mini` | ~$0.001/run | Best value, all-round |
| OpenAI | `gpt-4o` | ~$0.01/run | Highest quality |
| Anthropic | `claude-3-haiku-20240307` | ~$0.001/run | Fast, cheap, reliable |
| Anthropic | `claude-3-5-sonnet-20241022` | ~$0.008/run | Best for long docs & code |

Set your provider in `config.py`:

```python
# Cloud option — no GPU needed, best quality
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = "sk-..."  # get from platform.openai.com
```

---

### Per-Agent Model Recommendation

Different agents benefit from different model strengths. If you want to fine-tune:

| Agent | Best Local Model | Best Cloud Model | Why |
|---|---|---|---|
| ResearcherAgent | `llama3:latest` | `gpt-4o-mini` | Needs good summarization |
| WriterAgent | `mistral` | `claude-3-haiku` | Mistral excels at natural writing |
| CoderAgent | `qwen2.5-coder:7b` | `gpt-4o` | Coding-specialized models win here |

You can mix providers per agent by passing `provider` and `model` directly:

```python
researcher = ResearcherAgent(provider="ollama", model="llama3:latest")
writer = WriterAgent(provider="ollama", model="mistral")
coder = CoderAgent(provider="openai", model="gpt-4o-mini")  # cloud for best code
```

---

### Quick Checklist Before Running

- [ ] Check your RAM: `free -h` (Linux/Mac) or Task Manager → Performance (Windows)
- [ ] Pull your chosen model: `ollama pull <model-name>`
- [ ] Update `config.py` with your model name
- [ ] If using cloud: add your API key to `config.py`
- [ ] Run: `python examples/01_research_assistant.py "test"` — if it responds, you're good

---

## Chapter 1: What Is Agentic AI?

### Traditional AI Usage (Chatbot Pattern)

```
User → Ask question → AI → Reply
```

That's fine for Q&A. But it can't:
- Break down complex goals
- Use external tools (search the web, read files, call APIs)
- Delegate sub-tasks to specialists
- Remember what happened in previous steps

### Agentic AI (Orchestrated Pattern)

```
Goal → Orchestrator → Plan → Agent A → Agent B → Agent C → Final Output
```

Each agent has a specialty. The orchestrator decides who does what, in what order, and passes context forward.

**Real example:**  
*Goal: "Research the top 5 Python AI frameworks and write a comparison blog post."*

1. **Orchestrator** plans: "Step 1: research. Step 2: write."
2. **ResearcherAgent** searches the web, synthesizes data
3. **WriterAgent** receives the research as context, writes the post
4. Output saved to file

This is what you built. This is what companies are building with frameworks like LangChain, AutoGen, and CrewAI — and now you understand the fundamentals from scratch.

---

## Chapter 2: The Architecture

### The Three Layers

**Layer 1 — The Core (`agent_core/`)**

| File | Purpose |
|---|---|
| `orchestrator.py` | Plans the goal, routes tasks, manages flow |
| `llm.py` | Unified call to any LLM (OpenAI / Anthropic / Ollama) |
| `memory.py` | Stores and retrieves agent results |

**Layer 2 — The Agents (`agents/`)**

| Agent | Specialty |
|---|---|
| `ResearcherAgent` | Web search + synthesis |
| `WriterAgent` | Reports, blogs, emails, summaries |
| `CoderAgent` | Python, JavaScript, Apex with explanations |

**Layer 3 — The Tools (`tools/`)**

| Tool | What it does |
|---|---|
| `web_search()` | DuckDuckGo search — no API key needed |
| `read_file()` / `write_file()` | Safe local file I/O |
| `calculate()` | AST-safe math evaluation |

Agents call tools. Orchestrators call agents. That's the whole model.

---

## Chapter 3: How the Orchestrator Works

The orchestrator is the most important piece. Here's what happens when you call `orchestrator.run(goal, agents)`:

### Step 1: Planning

```python
def plan(self, goal: str) -> list[dict]:
```

The orchestrator sends the goal to an LLM with a system prompt that says:
> "Break this goal into 2-5 tasks. For each task, specify: which agent should handle it and what the task is. Return JSON."

LLM returns something like:
```json
[
  {"agent": "researcher", "task": "Research the top Python AI frameworks in 2024"},
  {"agent": "writer", "task": "Write a comparison blog post based on the research"}
]
```

### Step 2: Execution

For each task in the plan:
1. Look up the agent in the agents dict
2. Get context from memory (recent results)
3. Call `agent.run(task, context)`
4. Store the result in memory

```python
for step in plan:
    agent = agents[step["agent"]]
    context = self.memory.get_context(step["agent"])
    result = agent.run(task=step["task"], context=context)
    self.memory.add(step["agent"], step["task"], result)
```

Simple. Effective. Extensible.

### Why Pass Context Forward?

Each agent works better when it knows what previous agents found. The `WriterAgent` writes a better blog post when it has the `ResearcherAgent`'s findings as context. The `CoderAgent` writes better code when it knows the architecture decisions made earlier.

This is called **chaining** — and it's what makes multi-agent systems powerful.

---

## Chapter 4: Working with Each Agent

### ResearcherAgent

```python
from agents.researcher import ResearcherAgent

agent = ResearcherAgent(provider="ollama", model="llama3.2")
result = agent.run(task="What are the best practices for Python REST APIs in 2026?")
print(result)
```

What it does internally:
1. Tries to do a live web search via DuckDuckGo
2. If search returns results, passes them to the LLM with: *"Synthesize this into key findings"*
3. If search fails (offline mode), LLM answers from training data only

**Best prompts for the Researcher:**
- "Research and summarize..."
- "Find key facts about..."
- "What are the latest trends in..."

---

### WriterAgent

```python
from agents.writer import WriterAgent

agent = WriterAgent(provider="openai", model="gpt-4o-mini")
result = agent.run(
    task="Write a 500-word blog post introduction about agentic AI",
    context="[paste researcher output here]"
)
```

**Best prompts for the Writer:**
- "Write a [format] about [topic]"
- "Summarize the following into a [length] [format]"
- "Draft a professional email that..."
- "Create a step-by-step guide for..."

Supported formats: blog post, report, email, summary, how-to guide, product description, LinkedIn post.

---

### CoderAgent

```python
from agents.coder import CoderAgent

agent = CoderAgent(provider="anthropic", model="claude-3-haiku-20240307")
result = agent.run(
    task="Write a Python function that reads a CSV file and returns rows as a list of dicts"
)
```

**Best prompts for the Coder:**
- "Write a Python function that..."
- "Create a JavaScript module for..."
- "Build a FastAPI endpoint that..."
- "Write a Salesforce Apex trigger that..."
- "Refactor this code to be more efficient: [paste code]"

The Coder always includes:
- The code block
- An explanation of how it works
- Usage example

---

## Chapter 5: The Tools Layer

### web_search()

```python
from tools.search import web_search

results = web_search("agentic AI python frameworks 2026", max_results=5)
print(results)
```

Returns a numbered list of results. No API key. Uses DuckDuckGo's HTML endpoint.

**Important:** Web search may fail if DDG changes its HTML structure or if you're rate-limited. The `ResearcherAgent` handles this gracefully by falling back to the LLM's training data.

---

### read_file() / write_file()

```python
from tools.file_ops import read_file, write_file, list_files

# Write output
write_file("output/my_report.txt", "# My Report\n\nContent here...")

# Read it back
content = read_file("output/my_report.txt")

# List all .txt files
files = list_files("output/", pattern="*.txt")
```

**Security note:** All paths are resolved relative to the current working directory. Path traversal (`../`) is blocked.

---

### calculate()

```python
from tools.calculator import calculate

result = calculate("(150 * 0.1) + 25")  # Returns: 40.0
result = calculate("2 ** 10")           # Returns: 1024
```

Uses Python's `ast` module instead of `eval()`. Safe to use with user input.

---

## Chapter 6: Building a Custom Pipeline

Let's build a pipeline that doesn't exist in the examples: a **Competitive Analysis Pipeline**.

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DEFAULT_PROVIDER, DEFAULT_MODEL
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from tools.file_ops import write_file

def competitive_analysis(product: str, competitors: list[str]):
    researcher = ResearcherAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)
    writer = WriterAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)

    # Research each competitor
    all_research = []
    for competitor in competitors:
        print(f"Researching {competitor}...")
        research = researcher.run(f"What are the features, pricing, and weaknesses of {competitor}?")
        all_research.append(f"=== {competitor} ===\n{research}")

    combined = "\n\n".join(all_research)

    # Write the analysis report
    print("Writing analysis...")
    report = writer.run(
        task=f"Write a competitive analysis report comparing {product} against these competitors. "
             f"Include a comparison table, strengths/weaknesses, and strategic recommendations.",
        context=combined,
    )

    write_file("output/competitive_analysis.md", report)
    print("Saved to output/competitive_analysis.md")
    return report

if __name__ == "__main__":
    competitive_analysis(
        product="My SaaS Product",
        competitors=["Notion", "Obsidian", "Roam Research"]
    )
```

That's the power of the kit. You're not learning syntax — you're assembling pipelines.

---

## Chapter 7: Adding a New Agent

Let's say you want a **DataAnalystAgent** that interprets CSV data.

**1. Create `agents/analyst.py`:**

```python
from agent_core.llm import call_llm

class DataAnalystAgent:
    def __init__(self, provider="ollama", model="llama3.2"):
        self.provider = provider
        self.model = model
        self.name = "analyst"

    def run(self, task: str, context: str = "") -> str:
        system = """You are an expert data analyst. When given data or a data question:
- Identify key trends and patterns
- Calculate relevant statistics
- Highlight anomalies or interesting findings
- Give actionable insights
Be specific and concise."""
        
        user = f"Data Context:\n{context}\n\nAnalysis Request:\n{task}" if context else task
        return call_llm(self.provider, self.model, system=system, user=user)
```

**2. Add to `agents/__init__.py`:**

```python
from .analyst import DataAnalystAgent
```

**3. Use it in a pipeline:**

```python
from agents.analyst import DataAnalystAgent
from tools.file_ops import read_file

analyst = DataAnalystAgent(provider="ollama", model="llama3.2")
data = read_file("data/sales_2025.csv")
result = analyst.run(
    task="What were the top 3 sales months and what drove the peaks?",
    context=data
)
print(result)
```

Done. Three steps to extend the kit.

---

## Chapter 8: Extending the Orchestrator

The default orchestrator works for linear pipelines. Here are two patterns for more advanced use:

### Pattern 1: Conditional Routing

```python
# In your pipeline
plan = orchestrator.plan(goal)

for step in plan:
    agent_name = step["agent"]
    
    # Custom routing: use coder for technical topics only
    if "code" in step["task"].lower() or "script" in step["task"].lower():
        agent_name = "coder"
    
    result = agents[agent_name].run(step["task"])
```

### Pattern 2: Parallel Execution

```python
import concurrent.futures

def run_parallel(tasks, agents):
    def execute(step):
        return agents[step["agent"]].run(step["task"])
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(execute, tasks))
    
    return results
```

Use parallel execution when tasks don't depend on each other (e.g., researching 5 competitors simultaneously).

---

## Chapter 9: Connecting to Real APIs

The kit is intentionally simple, but here's how to extend tools to call real APIs:

### Adding a Weather Tool

```python
# tools/weather.py
import requests

def get_weather(city: str) -> str:
    """Get current weather for a city using Open-Meteo (free, no API key)."""
    # First geocode the city
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    geo = requests.get(geo_url).json()
    
    if not geo.get("results"):
        return f"Could not find city: {city}"
    
    lat = geo["results"][0]["latitude"]
    lon = geo["results"][0]["longitude"]
    
    # Get weather
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,weathercode"
    )
    data = requests.get(weather_url).json()
    temp = data["current"]["temperature_2m"]
    return f"Current temperature in {city}: {temp}°C"
```

Then use it in an agent:

```python
from tools.weather import get_weather

class WeatherReporterAgent:
    def run(self, task: str, context: str = "") -> str:
        city = task  # Simplified: task is the city name
        weather = get_weather(city)
        return call_llm(
            provider=self.provider,
            model=self.model,
            system="You are a weather reporter. Write a friendly weather briefing.",
            user=f"Weather data: {weather}\nWrite a brief for: {task}"
        )
```

Same pattern works for any API: Stripe, Notion, Slack, GitHub, Salesforce, anything.

---

## Chapter 10: Production Checklist

Before deploying an agentic system to production:

**Security**
- [ ] API keys loaded from environment variables, not hardcoded
- [ ] File I/O restricted to safe directories (already done in `file_ops.py`)
- [ ] No `eval()` calls (already done in `calculator.py`)
- [ ] Rate limiting on LLM calls (add retry logic for production)

**Reliability**
- [ ] LLM calls wrapped in try/except
- [ ] Memory file backed up before long runs
- [ ] Timeouts on web search calls

**Cost Control**
- [ ] Use the smallest model that works (gpt-4o-mini, claude-haiku, llama3.2)
- [ ] Log token usage if using paid APIs
- [ ] Ollama for dev, cloud API for prod if needed

**Scalability**
- [ ] Add async/await for high-throughput pipelines
- [ ] Replace JSON memory with a real DB (SQLite, Postgres) for persistence
- [ ] Add a message queue (Redis, RabbitMQ) for long-running pipelines

---

## Appendix: Quick Reference

### LLM Provider Comparison

| Provider | Cost | Best Model | When to Use |
|---|---|---|---|
| Ollama (8 GB RAM) | Free | `phi4-mini` or `llama3.2:3b` | Low-end machine, privacy-sensitive |
| Ollama (16 GB RAM) | Free | `llama3:latest` or `mistral` | Recommended local sweet spot |
| Ollama (16 GB + GPU) | Free | `qwen2.5-coder:7b` | Best local code generation |
| Ollama (32 GB + GPU) | Free | `llama3:70b` | Near-cloud quality, offline |
| OpenAI | ~$0.001/run | `gpt-4o-mini` | Best value cloud option |
| OpenAI | ~$0.01/run | `gpt-4o` | Highest quality available |
| Anthropic | ~$0.001/run | `claude-3-haiku` | Fast cloud, great for writing |
| Anthropic | ~$0.008/run | `claude-3-5-sonnet` | Best cloud for long docs/code |

### Agent vs Tool: When to Use Which

| Scenario | Use |
|---|---|
| Need to think, reason, write | Agent |
| Need to fetch data, do math, read files | Tool |
| Need both | Agent that calls a Tool |

### Common Errors

| Error | Fix |
|---|---|
| `Connection refused :11434` | Start Ollama: `ollama serve` |
| `AuthenticationError` | Check API key in `config.py` |
| `Model not found` | Run `ollama pull <model-name>` |
| `JSONDecodeError` in orchestrator | LLM returned non-JSON — retry or use a stronger model |
| Search returns empty | DDG may be rate-limiting, wait 30s and retry |

---

## Final Word

You now have:
- A working multi-agent framework from scratch
- The mental model to extend it to any domain
- 3 production-ready example pipelines
- A guide to adding agents, tools, and API integrations

The biggest gap between developers and builders isn't knowledge — it's having something real to start from.

You have it now. Build something worth selling.

— MadjosBuilds
