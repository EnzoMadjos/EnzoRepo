Services — Controller

`services/controller.py` is a minimal simulation of the Council orchestration.

Usage example:

```bash
python services/controller.py --agent architect --model gpt-5-mini --prompt "Add Orders object linked to Account"
```

Notes:
- This script is a local simulation and does not call external LLM APIs.
- It demonstrates routing, chaining (architect -> code-assistant -> test-engineer), and saves outputs to:
  `agents/council-of-salesforce/workspace_outputs/`.
