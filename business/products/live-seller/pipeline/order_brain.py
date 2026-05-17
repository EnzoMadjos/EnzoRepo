"""
Order Brain — LLM-powered comment parser.
Sends a batch of raw comments to phi4-mini (Ollama) or Llama-3.3-70B (GitHub Models fallback).
Returns structured JSON with order and bid intent per comment.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from config import settings
from pipeline.batch import RawComment

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are an order parser for a Filipino live selling stream.
Comments are in Tagalog, Bisaya, English, or a mix — informal, with typos.

Your job: classify each comment and extract order or bid intent.

Common order patterns:
- "+1", "+2", "+", "mine", "pa-mine", "pamine", "order", "kuha", "bili", "penge", "ibili"
- "[product] [size/color/variant]", "2 [product]", "[product] x3"
- "isa" (1), "dalawa" (2), "tatlo" (3), "apat" (4), "lima" (5)

Common bid patterns:
- A number alone: "500", "600", "1000"
- "bid 600", "bi-bid 600", "600 na", "600 po"

Return ONLY a raw JSON array. No explanation. No markdown. No extra text.
Each object must have these exact keys:
{
  "comment_id": "<original comment_id passed in>",
  "intent": "order" | "bid" | "question" | "ignore",
  "product_hint": "<product name hint from comment or null>",
  "variant_hint": "<color/size hint or null>",
  "qty": <integer, default 1>,
  "bid_amount": <float or null — only for bid intent>,
  "buyer_name": "<name if buyer mentioned their name, else null>",
  "handle": "<handle/username if present, else null>",
  "confidence": <float 0.0 to 1.0>
}
"""


@dataclass
class ParsedComment:
    comment_id: str
    intent: str  # order | bid | question | ignore
    product_hint: Optional[str]
    variant_hint: Optional[str]
    qty: int
    bid_amount: Optional[float]
    buyer_name: Optional[str]
    handle: Optional[str]
    confidence: float
    raw_text: str
    received_at_ms: int


class OrderBrain:
    def __init__(self, products_snapshot_fn, session_orders_fn) -> None:
        """
        products_snapshot_fn: callable → list[dict] (active products + variants)
        session_orders_fn: callable → list[dict] (last 5 confirmed orders this session)
        """
        self._get_products = products_snapshot_fn
        self._get_orders = session_orders_fn
        self._ollama_failures = 0

    async def parse_batch(self, comments: list[RawComment]) -> list[ParsedComment]:
        products = self._get_products()
        recent_orders = self._get_orders()

        user_prompt = self._build_user_prompt(comments, products, recent_orders)

        raw_json = None
        use_fallback = self._ollama_failures >= settings.ollama_max_retries

        if not use_fallback:
            raw_json = await self._call_ollama(user_prompt)

        if raw_json is None:
            log.warning("Falling back to GitHub Models API")
            raw_json = await self._call_github_models(user_prompt)

        if raw_json is None:
            log.error("Both LLM endpoints failed — returning empty parse result")
            return []

        return self._parse_response(raw_json, comments)

    # ------------------------------------------------------------------ #
    # Prompt builder
    # ------------------------------------------------------------------ #

    def _build_user_prompt(
        self,
        comments: list[RawComment],
        products: list[dict],
        recent_orders: list[dict],
    ) -> str:
        comments_json = json.dumps(
            [{"comment_id": str(c.received_at_ms), "text": c.text} for c in comments],
            ensure_ascii=False,
        )
        products_json = json.dumps(products, ensure_ascii=False)
        orders_json = json.dumps(recent_orders[-5:], ensure_ascii=False)

        return (
            f"Active products:\n{products_json}\n\n"
            f"Recent confirmed orders (context):\n{orders_json}\n\n"
            f"Comments to parse:\n{comments_json}"
        )

    # ------------------------------------------------------------------ #
    # LLM callers
    # ------------------------------------------------------------------ #

    async def _call_ollama(self, user_prompt: str) -> Optional[str]:
        url = f"{settings.ollama_base_url}/api/chat"
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        for attempt in range(1, settings.ollama_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    content = resp.json()["message"]["content"]
                    self._ollama_failures = 0
                    return content
            except Exception as e:
                log.warning("Ollama attempt %d/%d failed: %s", attempt, settings.ollama_max_retries, e)
                self._ollama_failures += 1
                await asyncio.sleep(1.0)
        return None

    async def _call_github_models(self, user_prompt: str) -> Optional[str]:
        if not settings.github_models_token:
            log.error("GitHub Models API token not configured")
            return None
        url = f"{settings.github_models_endpoint}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.github_models_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.github_models_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.error("GitHub Models API failed: %s", e)
            return None

    # ------------------------------------------------------------------ #
    # Response parser
    # ------------------------------------------------------------------ #

    def _parse_response(
        self, raw: str, original_comments: list[RawComment]
    ) -> list[ParsedComment]:
        # Strip markdown code fences if model added them
        raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"```$", "", raw.strip())

        comment_map = {str(c.received_at_ms): c for c in original_comments}

        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            log.error("LLM returned unparseable JSON: %s", raw[:300])
            return []

        results: list[ParsedComment] = []
        for item in items:
            cid = str(item.get("comment_id", ""))
            original = comment_map.get(cid)
            results.append(
                ParsedComment(
                    comment_id=cid,
                    intent=item.get("intent", "ignore"),
                    product_hint=item.get("product_hint"),
                    variant_hint=item.get("variant_hint"),
                    qty=int(item.get("qty", 1)),
                    bid_amount=item.get("bid_amount"),
                    buyer_name=item.get("buyer_name"),
                    handle=item.get("handle"),
                    confidence=float(item.get("confidence", 0.0)),
                    raw_text=original.text if original else "",
                    received_at_ms=original.received_at_ms if original else 0,
                )
            )
        return results


# Late import to avoid circular at module level
import asyncio
