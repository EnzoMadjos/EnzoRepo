# RTK Integration for Council of AppDev

All agents in this council are required to use the RTK CLI for all shell commands. This ensures:
- Maximum token savings (60-90% reduction)
- Avoidance of token limits during development
- Consistent, efficient command output handling

## Usage
- Prefix all shell commands with `rtk` (e.g., `rtk git status`, `rtk pip install ...`)
- For meta commands, use as documented in the RTK section

## Enforcement
- Each agent’s system prompt includes this requirement
- Orchestration logic should validate RTK usage for all shell commands

## Reference
See `.github/copilot-instructions.md` for full RTK CLI documentation and council workflow.
