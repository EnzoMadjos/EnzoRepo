"""
GitHub Models API client — used for ALL LLM calls (case generation + interactive).

All methods automatically fall back through the model rotation chain when a
model's daily quota is hit (HTTP 429). See llm/model_router.py for chains.
Raises DailyLimitExhausted when all models in the chain are exhausted.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

import httpx

from config import GITHUB_BASE_URL, GITHUB_TIMEOUT, GITHUB_TOKEN
from llm.model_router import (
    GENERATION_CHAIN,
    INTERACTIVE_CHAIN,
    DailyLimitExhausted,
    get_router,
)

logger = logging.getLogger(__name__)

_FENCE_STRIP = staticmethod(lambda c: c.split("```", 2)[1].lstrip("json\n").rsplit("```", 1)[0].strip()
                            if c.startswith("```") else c)


def _strip_fence(content: str) -> str:
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.rsplit("```", 1)[0].strip()
    return content


class GitHubModelsClient:
    def __init__(self):
        if not GITHUB_TOKEN:
            raise RuntimeError(
                "GITHUB_TOKEN is not set. "
                "Add it to Game Dev/The Coroner/.env"
            )
        self._headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

    def _is_429(self, exc: Exception) -> bool:
        return (
            isinstance(exc, httpx.HTTPStatusError)
            and exc.response.status_code == 429
        )

    async def _post(self, payload: dict) -> dict:
        """Raw POST to chat/completions — returns parsed response JSON."""
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            r = await client.post(
                f"{GITHUB_BASE_URL}/chat/completions",
                headers=self._headers,
                json=payload,
            )
            r.raise_for_status()
        return r.json()

    # ── Generation calls (use GENERATION_CHAIN) ───────────────────────────────

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Non-streaming JSON call — case generation. Falls back through GENERATION_CHAIN."""
        router = get_router()
        while True:
            model = router.next_generation()
            try:
                data = await self._post({
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                })
                logger.debug(f"[GH] chat_json via {model}")
                content = _strip_fence(data["choices"][0]["message"]["content"].strip())
                return json.loads(content)
            except DailyLimitExhausted:
                raise
            except Exception as e:
                if self._is_429(e):
                    router.mark_exhausted(model)
                    continue
                raise

    async def chat_text(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 1024,
    ) -> str:
        """Non-streaming text call — case generation. Falls back through GENERATION_CHAIN."""
        router = get_router()
        while True:
            model = router.next_generation()
            try:
                data = await self._post({
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                })
                logger.debug(f"[GH] chat_text via {model}")
                return data["choices"][0]["message"]["content"].strip()
            except DailyLimitExhausted:
                raise
            except Exception as e:
                if self._is_429(e):
                    router.mark_exhausted(model)
                    continue
                raise

    # ── Interactive calls (use INTERACTIVE_CHAIN) ─────────────────────────────

    async def chat_json_interactive(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> dict:
        """Non-streaming JSON — scoring/voice pass. Falls back through INTERACTIVE_CHAIN."""
        router = get_router()
        while True:
            model = router.next_interactive()
            try:
                data = await self._post({
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                })
                logger.debug(f"[GH] chat_json_interactive via {model}")
                content = _strip_fence(data["choices"][0]["message"]["content"].strip())
                return json.loads(content)
            except DailyLimitExhausted:
                raise
            except Exception as e:
                if self._is_429(e):
                    router.mark_exhausted(model)
                    continue
                raise

    async def chat_text_interactive(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 512,
    ) -> str:
        """Non-streaming text — interactive calls. Falls back through INTERACTIVE_CHAIN."""
        router = get_router()
        while True:
            model = router.next_interactive()
            try:
                data = await self._post({
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                })
                logger.debug(f"[GH] chat_text_interactive via {model}")
                return data["choices"][0]["message"]["content"].strip()
            except DailyLimitExhausted:
                raise
            except Exception as e:
                if self._is_429(e):
                    router.mark_exhausted(model)
                    continue
                raise

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        max_tokens: int = 300,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming SSE — witness interviews and specialist consults.
        Falls back through INTERACTIVE_CHAIN on 429.
        Raises DailyLimitExhausted before yielding any tokens if all models exhausted.
        """
        router = get_router()

        while True:
            model = router.next_interactive()  # raises DailyLimitExhausted if all out
            got_429 = False

            try:
                async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
                    async with client.stream(
                        "POST",
                        f"{GITHUB_BASE_URL}/chat/completions",
                        headers=self._headers,
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "stream": True,
                        },
                    ) as response:
                        if response.status_code == 429:
                            router.mark_exhausted(model)
                            got_429 = True
                        else:
                            response.raise_for_status()
                            logger.debug(f"[GH] chat_stream via {model}")
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
                            return  # success — exit the while loop

            except DailyLimitExhausted:
                raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    router.mark_exhausted(model)
                    got_429 = True
                else:
                    raise

            if not got_429:
                return  # shouldn't reach — success path returns above
            # got_429=True → loop continues with next model


# ── Singleton ─────────────────────────────────────────────────────────────────

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
                [{"role": "user", "content": "Reply with one word: ready"}],
                max_tokens=10,
            ),
            timeout=15,
        )
        return len(result) > 0
    except DailyLimitExhausted:
        logger.warning("GitHub Models smoke test: all generation models exhausted for today.")
        return False
    except Exception as e:
        logger.warning(f"GitHub Models smoke test failed: {e}")
        return False

