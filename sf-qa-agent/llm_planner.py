"""
LLM Planner: converts a plain-English test script into a structured
JSON operation list using a local Ollama model.

Supported actions: create, update, delete, clone, query, warning
Cross-step references use $stepN.id syntax.
"""

from __future__ import annotations

import json
import re
from typing import Any

import app_logger
import config
import httpx

# ---------------------------------------------------------------------------
# System prompt — injected schema appended at call time
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = """\
You are a Salesforce test automation assistant. Convert a plain-English QA test \
script into a JSON array of Salesforce operations. The script can be written in \
any free-form style — you must interpret the intent.

## User Script Style (must support)
Many scripts follow this UI-style format:
- TEST: <title>
- STEP N: <instruction>
- Optional bullet lines under a step for IDs or values (e.g. "- Opportunity ID: 006...", "- Account: 001...")

Interpret these phrases as follows:
- "Open <Object> record" -> query existing record (usually by provided ID)
- "Look for <field>" -> query/read intent (not create)
- "Edit/Update <field>" -> update action
- "Select <related object>" -> set lookup reference field (for Opportunity+Account use AccountId)
- "Save" -> usually a UI confirmation step; do not create unsupported actions

## Output rules
1. Output ONLY a valid JSON array — no explanation, no markdown, no code fences.
2. Every element must have:
   - "step"      : integer (1-based)
   - "action"    : one of "create" | "update" | "delete" | "clone" | "query" | "warning"
   - "object"    : Salesforce API name (e.g. "Account", "Opportunity", "Contact")
   - "label"     : short human-readable description
   - "fields"    : object of { fieldAPIName: value }  (omit for delete/warning)
   - "record_id" : required for update, delete, clone — use "$stepN.id" to reference a prior step
   - "soql"      : required for query action
   - "message"   : required for warning action — explain what is unclear

3. Cross-step references: use "$stepN.id" as a field value to reference the ID \
   created/updated in step N (e.g. "AccountId": "$step1.id").
4. Always use exact Salesforce API field names from the schema provided below.
5. Keywords and their action mappings:
   - "create / add / new / make"            → action: "create"
   - "update / change / set / modify / edit"→ action: "update"
   - "delete / remove / trash / clean up"   → action: "delete"
   - "clone / copy / duplicate"             → action: "clone"
   - "link / relate / associate / attach"   → set the lookup field (e.g. AccountId) to "$stepN.id"
   - "query / find / search / get"          → action: "query"
6. If a step is ambiguous or cannot be mapped to a valid object/field, output a \
   "warning" action step instead of guessing — include a clear message explaining \
   what is unclear.
7. Never invent field names. Only use field API names from the ## Org Schema section.
8. Do NOT emit a warning just because a field like "Name" exists on multiple objects.
    Many Salesforce objects legitimately use a generic Name field, including Opportunity.
    If the requested object is clear from the step, use that object's valid Name field.
9. If the script mentions an account name while creating a related Opportunity, interpret
    that as a relationship hint and use AccountId to link to the Account step rather than
    warning about object mismatch.
10. Relationship guidance:
    - Opportunity name/title -> use Opportunity.Name
    - Related account for an Opportunity -> use Opportunity.AccountId
    - Querying an Opportunity's parent account name -> use SOQL relationship field Account.Name
    - Do not treat a phrase like "account name" as a literal field on Opportunity unless the schema says so.

## Examples

Input: "Create an Account called Acme Corp, then link a new Opportunity to it for $50,000 closing next month"
Output:
[
  {"step":1,"action":"create","object":"Account","label":"Create Acme Corp account","fields":{"Name":"Acme Corp"}},
  {"step":2,"action":"create","object":"Opportunity","label":"Link opportunity to Acme","fields":{"Name":"New Opportunity","AccountId":"$step1.id","Amount":50000,"CloseDate":"2026-05-21","StageName":"Prospecting"}}
]

Input: "Update the account name from step 1 to NewCo"
Output:
[
    {"step":2,"action":"update","object":"Account","label":"Rename account to NewCo","record_id":"$step1.id","fields":{"Name":"NewCo"}}
]

Input: "Clone the contact from step 2 with a different email: test@newco.com"
Output:
[
    {"step":3,"action":"clone","object":"Contact","label":"Clone contact with new email","record_id":"$step2.id","fields":{"Email":"test@newco.com"}}
]

Input: "Delete the opportunity created in step 3"
Output:
[
    {"step":4,"action":"delete","object":"Opportunity","label":"Delete opportunity from step 3","record_id":"$step3.id","fields":{}}
]

Input: "Create an account named Acme, then create an opportunity named Renewal for that account"
Output:
[
    {"step":1,"action":"create","object":"Account","label":"Create Acme account","fields":{"Name":"Acme"}},
    {"step":2,"action":"create","object":"Opportunity","label":"Create Renewal opportunity for Acme","fields":{"Name":"Renewal","AccountId":"$step1.id","StageName":"Prospecting","CloseDate":"2026-05-21"}}
]

Input: "Find the opportunity from step 1 and show its account name"
Output:
[
    {"step":2,"action":"query","object":"Opportunity","label":"Query opportunity account name","soql":"SELECT Id, Name, Account.Name FROM Opportunity WHERE Id = '$step1.id'"}
]

Input: "Do the thing with the stuff"
Output:
[
  {"step":1,"action":"warning","object":"","label":"Ambiguous instruction","fields":{},"message":"Cannot determine what Salesforce object or operation is intended. Please clarify."}
]
"""

