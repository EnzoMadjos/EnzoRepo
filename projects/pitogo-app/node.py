from __future__ import annotations

import json
import uuid
from pathlib import Path
import config


NODE_FILE = config.SECURE_DIR / "node_id.json"


def get_node_id() -> str:
    if NODE_FILE.exists():
        try:
            data = json.loads(NODE_FILE.read_text(encoding="utf-8"))
            if data.get("node_id"):
                return data["node_id"]
        except Exception:
            pass
    nid = str(uuid.uuid4())
    NODE_FILE.write_text(json.dumps({"node_id": nid}), encoding="utf-8")
    return nid


def get_node_short(length: int = 6) -> str:
    return get_node_id().replace("-", "")[:length].upper()
