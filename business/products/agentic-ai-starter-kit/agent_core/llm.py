"""
LLM abstraction — supports OpenAI, Anthropic, and Ollama.
Set your provider in config.py or pass it directly.
"""

from __future__ import annotations


def call_llm(
    provider: str,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Unified LLM call. Returns the assistant's reply as a string.

    Providers:
        - "openai"    → OpenAI API (gpt-4o, gpt-4o-mini, etc.)
        - "anthropic" → Anthropic API (claude-3-5-sonnet, etc.)
        - "ollama"    → Local Ollama (llama3.2, phi4-mini, etc.)
    """
    if provider == "openai":
        return _call_openai(model, system, user, temperature, max_tokens)
    elif provider == "anthropic":
        return _call_anthropic(model, system, user, temperature, max_tokens)
    elif provider == "ollama":
        return _call_ollama(model, system, user)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai', 'anthropic', or 'ollama'.")


def _call_openai(model, system, user, temperature, max_tokens) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")

    from config import OPENAI_API_KEY
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _call_anthropic(model, system, user, temperature, max_tokens) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")

    from config import ANTHROPIC_API_KEY
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def _call_ollama(model, system, user) -> str:
    try:
        import requests
    except ImportError:
        raise ImportError("Run: pip install requests")

    from config import OLLAMA_BASE_URL
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=300,  # 5 min — larger models (llama3, mistral) need more time on CPU
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}.\n"
            "Fix: make sure Ollama is running → run 'ollama serve' in a terminal."
        )
    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            f"Ollama timed out while running model '{model}'.\n"
            "Fix: try a smaller model (e.g. llama3.2:3b or phi4-mini) or wait longer.\n"
            "Tip: larger models need more RAM and time on CPU-only machines."
        )
