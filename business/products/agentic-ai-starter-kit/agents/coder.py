"""
Coder Agent — writes, reviews, and debugs code.
Supports Python, JavaScript, Apex, and more.
"""

from __future__ import annotations
from agent_core.llm import call_llm


CODER_SYSTEM = """
You are an expert software engineer specializing in Python, JavaScript, 
and Salesforce (Apex, LWC). You write clean, production-ready code.

When given a task:
1. Understand the requirement fully before writing code
2. Write clean, well-commented, production-grade code
3. Include error handling for edge cases
4. Add a brief explanation of what the code does and how to use it
5. If reviewing code, identify bugs, security issues, and improvements

Output format:
- Brief explanation (2-3 sentences)
- The code block
- Usage example (if applicable)
"""


class CoderAgent:
    def __init__(self, provider: str = "ollama", model: str = "llama3:latest"):
        self.provider = provider
        self.model = model
        self.name = "coder"

    def run(self, task: str, context: str = "") -> str:
        user_prompt = f"Coding task: {task}"
        if context:
            user_prompt += f"\n\nContext / requirements:\n{context}"

        return call_llm(
            provider=self.provider,
            model=self.model,
            system=CODER_SYSTEM,
            user=user_prompt,
        )
