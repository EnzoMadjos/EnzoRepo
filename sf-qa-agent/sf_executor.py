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
            raise ValueError(f"$step{step_num}.id referenced before step {step_num} ran")
        return results[step_num]["id"]
    return _REF_PATTERN.sub(replacer, value)


def execute(
    plan: list[dict[str, Any]],
    client: SalesforceClient,
    run_context: dict[str, Any] | None = None,
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
        step_num: int = int(op.get("step", 0) or 0)
        action: str = op.get("action", "create").lower()
        obj: str = op.get("object", "")
        label: str = op.get("label", f"Step {step_num}")
        fields: dict[str, Any] = op.get("fields", {})

        yield {"type": "step_start", "step": step_num, "label": label, "object": obj}

        try:
            # Resolve cross-references in field values
            resolved_fields = {k: _resolve_refs(v, results) for k, v in fields.items()}

            # Canonicalize common aliases to avoid hard failures.
            if action in {"edit", "modify", "change", "set", "link", "associate", "attach", "relate"}:
                action = "update"
            elif action in {"find", "search", "lookup", "open"}:
                action = "query"
            elif action == "save":
                action = "warning"

            if action == "warning":
                # Non-blocking warning step — surface to UI, do not execute
                msg = op.get("message", op.get("label", "Ambiguous step — review before running."))
                summary.append({
                    "step": step_num, "label": label, "object": obj,
                    "id": "", "url": "", "status": f"warning: {msg}",
                })
                yield {"type": "step_warning", "step": step_num, "message": msg}

            elif action == "create":
                result = client.create_record(obj, resolved_fields)
                results[step_num] = result
                summary.append({
                    "step": step_num, "label": label, "object": obj,
                    "id": result["id"], "url": result["url"], "status": "created",
                })
                yield {
                    "type": "step_done", "step": step_num,
                    "id": result["id"], "url": result["url"], "object": obj, "action": action,
                }

            elif action == "update":
                # record_id can be a direct ID or a $stepN.id reference
                record_id = _resolve_refs(op.get("record_id", ""), results)
                if not record_id:
                    raise ValueError("update action requires a 'record_id' field (e.g. '$step1.id')")
                result = client.update_record(obj, record_id, resolved_fields)
                results[step_num] = result
                summary.append({
                    "step": step_num, "label": label, "object": obj,
                    "id": result["id"], "url": result["url"], "status": "updated",
                })
                yield {
                    "type": "step_done", "step": step_num,
                    "id": result["id"], "url": result["url"], "object": obj, "action": action,
                }

            elif action == "delete":
                record_id = _resolve_refs(op.get("record_id", ""), results)
                if not record_id:
                    raise ValueError("delete action requires a 'record_id' field (e.g. '$step1.id')")
                client.delete_record(obj, record_id)
                results[step_num] = {"id": record_id, "url": ""}
                summary.append({
                    "step": step_num, "label": label, "object": obj,
                    "id": record_id, "url": "", "status": "deleted",
                })
                yield {"type": "step_done", "step": step_num, "id": record_id, "url": "", "object": obj, "action": action}

            elif action == "clone":
                source_id = _resolve_refs(op.get("record_id", ""), results)
                if not source_id:
                    raise ValueError("clone action requires a 'record_id' field (e.g. '$step1.id')")
                result = client.clone_record(obj, source_id, resolved_fields)
                results[step_num] = result
                summary.append({
                    "step": step_num, "label": label, "object": obj,
                    "id": result["id"], "url": result["url"], "status": "cloned",
                })
                yield {
                    "type": "step_done", "step": step_num,
                    "id": result["id"], "url": result["url"], "object": obj, "action": action,
                }

            elif action == "query":
                soql: str = op.get("soql", "") or fields.get("soql", "")
                if soql:
                    soql = _resolve_refs(soql, results)
                records = client.query(soql) if soql else []
                results[step_num] = {"id": records[0]["Id"] if records else "", "url": ""}
                summary.append({
                    "step": step_num, "label": label, "object": obj,
                    "id": f"{len(records)} record(s) found", "url": "", "status": "queried",
                })
                yield {
                    "type": "step_done", "step": step_num,
                    "id": f"{len(records)} found", "url": "", "object": obj, "action": action,
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
                **(run_context or {}),
            )
            summary.append({
                "step": step_num,
                "label": label,
                "object": obj,
                "id": "",
                "url": "",
                "status": f"error: {exc}",
            })
            yield {"type": "step_error", "step": step_num, "error": str(exc)}

    yield {"type": "summary", "results": summary}
