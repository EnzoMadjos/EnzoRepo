"""
Auto-learning layer for ATLAS.
After every conversation exchange, this runs silently in the background
and extracts facts about the user — no manual training tab needed.
ATLAS learns just from talking to you.
"""

import hashlib
import json
import re as _re
import threading
from pathlib import Path

import ollama
from training_memory import add_training, list_training

# Quick heuristic patterns — no LLM needed for obvious facts
_QUICK_PATTERNS = [
    (
        _re.compile(
            r"\bI(?:'m| am)\s+(?:a|an)\s+([a-zA-Z][a-zA-Z\s]{2,30}?)(?:\.|,|\s|$)",
            _re.I,
        ),
        lambda m: f"User is a {m.group(1).strip()}",
    ),
    (
        _re.compile(
            r"\bI work(?:ed)?\s+(?:at|for|in|as)\s+([a-zA-Z0-9][a-zA-Z0-9\s]{2,40}?)(?:\.|,|$)",
            _re.I,
        ),
        lambda m: f"User works at/as {m.group(1).strip()}",
    ),
    (
        _re.compile(
            r"\bI(?:'m| am)\s+from\s+([a-zA-Z][a-zA-Z\s]{2,30}?)(?:\.|,|$)", _re.I
        ),
        lambda m: f"User is from {m.group(1).strip()}",
    ),
    (
        _re.compile(r"\bI prefer\s+(.{5,60}?)(?:\.|,|$)", _re.I),
        lambda m: f"User prefers {m.group(1).strip()}",
    ),
    (
        _re.compile(r"\bI(?:'m| am)\s+(\d+)\s*(?:years old|yo\b)", _re.I),
        lambda m: f"User is {m.group(1)} years old",
    ),
    (
        _re.compile(r"\bmy name is\s+([A-Z][a-z]+)"),
        lambda m: f"User's name is {m.group(1)}",
    ),
    (
        _re.compile(r"\bI(?:'m| am)\s+(?:called|known as)\s+([A-Z][a-z]+)"),
        lambda m: f"User is called {m.group(1)}",
    ),
    (
        _re.compile(
            r"\bI(?:'m| am)\s+(?:using|building|making|working on)\s+(.{5,60}?)(?:\.|,|$)",
            _re.I,
        ),
        lambda m: f"User is working on {m.group(1).strip()}",
    ),
]

# Correction patterns — detect when user is correcting a wrong assumption
_CORRECTION_PATTERNS = [
    (
        _re.compile(
            r"(?:no[,.]?\s+)?actually[,.]?\s+(?:it(?:'s| is)|I(?:'m| am)|the answer is|that(?:'s| is))\s+(.{5,80}?)(?:\.|$)",
            _re.I,
        ),
        lambda m: f"Correction: actually {m.group(1).strip()}",
    ),
    (
        _re.compile(
            r"(?:no[,.]?\s+)?(?:wrong|incorrect)[,.]\s+(?:it(?:'s| is)|I(?:'m| am)|the)\s+(.{5,80}?)(?:\.|$)",
            _re.I,
        ),
        lambda m: f"Correction: {m.group(1).strip()}",
    ),
    (
        _re.compile(
            r"that(?:'s| is) (?:not|wrong|incorrect)[,.]\s+(?:it(?:'s| is)|I(?:'m| am))\s+(.{5,80}?)(?:\.|$)",
            _re.I,
        ),
        lambda m: f"Correction: {m.group(1).strip()}",
    ),
    (
        _re.compile(
            r"I (?:don't|do not) (?:like|want|prefer|use)\s+(.{5,60}?)(?:\.|,|$)", _re.I
        ),
        lambda m: f"User does not like/want: {m.group(1).strip()}",
    ),
    (
        _re.compile(r"I (?:hate|dislike|avoid)\s+(.{5,60}?)(?:\.|,|$)", _re.I),
        lambda m: f"User dislikes/avoids: {m.group(1).strip()}",
    ),
    (
        _re.compile(r"never (?:do|use|say|call)\s+(.{5,60}?)(?:\.|,|$)", _re.I),
        lambda m: f"User rule - never: {m.group(1).strip()}",
    ),
    (
        _re.compile(r"always (?:do|use|say|call)\s+(.{5,60}?)(?:\.|,|$)", _re.I),
        lambda m: f"User rule - always: {m.group(1).strip()}",
    ),
]


