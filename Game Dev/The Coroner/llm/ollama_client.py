"""
Ollama client — used for all interactive calls during gameplay.
Model: phi4-mini (fits GTX 1650 4GB VRAM, ~20-30 tok/s).
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import httpx

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_TIMEOUT,
)

logger = logging.getLogger(__name__)


class OllamaClient:

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        num_ctx: int = OLLAMA_NUM_CTX,
    ) -> dict:
        """
        Non-streaming JSON chat call.
        Uses Ollama's format:'json' mode for schema compliance.
        """
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data["message"]["content"].strip()

        # Strip markdown fences if present
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
        num_ctx: int = OLLAMA_NUM_CTX,
    ) -> str:
        """Non-streaming text chat call."""
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        return data["message"]["content"].strip()

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.85,
        num_ctx: int = OLLAMA_NUM_CTX,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming chat — yields text chunks as they arrive.
        Used for witness interviews and specialist consults (SSE).
        """
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }

        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue


# Singleton
_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client


async def smoke_test() -> bool:
    """Quick connectivity check — returns True if Ollama responds."""
    try:
        client = get_ollama_client()
        result = await client.chat_text(
            [{"role": "user", "content": "Say: ready"}],
            temperature=0.1,
            num_ctx=64,
        )
        return len(result) > 0
    except Exception as e:
        logger.warning(f"Ollama smoke test failed: {e}")
        return False