_SCHEMA_HEADER = "\n## Org Schema (use ONLY these API names)\n"

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

# Common read-only / system fields to never inject into prompts
_SYSTEM_FIELDS = {
    "Id",
    "CreatedDate",
    "CreatedById",
    "LastModifiedDate",
    "LastModifiedById",
    "SystemModstamp",
    "IsDeleted",
    "LastActivityDate",
    "LastViewedDate",
    "LastReferencedDate",
}

# Objects we always include in schema even if not mentioned in the script
_ALWAYS_INCLUDE = {
    "Account",
    "Contact",
    "Lead",
    "Opportunity",
    "Case",
    "Task",
    "Event",
    "Contract",
    "Order",
    "Product2",
    "Pricebook2",
    "PricebookEntry",
    "Quote",
    "Asset",
    "Campaign",
    "CampaignMember",
}

# Regex to find capitalized words that might be sObject names
_LIKELY_OBJECT = re.compile(r"\b([A-Z][a-zA-Z0-9_]+)\b")
_SF_ID = re.compile(r"\b([a-zA-Z0-9]{15}|[a-zA-Z0-9]{18})\b")
_STEP_LINE = re.compile(r"^\s*STEP\s*\d+\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
_STEP_BLOCK = re.compile(
    r"^\s*STEP\s*(\d+)\s*:\s*(.+?)(?=^\s*STEP\s*\d+\s*:|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_CUSTOM_OBJECT = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*__c)\b")
_REF_STEP = re.compile(r"\$step(\d+)\.id")


def _build_object_lookup(all_objects: list[dict[str, Any]]) -> dict[str, str]:
    """Map lowercase API names and labels to canonical API object names."""
    lookup: dict[str, str] = {}
    for obj in all_objects:
        name = obj.get("name", "")
        label = obj.get("label", "")
        if not name:
            continue
        lookup[name.lower()] = name
        if label:
            lbl = label.lower()
            lookup[lbl] = name
            lookup[f"{lbl}s"] = name
            if lbl.endswith("y"):
                lookup[f"{lbl[:-1]}ies"] = name
    return lookup


def _detect_mentioned_objects(
    script: str, all_objects: list[dict[str, Any]]
) -> set[str]:
    """Detect objects mentioned in script using API names, labels, step headers, and custom objects."""
    lookup = _build_object_lookup(all_objects)
    mentioned: set[str] = set()

    candidates: set[str] = set()
    candidates.update(m.lower() for m in _LIKELY_OBJECT.findall(script))
    candidates.update(m.lower() for m in _CUSTOM_OBJECT.findall(script))

    for step_text in _STEP_LINE.findall(script):
        raw = step_text.strip().lower()
        # include both whole line and tokenized words to catch labels like "open opportunity record"
        candidates.add(raw)
        candidates.update(re.findall(r"[a-zA-Z][a-zA-Z0-9_]*", raw))

    for c in candidates:
        c = c.strip(" :-")
        if not c:
            continue
        if c in lookup:
            mentioned.add(lookup[c])

    return mentioned


def _build_schema_context(script: str, client) -> str:
    """
    Auto-detect likely sObject names from the script, fetch their field lists,
    and return a compact schema string for the prompt.
    """
    try:
        all_objects = client.describe_all_objects()
        all_names = {o["name"] for o in all_objects}

        # Describe all objects explicitly mentioned by user script (API name or label).
        mentioned = _detect_mentioned_objects(script, all_objects)
        objects_to_describe = mentioned & all_names
        if not objects_to_describe:
            # Fallback for very vague scripts.
            objects_to_describe = _ALWAYS_INCLUDE & all_names

        schema_title = f"{_SCHEMA_HEADER}Mentioned objects: {', '.join(sorted(objects_to_describe))}\n"

        lines: list[str] = []
        for obj_name in sorted(objects_to_describe):
            try:
                meta = client.describe(obj_name)
                fields = []
                for f in meta["fields"]:
                    if f["name"] in _SYSTEM_FIELDS:
                        continue
                    if not (f["createable"] or f["updateable"]):
                        continue
                    field_desc = f["name"]
                    if f.get("type") == "reference" and f.get("referenceTo"):
                        refs = "/".join(f["referenceTo"][:3])
                        field_desc += f"(ref:{refs})"
                    elif f.get("type"):
                        field_desc += f"({f['type']})"
                    fields.append(field_desc)
                lines.append(f"{obj_name}: {', '.join(fields)}")
            except Exception:
                pass
        return schema_title + "\n".join(lines) + "\n" if lines else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Validation pass
# ---------------------------------------------------------------------------


def _validate_plan(plan: list[dict[str, Any]], client) -> list[dict[str, Any]]:
    """
    Check each step's field names against the org schema.
    Appends a 'warnings' list to steps with unknown fields.
    Does not block execution — caller decides.
    """
    schema_cache: dict[str, set[str]] = {}

    def _get_fields(obj: str) -> set[str]:
        if obj not in schema_cache:
            try:
                meta = client.describe(obj)
                schema_cache[obj] = {f["name"] for f in meta["fields"]}
            except Exception:
                schema_cache[obj] = set()
        return schema_cache[obj]

    validated: list[dict[str, Any]] = []
    for step in plan:
        action = step.get("action", "")
        obj = step.get("object", "")
        fields = step.get("fields", {})
        warns: list[str] = []

        if action not in ("warning", "query", "delete") and obj and fields:
            known = _get_fields(obj)
            if known:
                for fname in fields:
                    if fname not in known:
                        # Simple fuzzy suggestion
                        close = [k for k in known if k.lower() == fname.lower()]
                        suggestion = f" — did you mean '{close[0]}'?" if close else ""
                        warns.append(f"Field '{fname}' not found on {obj}{suggestion}")

        if warns:
            step = {**step, "warnings": warns}
        validated.append(step)
    return validated


# ---------------------------------------------------------------------------
# Script-shape adaptation
# ---------------------------------------------------------------------------


def _extract_step_blocks(test_script: str) -> list[tuple[int, str, str]]:
    blocks: list[tuple[int, str, str]] = []
    for step_no, chunk in _STEP_BLOCK.findall(test_script):
        lines = [line.rstrip() for line in chunk.strip().splitlines() if line.strip()]
        if not lines:
            continue
        blocks.append((int(step_no), lines[0].strip(), "\n".join(lines[1:])))
    return blocks


def _extract_object_from_open_step(header: str) -> str:
    match = re.search(
        r"open\s+(?:the\s+)?([A-Za-z][A-Za-z0-9_]*)\s+record", header, re.IGNORECASE
    )
    return match.group(1) if match else ""


def _canonicalize_ui_field_name(field_name: str, object_name: str) -> str:
    cleaned = field_name.strip().strip(".:")
    collapsed = re.sub(r"\s+", " ", cleaned)
    lower = collapsed.lower()
    object_lower = object_name.lower().strip()

    if lower == "name" or lower == f"{object_lower} name":
        return "Name"

    return collapsed.replace(" ", "")


def _extract_field_name(text: str, prefix: str, object_name: str) -> str:
    match = re.search(rf"{prefix}\s+(.+?)(?:\s+field)?$", text.strip(), re.IGNORECASE)
    if not match:
        return ""
    return _canonicalize_ui_field_name(match.group(1), object_name)


def _extract_bullet_fields(body: str, object_name: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line.startswith("-") or ":" not in line:
            continue
        key, value = line[1:].split(":", 1)
        field_name = _canonicalize_ui_field_name(
            key.strip().removesuffix(" field"), object_name
        )
        field_value = value.strip()
        if field_name and field_value and not _SF_ID.fullmatch(field_value):
            fields[field_name] = field_value
    return fields


def _plan_for_direct_id_flow(test_script: str) -> list[dict[str, Any]] | None:
    """Handle explicit-record-ID UI scripts without relying on the LLM."""
    blocks = _extract_step_blocks(test_script)
    if not blocks:
        return None

    open_block = next(
        (
            (step_no, header, body)
            for step_no, header, body in blocks
            if "open" in header.lower() and "record" in header.lower()
        ),
        None,
    )
    if not open_block:
        return None

    _, open_header, open_body = open_block
    object_name = _extract_object_from_open_step(open_header)
    record_id = next(iter(_SF_ID.findall(open_body)), "")
    if not object_name or not record_id:
        return None

    queried_fields = ["Id", "Name"]
    look_step = next(
        (
            (step_no, header, body)
            for step_no, header, body in blocks
            if header.lower().startswith("look for ")
        ),
        None,
    )
    edit_step = next(
        (
            (step_no, header, body)
            for step_no, header, body in blocks
            if any(
                token in header.lower()
                for token in ["edit", "update", "change", "modify", "set "]
            )
        ),
        None,
    )

    look_field = (
        _extract_field_name(look_step[1], "look for", object_name) if look_step else ""
    )
    if look_field and look_field not in queried_fields:
        queried_fields.append(look_field)

    edit_fields = _extract_bullet_fields(edit_step[2], object_name) if edit_step else {}
    for field_name in edit_fields:
        if field_name not in queried_fields:
            queried_fields.append(field_name)

    plan: list[dict[str, Any]] = [
        {
            "step": 1,
            "action": "query",
            "object": object_name,
            "label": f"Open {object_name} record by ID",
            "soql": f"SELECT {', '.join(queried_fields)} FROM {object_name} WHERE Id = '{record_id}'",
            "fields": {},
        }
    ]

    if look_step and look_field:
        plan.append(
            {
                "step": len(plan) + 1,
                "action": "query",
                "object": object_name,
                "label": f"Look for {look_field} field on {object_name}",
                "soql": f"SELECT Id, {look_field} FROM {object_name} WHERE Id = '{record_id}'",
                "fields": {},
            }
        )

    if edit_step and edit_fields:
        plan.append(
            {
                "step": len(plan) + 1,
                "action": "update",
                "object": object_name,
                "label": f"Update {object_name} fields",
                "record_id": record_id,
                "fields": edit_fields,
            }
        )

    if any("save" in header.lower() for _, header, _ in blocks):
        plan.append(
            {
                "step": len(plan) + 1,
                "action": "warning",
                "object": object_name,
                "label": f"Save {object_name} changes",
                "fields": {},
                "message": "Save is a UI action; the API update is already applied directly to the record.",
            }
        )

    return plan if len(plan) > 1 else None


def _plan_for_ui_link_flow(test_script: str) -> list[dict[str, Any]] | None:
    """
    Adapt common UI-style scripts like:
    - Open Opportunity (with ID)
    - Select Account (with ID)
    - Save

    into deterministic API operations.
    """
    text = test_script.lower()
    if "opportunity" not in text or "account" not in text:
        return None

    ids = _SF_ID.findall(test_script)
    opp_id = next((i for i in ids if i.startswith("006")), "")
    acct_id = next((i for i in ids if i.startswith("001")), "")
    if not opp_id or not acct_id:
        return None

    looks_like_link_flow = any(
        k in text
        for k in ["link", "select the account", "save the update", "edit the account"]
    )
    if not looks_like_link_flow:
        return None

    return [
        {
            "step": 1,
            "action": "query",
            "object": "Opportunity",
            "label": "Open opportunity record",
            "soql": f"SELECT Id, Name, AccountId FROM Opportunity WHERE Id = '{opp_id}'",
            "fields": {},
        },
        {
            "step": 2,
            "action": "update",
            "object": "Opportunity",
            "label": "Link selected account to opportunity",
            "record_id": opp_id,
            "fields": {"AccountId": acct_id},
        },
    ]


def _normalize_actions(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map common action aliases from natural-language scripts to supported actions."""
    alias = {
        "edit": "update",
        "modify": "update",
        "change": "update",
        "set": "update",
        "link": "update",
        "relate": "update",
        "associate": "update",
        "attach": "update",
        "find": "query",
        "search": "query",
        "lookup": "query",
        "open": "query",
        "save": "warning",  # UI save is typically no-op in API automation
    }
    normalized: list[dict[str, Any]] = []
    for step in plan:
        action = str(step.get("action", "")).lower().strip()
        mapped = alias.get(action, action)
        fixed = {**step, "action": mapped}

        # Normalize common pseudo field emitted by some prompts/scripts
        fields = fixed.get("fields", {})
        if (
            isinstance(fields, dict)
            and "Account" in fields
            and "AccountId" not in fields
        ):
            fixed["fields"] = {**fields, "AccountId": fields["Account"]}
            fixed["fields"].pop("Account", None)

        if mapped == "warning" and action == "save" and "message" not in fixed:
            fixed["message"] = (
                "Save is a UI action; update was already applied via API."
            )

        normalized.append(fixed)
    return normalized


def _find_invalid_refs(value: Any, current_step: int) -> list[int]:
    """Return referenced step numbers that are self/forward refs for current step."""
    bad: list[int] = []
    if isinstance(value, str):
        for m in _REF_STEP.findall(value):
            ref = int(m)
            if ref >= current_step:
                bad.append(ref)
    elif isinstance(value, dict):
        for v in value.values():
            bad.extend(_find_invalid_refs(v, current_step))
    elif isinstance(value, list):
        for v in value:
            bad.extend(_find_invalid_refs(v, current_step))
    return bad


def _sanitize_step_references(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prevent runtime crashes from invalid self/forward $stepN.id references."""
    sanitized: list[dict[str, Any]] = []
    for i, step in enumerate(plan, start=1):
        step_no = int(step.get("step", i) or i)
        targets = [
            step.get("record_id", ""),
            step.get("soql", ""),
            step.get("fields", {}),
        ]
        bad_refs: list[int] = []
        for t in targets:
            bad_refs.extend(_find_invalid_refs(t, step_no))

        if bad_refs:
            bad_refs = sorted(set(bad_refs))
            sanitized.append(
                {
                    "step": step_no,
                    "action": "warning",
                    "object": step.get("object", ""),
                    "label": step.get("label", f"Step {step_no}"),
                    "fields": {},
                    "message": (
                        f"Invalid step reference(s) {', '.join(f'$step{r}.id' for r in bad_refs)} "
                        f"in step {step_no}. Use only previous-step IDs."
                    ),
                }
            )
            continue

        sanitized.append(step)
    return sanitized


# ---------------------------------------------------------------------------
# Ollama call + JSON extraction
# ---------------------------------------------------------------------------


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 8192},
    }
    with httpx.Client(timeout=600) as client:
        resp = client.post(f"{config.OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


def _extract_json(raw: str) -> list[dict[str, Any]]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in LLM output:\n{raw}")
    return json.loads(cleaned[start : end + 1])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def plan(test_script: str, client=None) -> list[dict[str, Any]]:
    """
    Convert a free-form plain-English test script to a list of operation dicts.
    Optionally pass a SalesforceClient to enable schema injection + field validation.
    Retries once on malformed JSON.
    """
    app_logger.info("LLM planning started", model=config.OLLAMA_MODEL)

    # Fast path for frequently used UI-style account-linking scripts.
    ui_flow = _plan_for_ui_link_flow(test_script)
    if ui_flow:
        app_logger.info("Using UI-flow adapter plan", steps=len(ui_flow))
        return ui_flow

    direct_id_flow = _plan_for_direct_id_flow(test_script)
    if direct_id_flow:
        app_logger.info("Using direct-ID adapter plan", steps=len(direct_id_flow))
        return direct_id_flow

    schema_ctx = _build_schema_context(test_script, client) if client else ""
    system_prompt = _SYSTEM_PROMPT_BASE + schema_ctx

    raw = ""
    for attempt in range(2):
        try:
            raw = _call_ollama(system_prompt, test_script)
            result = _sanitize_step_references(_normalize_actions(_extract_json(raw)))
            app_logger.info(f"LLM plan ready — {len(result)} step(s)")
            if client:
                result = _validate_plan(result, client)
            return result
        except (ValueError, json.JSONDecodeError) as exc:
            if attempt == 1:
                app_logger.error("LLM returned invalid JSON after 2 attempts", exc=exc)
                raise RuntimeError(
                    f"LLM returned invalid JSON after 2 attempts. Last error: {exc}\n"
                    f"Raw output:\n{raw}"
                ) from exc
    return []