def _correction_extract(text: str) -> list:
    facts = []
    for pattern, formatter in _CORRECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                facts.append(formatter(match))
            except Exception:
                pass
    return facts


def _quick_extract(text: str) -> list:
    facts = []
    for pattern, formatter in _QUICK_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                facts.append(formatter(match))
            except Exception:
                pass
    return facts


# Don't re-save facts we already have (dedup by hash)
_seen_hashes: set = set()

# How many auto-learned entries to keep max (oldest get pruned)
MAX_AUTO_ENTRIES = 200

# Cooldown: only run LLM extraction once per N seconds to avoid blocking Ollama
_LLM_EXTRACT_COOLDOWN = 300  # 5 minutes
_last_llm_extract: float = 0.0

# Minimum message length worth analyzing
MIN_MESSAGE_LEN = 30

# Phrases that indicate a trivial/conversational exchange — skip extraction
_TRIVIAL_PATTERNS = _re.compile(
    r"^\s*(?:"
    r"(?:hey|hi|hello|sup|yo|hola|kamusta)[!.,?\s]*|"
    r"(?:what(?:'s| is) (?:up|good)|how(?:'s| are) (?:you|it going)|how are you)[!.,?\s]*|"
    r"(?:ok(?:ay)?|sure|got it|thanks?|thank you|np|no prob(?:lem)?|cool|nice|great|awesome|lol|haha|lmao)[!.,?\s]*|"
    r"(?:yes|no|yep|nope|yup|nah)[!.,?\s]*|"
    r"(?:bye|goodbye|see you|cya|talk later)[!.,?\s]*"
    r")$",
    _re.I,
)


def _hash(text: str) -> str:
    return hashlib.md5(text.lower().strip().encode()).hexdigest()


def _already_known(fact: str) -> bool:
    """Check if semantically similar fact already exists."""
    if _hash(fact) in _seen_hashes:
        return True
    existing = [
        e.get("entry", "") if isinstance(e, dict) else str(e) for e in list_training()
    ]
    fact_words = set(fact.lower().split())
    for entry in existing:
        if not entry:
            continue
        entry_words = set(entry.lower().split())
        overlap = len(fact_words & entry_words) / max(len(fact_words), 1)
        if overlap > 0.65:  # slightly tighter threshold
            _seen_hashes.add(_hash(fact))  # cache it so future checks are instant
            return True
    return False


