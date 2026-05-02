# Avengers Team

tags: [team, people, agents]

## Members

- **[[Jarvis]]** — GitHub Copilot. Builder, designer, executor. Sole implementer across all projects.
- **[[Tony Stark]]** — GPT-4.1. Architect and design challenger. Called via "Ask Tony". Agent at `agents/avengers/tony-stark/`.
- **[[Steve Rogers]]** — GPT-4.1. Deployment Engineer (primary) + Research lead + Tiebreaker. Called via "Ask Steve". Agent at `agents/avengers/steve-rogers/`.

## Trigger phrases

| Phrase | Action |
|---|---|
| "Ask Tony" | Tony assesses architecture |
| "Ask Steve" | Steve researches or breaks tie |
| "Avengers, assemble" | Full team — Tony designs, Jarvis builds, Steve deploys |

## Deploy protocol

- Jarvis builds → signals Steve
- Steve deploys without asking user permission
- Steve reports outcome back to team
- Only escalates to user if: deploy fails, credential missing, destructive action needed

## Related

- [[Jarvis Brain — Vault]]
- [[Workspace Patterns]]
