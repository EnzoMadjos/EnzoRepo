"""
Example 1: Research Assistant Pipeline
----------------------------------------
Goal: Research a topic → summarize findings → save report to file.

Run: python examples/01_research_assistant.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DEFAULT_PROVIDER, DEFAULT_MODEL
from agent_core.orchestrator import Orchestrator
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from tools.file_ops import write_file


def run(topic: str = "What is agentic AI and why is it important in 2026?"):
    print("=" * 60)
    print("RESEARCH ASSISTANT PIPELINE")
    print("=" * 60)

    # Initialize agents
    researcher = ResearcherAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)
    writer = WriterAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)

    # Step 1: Research
    print(f"\n[Step 1] Researching: {topic}")
    research = researcher.run(task=topic)
    print(f"\n--- Research Output (preview) ---\n{research[:300]}...\n")

    # Step 2: Write a clean summary report
    print("[Step 2] Writing summary report...")
    report = writer.run(
        task=f"Write a clear, professional 3-paragraph summary report about: {topic}",
        context=research,
    )

    # Step 3: Save to file
    filename = "output/research_report.txt"
    write_file(filename, report)
    print(f"\n[Step 3] Report saved to: {filename}")
    print("\n--- Final Report ---")
    print(report)
    print("\n" + "=" * 60)

    return report


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "What is agentic AI and why is it important in 2026?"
    run(topic)
