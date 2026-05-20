"""
Agentic AI Starter Kit — Orchestrator
--------------------------------------
The orchestrator manages a team of agents, routes tasks, and
collects results. Supports OpenAI, Anthropic, and Ollama backends.
"""

from __future__ import annotations
import json
from typing import Any
from agent_core.llm import call_llm
from agent_core.memory import Memory


ORCHESTRATOR_SYSTEM = """
You are an orchestrator managing a team of specialized AI agents.
Given a user goal, break it into subtasks and assign each to the
correct agent. Respond ONLY with valid JSON in this format:

{
  "plan": [
    {"agent": "<agent_name>", "task": "<what to do>"},
    ...
  ]
}

Available agents: researcher, writer, coder
"""


class Orchestrator:
    def __init__(self, provider: str = "ollama", model: str = "llama3.2"):
        self.provider = provider
        self.model = model
        self.memory = Memory()

    def plan(self, goal: str) -> list[dict]:
        """Break a goal into a list of agent tasks."""
        response = call_llm(
            provider=self.provider,
            model=self.model,
            system=ORCHESTRATOR_SYSTEM,
            user=f"Goal: {goal}",
        )
        try:
            data = json.loads(response)
            return data.get("plan", [])
        except json.JSONDecodeError:
            # Fallback: single researcher task
            return [{"agent": "researcher", "task": goal}]

    def run(self, goal: str, agents: dict) -> list[dict]:
        """Execute a goal using available agents and return results."""
        plan = self.plan(goal)
        results = []
        context = ""

        print(f"\n[Orchestrator] Goal: {goal}")
        print(f"[Orchestrator] Plan: {json.dumps(plan, indent=2)}\n")

        for step in plan:
            agent_name = step.get("agent", "researcher")
            task = step.get("task", "")
            agent = agents.get(agent_name)

            if not agent:
                print(f"[Orchestrator] Unknown agent '{agent_name}', skipping.")
                continue

            print(f"[{agent_name.upper()}] Task: {task}")
            result = agent.run(task=task, context=context)
            print(f"[{agent_name.upper()}] Done.\n")

            context += f"\n\n--- {agent_name} output ---\n{result}"
            results.append({"agent": agent_name, "task": task, "result": result})
            self.memory.add(agent_name, task, result)

        return results
