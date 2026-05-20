"""
Example 3: Full Multi-Agent Orchestrator Pipeline
---------------------------------------------------
Goal: Give a high-level goal → orchestrator breaks it into subtasks
      → assigns to researcher/writer/coder automatically → returns results.

Run: python examples/03_multi_agent_pipeline.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DEFAULT_PROVIDER, DEFAULT_MODEL
from agent_core.orchestrator import Orchestrator
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from agents.coder import CoderAgent
from tools.file_ops import write_file


def run(goal: str = "Build a Python script that fetches weather data and writes a daily summary report"):
    print("=" * 60)
    print("MULTI-AGENT ORCHESTRATOR PIPELINE")
    print("=" * 60)
    print(f"\nGoal: {goal}\n")

    # Initialize all agents
    agents = {
        "researcher": ResearcherAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL),
        "writer": WriterAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL),
        "coder": CoderAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL),
    }

    # Orchestrator plans and routes tasks automatically
    orchestrator = Orchestrator(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)
    results = orchestrator.run(goal=goal, agents=agents)

    # Save full output
    output_lines = [f"GOAL: {goal}\n", "=" * 60 + "\n"]
    for r in results:
        output_lines.append(f"\n[{r['agent'].upper()}] Task: {r['task']}\n")
        output_lines.append(r["result"])
        output_lines.append("\n" + "-" * 40 + "\n")

    output = "\n".join(output_lines)
    filename = "output/multi_agent_output.txt"
    write_file(filename, output)

    print(f"\n[Done] Full output saved to: {filename}")
    print(f"Total steps executed: {len(results)}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    goal = " ".join(sys.argv[1:]) or \
        "Build a Python script that fetches weather data and writes a daily summary report"
    run(goal)
