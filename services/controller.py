#!/usr/bin/env python3
"""
Council of Salesforce — Controller

Routes a user prompt through the selected Council agent (or auto-chains agents when
starting with the Architect). Calls real LLM providers via services/provider.py.

Usage:
  # Real LLM call via GitHub Models (uses GITHUB_TOKEN):
  python services/controller.py --agent architect --model gpt-4.1 --prompt "Add Orders object linked to Account"

  # Switch to Anthropic (uses ANTHROPIC_API_KEY):
  python services/controller.py --agent debugger --provider anthropic --model claude-sonnet --prompt "..."

  # Dry-run / simulation (no API calls):
  python services/controller.py --agent architect --model gpt-4.1 --prompt "..." --simulate

Provider auto-detection (in order):
  1. --provider flag
  2. LLM_PROVIDER env var
  3. Defaults to "github"

Required env vars:
  GITHUB_TOKEN      — GitHub fine-grained PAT with Models: Read permission  (provider=github)
  ANTHROPIC_API_KEY — Anthropic API key                                      (provider=anthropic)
"""

import argparse
import json
import os
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "agents" / "council-of-salesforce"
OUT = BASE / "workspace_outputs"
OUT.mkdir(parents=True, exist_ok=True)

# Agents that the Architect will automatically chain to
ARCHITECT_CHAIN = ["code-assistant", "test-engineer"]


# Simple request tracker to enforce a soft requests-per-minute quota
class RequestTracker:
    def __init__(self, max_per_min: int = None):
        # default from env or 45 req/min
        self.max_per_min = max_per_min or int(os.environ.get("LLM_MAX_RPM", "45"))
        self.calls = deque()

    def wait_for_slot(self):
        # remove timestamps older than 60s
        now = time.time()
        while self.calls and now - self.calls[0] > 60:
            self.calls.popleft()
        if len(self.calls) < self.max_per_min:
            self.calls.append(now)
            return
        # otherwise sleep until a slot frees
        wait = 60 - (now - self.calls[0]) + 0.1
        time.sleep(wait)
        # recurse once
        self.wait_for_slot()


REQUEST_TRACKER = RequestTracker()


def load_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


def build_system_prompt(agent_name: str) -> str:
    folder = BASE / agent_name.replace(" ", "-").lower()
    return load_text(folder / "system.prompt.md")


def build_user_prompt(
    agent_name: str, user_prompt: str, upstream_context: str = ""
) -> str:
    folder = BASE / agent_name.replace(" ", "-").lower()
    user_tmpl = load_text(folder / "user.template.md")
    user_section = user_tmpl.replace("{{one-line business goal}}", user_prompt)
    if upstream_context:
        return f"{user_section}\n\n--- Context from upstream agent ---\n{upstream_context}\n\nUser request: {user_prompt}"
    return f"{user_section}\n\nUser request: {user_prompt}"


def run_agent(
    agent_name: str,
    model: str,
    provider: str,
    user_prompt: str,
    upstream_context: str = "",
    simulate: bool = False,
) -> dict:
    """Call one Council agent and return a result dict."""
    system = build_system_prompt(agent_name)
    user = build_user_prompt(agent_name, user_prompt, upstream_context)

    if simulate:
        text = (
            f"[SIMULATE] {agent_name} | {model} | {provider}\nPrompt: {user[:150]}..."
        )
    else:
        from services.provider import call_llm

        print(f"  -> Calling {agent_name} via {provider}/{model}...", flush=True)
        # respect soft quota
        REQUEST_TRACKER.wait_for_slot()
        resp = call_llm(provider, model, system, user)
        # normalize response: resp is a dict {text, usage}
        if isinstance(resp, dict):
            text = resp.get("text")
            usage = resp.get("usage")
        else:
            text = resp
            usage = None

    return {
        "agent": agent_name,
        "model": model,
        "provider": provider,
        "response": text,
        "usage": locals().get("usage"),
    }


