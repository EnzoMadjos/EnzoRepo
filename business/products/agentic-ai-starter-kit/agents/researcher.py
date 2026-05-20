"""
Researcher Agent — gathers information on a topic.
Uses web search tool if available, otherwise relies on LLM knowledge.
"""

from __future__ import annotations
from agent_core.llm import call_llm
from tools.search import web_search


RESEARCHER_SYSTEM = """
You are a research specialist. Your job is to gather accurate, 
well-structured information on any topic given to you.

When given a task:
1. Identify the key questions to answer
2. Provide comprehensive, factual information
3. Structure your response with clear sections
4. Include relevant details, examples, and data points
5. Be concise but thorough

If context from previous steps is provided, build on it.
"""


class ResearcherAgent:
    def __init__(self, provider: str = "ollama", model: str = "llama3:latest"):
        self.provider = provider
        self.model = model
        self.name = "researcher"

    def run(self, task: str, context: str = "") -> str:
        # Try to get fresh web search results first
        search_results = ""
        try:
            search_results = web_search(task)
            search_context = f"\n\nWeb search results:\n{search_results}\n"
        except Exception:
            search_context = ""

        user_prompt = f"Task: {task}"
        if context:
            user_prompt += f"\n\nPrevious context:\n{context}"
        if search_context:
            user_prompt += search_context

        return call_llm(
            provider=self.provider,
            model=self.model,
            system=RESEARCHER_SYSTEM,
            user=user_prompt,
        )