def _prune_if_needed():
    """Keep auto-learned entries under MAX_AUTO_ENTRIES."""
    from training_memory import add_training as _add
    from training_memory import clear_training, list_training

    entries = list_training()
    auto = [
        e
        for e in entries
        if isinstance(e, dict) and e.get("category") == "auto-learned"
    ]
    if len(auto) > MAX_AUTO_ENTRIES:
        # Keep most recent half
        keep = auto[-(MAX_AUTO_ENTRIES // 2) :]
        manual = [
            e
            for e in entries
            if not (isinstance(e, dict) and e.get("category") == "auto-learned")
        ]
        clear_training()
        for e in manual + keep:
            _add(e.get("entry", str(e)), category=e.get("category", "training"))


def extract_and_learn(user_message: str, assistant_response: str) -> None:
    """
    Called after every /ask exchange.
    Runs in background — extracts facts about the user and saves them permanently.
    For short messages, uses fast regex patterns. For longer messages, uses LLM.
    """
    # Hard skip: too short or obviously trivial/conversational
    if len(user_message) < MIN_MESSAGE_LEN:
        return
    if _TRIVIAL_PATTERNS.match(user_message.strip()):
        return
    # Also skip if message is purely a question with no self-disclosure signal
    stripped = user_message.strip()
    is_pure_question = stripped.endswith("?") and not any(
        kw in stripped.lower()
        for kw in (
            "i ",
            "i'm",
            "i am",
            "my ",
            "me ",
            "i've",
            "i work",
            "i prefer",
            "i use",
            "i like",
            "i hate",
        )
    )
    if is_pure_question and len(stripped) < 120:
        return

    # Fast path: regex extraction for short-medium messages
    quick_facts = _quick_extract(user_message)
    correction_facts = _correction_extract(user_message)
    all_quick = quick_facts + correction_facts
    if all_quick:
        for fact in all_quick[:4]:
            if not _already_known(fact):
                add_training(fact, category="auto-learned")
                _seen_hashes.add(_hash(fact))
                try:
                    from rag_memory import upsert_memory

                    upsert_memory(fact, category="auto-learned")
                except Exception:
                    pass
        _prune_if_needed()

    # Run LLM extraction when message has any meaningful content (not just self-disclosure)
    # and cooldown has expired to prevent Ollama queue contention
    import time as _time

    global _last_llm_extract
    content_signals = any(
        kw in user_message.lower()
        for kw in (
            "i ",
            "i'm",
            "i am",
            "my ",
            "me ",
            "i've",
            "i work",
            "i prefer",
            "i use",
            "i like",
            "i hate",
            "i need",
            "i want",
            "i always",
            "i never",
            "actually",
            "correction",
            "wrong",
            "prefer",
            "usually",
            "normally",
            "working on",
            "building",
            "trying to",
            "help me",
            "can you",
            "how do",
            "salesforce",
            "apex",
            "lwc",
            "soql",
            "flow",
            "trigger",  # platform signals
        )
    )
    if len(user_message) < 60 or not content_signals:
        return
    if (_time.time() - _last_llm_extract) < _LLM_EXTRACT_COOLDOWN:
        return  # cooldown active — regex path handled it, skip LLM

    def _run():
        prompt = f"""Analyze this conversation exchange and extract facts worth remembering long-term.

User said: "{user_message}"
Assistant replied: "{assistant_response[:300]}"

Extract facts in these categories:
- Who the user is (name, role, location, background)
- What they are currently working on or building
- Their explicit preferences, habits, or working style
- Technologies, tools, or platforms they use
- Goals or problems they are trying to solve
- Corrections or things they want ATLAS to remember

Do NOT extract:
- Generic questions with no personal context
- Things ATLAS said (only extract about the USER)
- Vague observations like "user asked about X"

Return a JSON array of max 4 concise strings, or [] if nothing qualifies.
Example: ["User is a Salesforce developer", "User is building an ERP integration", "User prefers REST over SOAP"]
Return ONLY valid JSON. Nothing else."""

        try:
            result = ollama.chat(
                model="atlas",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 150},
            )
            raw = result["message"]["content"].strip()

            # Find JSON array in response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start < 0 or end <= start:
                return

            facts = json.loads(raw[start:end])
            if not isinstance(facts, list):
                return

            saved = 0
            for fact in facts[:3]:
                if not isinstance(fact, str) or len(fact) < 15:
                    continue
                if _already_known(fact):
                    continue
                add_training(fact, category="auto-learned")
                _seen_hashes.add(_hash(fact))
                saved += 1
                # Sync to RAG vector store immediately
                try:
                    from rag_memory import upsert_memory

                    upsert_memory(fact, category="auto-learned")
                except Exception:
                    pass

            if saved > 0:
                _prune_if_needed()

        except Exception:
            pass  # Silent — learning is best-effort, never breaks main flow

    _last_llm_extract = __import__("time").time()
    t = threading.Thread(target=_run, daemon=True)
    t.start()
