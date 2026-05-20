"""
Writer Agent — produces polished written content.
Blog posts, reports, summaries, emails, product descriptions.
"""

from __future__ import annotations
from agent_core.llm import call_llm


WRITER_SYSTEM = """
You are an expert writer and content specialist. You produce 
clear, engaging, well-structured written content.

When given a task:
1. Use any provided research or context as your source material
2. Write in a clear, professional tone unless instructed otherwise
3. Structure content with proper headings, paragraphs, and flow
4. Tailor the format to the content type (blog, report, email, etc.)
5. Be specific — avoid vague or generic statements

Output only the final written content, ready to use.
"""


class WriterAgent:
    def __init__(self, provider: str = "ollama", model: str = "llama3:latest"):
        self.provider = provider
        self.model = model
        self.name = "writer"

    def run(self, task: str, context: str = "") -> str:
        user_prompt = f"Writing task: {task}"
        if context:
            user_prompt += f"\n\nSource material / context:\n{context}"

        return call_llm(
            provider=self.provider,
            model=self.model,
            system=WRITER_SYSTEM,
            user=user_prompt,
        )
