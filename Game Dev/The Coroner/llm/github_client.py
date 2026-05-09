"""
GitHub Models API client — used for ALL LLM calls (case generation + interactive).
Generation model: Llama-3.3-70B-Instruct (or GITHUB_MODEL env var)
Interactive model: gpt-4.1-mini (or INTERACTIVE_MODEL env var)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

import httpx

from config import (
    GITHUB_BASE_URL,
    GITHUB_MODEL,
    GITHUB_TIMEOUT,
    GITHUB_TOKEN,
    INTERACTIVE_MODEL,
)

logger = logging.getLogger(__name__)


class GitHubModelsClient:
    def __init__(self):
        if not GITHUB_TOKEN:
            raise RuntimeError(
                "GITHUB_TOKEN is not set. "
                "Add it to Game Dev/The Coroner/.env — needed for case generation."
            )
        self._headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """
        Send a chat completion request expecting a JSON response.
        Returns the parsed JSON dict from the model's reply.
        Raises on HTTP error, timeout, or invalid JSON.
        """
        payload = {
            "model": GITHUB_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.post(
                f"{GITHUB_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Strip markdown code fences if model wraps the JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()

        return json.loads(content)

    async def chat_text(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> str:
        """Send a chat request and return the raw text response."""
        payload = {
            "model": model or GITHUB_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.post(
                f"{GITHUB_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    async def chat_json_interactive(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> dict:
        """
        Non-streaming JSON call using the interactive model (gpt-4.1-mini).
        Used for scoring and voice pass where structured output is needed.
        """
        payload = {
            "model": INTERACTIVE_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.post(
                f"{GITHUB_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()
        return json.loads(content)

    async def chat_text_interactive(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 512,
    ) -> str:
        """Non-streaming text call using the interactive model (gpt-4.1-mini)."""
        payload = {
            "model": INTERACTIVE_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.post(
                f"{GITHUB_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 300,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming chat using the interactive model (gpt-4.1-mini).
        Yields text tokens as they arrive via SSE.
        Used for witness interviews and specialist consults.
        """
        payload = {
            "model": INTERACTIVE_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{GITHUB_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload_str = line[6:].strip()
                    if payload_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


# Singleton
_client: GitHubModelsClient | None = None


def get_github_client() -> GitHubModelsClient:
    global _client
    if _client is None:
        _client = GitHubModelsClient()
    return _client


async def smoke_test() -> bool:
    """Quick connectivity check — returns True if GitHub Models API responds."""
    try:
        client = get_github_client()
        result = await asyncio.wait_for(
            client.chat_text(
                [{"role": "user", "content": 'Reply with exactly: {"status":"ok"}'}],
                max_tokens=20,
            ),
            timeout=15,
        )
        return "ok" in result.lower()
    except Exception as e:
        logger.warning(f"GitHub Models smoke test failed: {e}")
        return False
