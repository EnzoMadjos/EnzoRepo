"""
Executor: runs an operation plan produced by llm_planner against Salesforce.

Resolves $stepN.id cross-references between steps and yields progress events
as dicts so the caller (sf_app.py) can stream them to the browser via SSE.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from typing import Any

import app_logger
from sf_client import SalesforceClient

_REF_PATTERN = re.compile(r"\$step(\d+)\.id")


def _resolve_refs(value: Any, results: dict[int, dict[str, str]]) -> Any:
    """Replace $stepN.id tokens in string values with the actual record ID."""
    if not isinstance(value, str):
        return value

    def replacer(m: re.Match) -> str:
        step_num = int(m.group(1))
        if step_num not in results:
            raise ValueError(
                f"$step{step_num}.id referenced before step {step_num} ran"
            )
        return results[step_num]["id"]

    return _REF_PATTERN.sub(replacer, value)


def execute(
    plan: list[dict[str, Any]],
    client: SalesforceClient,
) -> Generator[dict[str, Any], None, None]:
    """
    Iterate through plan operations and yield progress event dicts:

    {"type": "step_start",  "step": N, "label": "...", "object": "..."}
    {"type": "step_done",   "step": N, "id": "...", "url": "...", "object": "..."}
    {"type": "step_error",  "step": N, "error": "..."}
    {"type": "summary",     "results": [...]}
    """
    results: dict[int, dict[str, str]] = {}
    summary: list[dict[str, Any]] = []

    for op in plan:
        step_num: int = op.get("step", 0)
        action: str = op.get("action", "create").lower()
        obj: str = op.get("object", "")
        label: str = op.get("label", f"Step {step_num}")
        fields: dict[str, Any] = op.get("fields", {})

        yield {"type": "step_start", "step": step_num, "label": label, "object": obj}

        try:
            # Resolve cross-references in field values
            resolved_fields = {k: _resolve_refs(v, results) for k, v in fields.items()}

            if action == "create":
                result = client.create_record(obj, resolved_fields)
                results[step_num] = result
                summary.append(
                    {
                        "step": step_num,
                        "label": label,
                        "object": obj,
                        "id": result["id"],
                        "url": result["url"],
                        "status": "created",
                    }
                )
                yield {
                    "type": "step_done",
                    "step": step_num,
                    "id": result["id"],
                    "url": result["url"],
                    "object": obj,
                }

            elif action == "query":
                soql: str = op.get("soql", "") or fields.get("soql", "")
                if soql:
                    soql = _resolve_refs(soql, results)
                records = client.query(soql) if soql else []
                results[step_num] = {
                    "id": records[0]["Id"] if records else "",
                    "url": "",
                }
                summary.append(
                    {
                        "step": step_num,
                        "label": label,
                        "object": obj,
                        "id": f"{len(records)} record(s) found",
                        "url": "",
                        "status": "queried",
                    }
                )
                yield {
                    "type": "step_done",
                    "step": step_num,
                    "id": f"{len(records)} found",
                    "url": "",
                    "object": obj,
                }

            else:
                raise ValueError(f"Unsupported action: {action}")

        except Exception as exc:
            app_logger.error(
                f"Step {step_num} failed: {exc}",
                exc=exc,
                step=step_num,
                object=obj,
                action=action,
            )
            summary.append(
                {
                    "step": step_num,
                    "label": label,
                    "object": obj,
                    "id": "",
                    "url": "",
                    "status": f"error: {exc}",
                }
            )
            yield {"type": "step_error", "step": step_num, "error": str(exc)}

    yield {"type": "summary", "results": summary}
