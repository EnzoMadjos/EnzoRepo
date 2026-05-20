"""
Example 2: Blog Post Generator Pipeline
-----------------------------------------
Goal: Given a topic, research it → generate a full blog post → save it.

Run: python examples/02_blog_post_generator.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DEFAULT_PROVIDER, DEFAULT_MODEL
from agents.researcher import ResearcherAgent
from agents.writer import WriterAgent
from tools.file_ops import write_file


def run(topic: str = "How to build your first AI agent with Python"):
    print("=" * 60)
    print("BLOG POST GENERATOR PIPELINE")
    print("=" * 60)

    researcher = ResearcherAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)
    writer = WriterAgent(provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL)

    # Step 1: Research the topic
    print(f"\n[Step 1] Researching: {topic}")
    research = researcher.run(task=f"Research key facts, trends, and examples about: {topic}")
    print(f"Research complete ({len(research)} chars)\n")

    # Step 2: Write the blog post
    print("[Step 2] Writing blog post...")
    blog_task = f"""
Write a complete, engaging blog post (600-900 words) about: {topic}

Structure:
- Catchy title (H1)
- Introduction (hook the reader)
- 3-4 main sections with subheadings (H2)
- Practical tips or takeaways
- Conclusion with a call to action

Tone: Professional but approachable. Target audience: developers and tech professionals.
"""
    blog_post = writer.run(task=blog_task, context=research)

    # Step 3: Save
    filename = "output/blog_post.md"
    write_file(filename, blog_post)
    print(f"\n[Step 3] Blog post saved to: {filename}")
    print("\n--- Blog Post Preview (first 500 chars) ---")
    print(blog_post[:500] + "...")
    print("\n" + "=" * 60)

    return blog_post


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "How to build your first AI agent with Python"
    run(topic)
