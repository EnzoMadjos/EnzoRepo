"""
LLM Planner: converts a plain-English test script into a structured
JSON operation list using a local Ollama model.

Expected output format from the LLM:
[
  {
    "step": 1,
    "action": "create",
    "object": "Account",
    "label": "Create customer account",
    "fields": {
      "Name": "Acme Corporation",
      "Type": "Customer",
      "Industry": "Technology"
    }
  },
  {
    "step": 2,
    "action": "create",
    "object": "Contact",
    "label": "Create contact linked to step 1",
    "fields": {
      "FirstName": "John",
      "LastName": "Smith",
      "Email": "john@acme.com",
      "AccountId": "$step1.id"
    }
  }
]

Cross-step references use $stepN.id syntax.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

import app_logger
import config

_SYSTEM_PROMPT = """\
You are a Salesforce test automation assistant. Your ONLY job is to convert a
plain-English QA test script into a JSON array of Salesforce record operations.

Rules:
1. Output ONLY valid JSON — no explanation, no markdown, no code fences.
2. Each element must have: step (int), action ("create"), object (Salesforce API name),
   label (short description string), fields (object of field API name → value).
3. For fields that reference a record created in a previous step, use the token
   "$stepN.id" as the value (e.g. "$step1.id" to reference the ID from step 1).
4. Use Salesforce standard API field names (e.g. FirstName, LastName, AccountId).
5. If the script is ambiguous, make the most reasonable assumption.
6. Never include SOQL, Apex, or any non-create operations unless the script
   explicitly says to query or update — in that case use action "query" or "update".

Test script format you will receive:
TEST: <title>

STEP N: <Salesforce Object Type>
  - Field: Value
  - Field: Value (linked to Step M <Object>)

Now convert the following test script to JSON.
"""


def _call_ollama(prompt: str) -> str:
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096},
    }
    with httpx.Client(timeout=120) as client:
        resp = client.post(f"{config.OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


def _extract_json(raw: str) -> list[dict[str, Any]]:
    """Strip markdown fences if present and parse JSON."""
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    # Find first [ and last ]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in LLM output:\n{raw}")
    return json.loads(cleaned[start : end + 1])


def plan(test_script: str) -> list[dict[str, Any]]:
    """
    Convert a plain-English test script to a list of operation dicts.
    Retries once on malformed JSON.
    """
    app_logger.info("LLM planning started", model=config.OLLAMA_MODEL)
    for attempt in range(2):
        try:
            raw = _call_ollama(test_script)
            result = _extract_json(raw)
            app_logger.info(f"LLM plan ready — {len(result)} step(s)")
            return result
        except (ValueError, json.JSONDecodeError) as exc:
            if attempt == 1:
                app_logger.error("LLM returned invalid JSON after 2 attempts", exc=exc)
                raise RuntimeError(
                    f"LLM returned invalid JSON after 2 attempts. Last error: {exc}\n"
                    f"Raw output:\n{raw}"
                ) from exc
    return []  # unreachable
