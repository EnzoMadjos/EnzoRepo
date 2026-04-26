"""
LLM Provider abstraction for Council of Salesforce.

Supported providers:
  - github   (default) — GitHub Models API, uses your Copilot subscription via GITHUB_TOKEN
  - anthropic          — Anthropic Claude API, uses ANTHROPIC_API_KEY (fallback/switch)

Provider is selected via:
  1. --provider CLI flag on controller.py
  2. LLM_PROVIDER env var
  3. Defaults to "github"

Model name aliases:
  github provider:
    gpt-5-mini    -> gpt-4.1-mini   (GitHub Models name)
    gpt-4.1       -> gpt-4.1        (same)
    claude-sonnet -> claude-sonnet-4-5 (same endpoint, different model)

Usage in controller:
  from services.provider import call_llm
  response = call_llm(provider, model, system_prompt, user_prompt)
"""

import os

# ---------------------------------------------------------------------------
# Model name aliases (normalize CLI shortcuts to provider-specific names)
# ---------------------------------------------------------------------------
GITHUB_MODEL_ALIASES = {
    "gpt-5-mini":    "gpt-4.1-mini",
    "gpt-4.1-mini":  "gpt-4.1-mini",
    "gpt-4.1":       "gpt-4.1",
    "claude-sonnet": "claude-sonnet-4-5",
    "claude":        "claude-sonnet-4-5",
}

ANTHROPIC_MODEL_ALIASES = {
    "claude-sonnet": "claude-sonnet-4-5-20251001",
    "claude":        "claude-sonnet-4-5-20251001",
    "claude-opus":   "claude-opus-4-5-20251001",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _github_call(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.15, max_tokens: int = 4096) -> str:
    """Call GitHub Models API using the OpenAI SDK (OpenAI-compatible endpoint)."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable not set.\n"
            "Create a GitHub Fine-grained PAT with Models: Read permission and set:\n"
            "  export GITHUB_TOKEN=github_pat_..."
        )

    resolved_model = GITHUB_MODEL_ALIASES.get(model, model)

    client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )

    resp = client.chat.completions.create(
        model=resolved_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    # extract response text
    content = None
    try:
        content = resp.choices[0].message.content
    except Exception:
        content = getattr(resp.choices[0].message, 'content', '')

    # try to extract usage if available
    usage = None
    try:
        usage = resp.usage if hasattr(resp, 'usage') else (resp.get('usage') if isinstance(resp, dict) else None)
    except Exception:
        usage = None

    return content, usage


def _anthropic_call(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.15, max_tokens: int = 4096) -> str:
    """Call Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Set: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    resolved_model = ANTHROPIC_MODEL_ALIASES.get(model, model)

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=resolved_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    # Anthropic client may return text in different locations
    content = getattr(resp, 'content', None) or getattr(resp, 'text', None) or (resp.get('content') if isinstance(resp, dict) else None)
    usage = None
    try:
        usage = resp.get('usage') if isinstance(resp, dict) else None
    except Exception:
        usage = None
    # normalize
    if isinstance(content, list) and len(content) > 0:
        content = content[0].get('text') if isinstance(content[0], dict) else str(content[0])
    return content or '', usage


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_llm(provider: str, model: str, system_prompt: str, user_prompt: str,
             temperature: float = 0.15, max_tokens: int = 4096, max_retries: int = 3) -> dict:
    """
    Call the selected LLM provider.

    Args:
        provider:      "github" or "anthropic"
        model:         model name or alias (e.g. "gpt-4.1", "gpt-5-mini", "claude-sonnet")
        system_prompt: agent system prompt
        user_prompt:   user message
        temperature:   0.0–1.0 (default: 0.15 for deterministic code gen)
        max_tokens:    max response tokens (default: 4096)

    Returns:
        LLM response text
    """
    # Basic retry loop with exponential backoff for transient errors (rate limits / network)
    attempt = 0
    while True:
        try:
            if provider == "github":
                text, usage = _github_call(model, system_prompt, user_prompt, temperature, max_tokens)
            elif provider == "anthropic":
                text, usage = _anthropic_call(model, system_prompt, user_prompt, temperature, max_tokens)
            else:
                raise ValueError(f"Unknown provider '{provider}'. Use 'github' or 'anthropic'.")

            return {"text": text, "usage": usage}
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                raise
            # exponential backoff
            import time
            wait = 2 ** (attempt - 1)
            time.sleep(wait)
            continue


def summarize_text(provider: str, model: str, text: str, max_tokens: int = 512) -> str:
    """Generate a short summary of `text` using the provider. Returns the summary string."""
    sys = "You are a concise summarization assistant. Produce a short, clear summary suitable as upstream context for other agents."
    # Use a small model if available
    use_model = model
    if 'gpt' in model and 'mini' not in model:
        use_model = 'gpt-5-mini'
    resp = call_llm(provider, use_model, sys, text, temperature=0.0, max_tokens=max_tokens)
    return resp.get('text') or ''