def orchestrate(
    start_agent: str,
    initial_model: str,
    provider: str,
    prompt: str,
    simulate: bool = False,
    follow_model: str = None,
) -> tuple:
    start_agent_key = start_agent.replace(" ", "-").lower()
    results = []

    # Step 1: call the entry agent using the initial model
    first = run_agent(
        start_agent_key, initial_model, provider, prompt, simulate=simulate
    )
    results.append(first)

    # Step 2: if entry is architect, chain downstream agents with architect's output as context
    if start_agent_key == "architect":
        arch_context = first["response"]
        # decide follow-up model: if follow_model provided use it, else use initial_model
        fm = follow_model or initial_model
        for follow in ARCHITECT_CHAIN:
            follow_prompt = f"Implement the following proposal from the Architect:\n\n{arch_context}\n\nOriginal request: {prompt}"
            result = run_agent(
                follow,
                fm,
                provider,
                follow_prompt,
                upstream_context=arch_context,
                simulate=simulate,
            )
            results.append(result)

    out = {
        "start_agent": start_agent_key,
        "model": initial_model,
        "provider": provider,
        "simulate": simulate,
        "prompt": prompt,
        "responses": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUT / f"output_{start_agent_key}_{ts}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out_path, out


def main():
    p = argparse.ArgumentParser(description="Council of Salesforce — agent controller")
    p.add_argument(
        "--agent",
        required=True,
        help="Entry agent name: architect | code-assistant | test-engineer | "
        "deployment-officer | debugger | compliance-auditor | ux-flow-designer",
    )
    p.add_argument(
        "--model",
        default="gpt-4.1",
        help="Model name/alias: gpt-4.1 | gpt-5-mini | gpt-4.1-mini | claude-sonnet (default: gpt-4.1)",
    )
    p.add_argument(
        "--hybrid",
        action="store_true",
        help="Run hybrid flow: mini model for initial work, then full model for final review",
    )
    p.add_argument(
        "--force-model",
        default=None,
        help="Force a single model for all calls (overrides hybrid).",
    )
    p.add_argument(
        "--provider",
        default=None,
        help='LLM provider: github | anthropic (default: env LLM_PROVIDER or "github")',
    )
    p.add_argument(
        "--prompt", required=True, help="Your Salesforce request or question"
    )
    p.add_argument(
        "--simulate",
        action="store_true",
        help="Dry-run: build prompts but do not call any LLM API",
    )
    args = p.parse_args()

    provider = args.provider or os.environ.get("LLM_PROVIDER", "github")

    print(f"\nCouncil of Salesforce")
    print(f"  Agent   : {args.agent}")
    print(f"  Model   : {args.model}")
    print(f"  Provider: {provider}")
    print(f"  Mode    : {'SIMULATE' if args.simulate else 'LIVE'}\n")
    # Determine model selection for initial and final stages
    if args.force_model:
        initial_model = final_model = args.force_model
    elif args.hybrid:
        # Hybrid default: use mini for initial passes and full for final review
        if "gpt" in args.model:
            initial_model = "gpt-5-mini"
            final_model = "gpt-4.1"
        else:
            # fallback: use provided model for both stages for non-gpt names
            initial_model = args.model
            final_model = args.model
    else:
        initial_model = final_model = args.model

    # decide follow_model for chained agents: prefer mini for intermediate steps when possible
    if args.force_model:
        follow_model = initial_model
    elif args.hybrid:
        # use minis for chained agents
        follow_model = "gpt-5-mini"
    else:
        follow_model = initial_model

    try:
        path, result = orchestrate(
            args.agent,
            initial_model,
            provider,
            args.prompt,
            args.simulate,
            follow_model=follow_model,
        )

        # If hybrid mode requested and not simulating, run a final review with the final_model
        if args.hybrid and not args.simulate:
            # aggregate upstream responses to provide context for final review
            aggregated = "\n\n".join(
                [
                    (
                        r.get("response")
                        if isinstance(r.get("response"), str)
                        else str(r.get("response"))
                    )
                    for r in result["responses"]
                ]
            )
            # summarize aggregated output to reduce token usage
            from services.provider import summarize_text

            summary = summarize_text(provider, final_model, aggregated)
            review_prompt = f"Please review and critique the combined outputs below and provide any fixes or improvements:\n\n{summary}\n\nOriginal request: {args.prompt}"
            print("\nRunning final review using", final_model)
            final = run_agent(
                args.agent.replace(" ", "-").lower(),
                final_model,
                provider,
                review_prompt,
                upstream_context=summary,
                simulate=args.simulate,
            )
            result["responses"].append(final)

    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nOutput saved to: {path}\n")
    print("=" * 60)
    for r in result["responses"]:
        print(f"\n[{r['agent'].upper()}]")
        print(r["response"])
        print("-" * 60)


if __name__ == "__main__":
    main()
