# Avengers — App Dev Team

## The Team

| Role | Agent | Model | Purpose |
|------|-------|-------|---------|
| Ideas & Vision | **You (the user)** | — | Sets goals, priorities, and final approval |
| Builder & Design | **Jarvis** (GitHub Copilot) | Claude | Designs, builds, and executes everything |
| Architect | **Tony Stark** | Claude Sonnet 4.6 | Architecture proposals, system design, API surface, data models |
| Research & Tiebreaker | **Steve Rogers** | Claude Sonnet 4.6 | Deep research, feasibility studies, final call when Tony and Jarvis disagree |

## How We Work

1. **You bring the idea** — brief description, goal, constraints.
2. **Jarvis + Tony** exchange architecture proposals and challenge each other.
3. If they disagree, **Steve Rogers** conducts a feasibility study and delivers a verdict.
4. **Jarvis presents the final plan** to you before building anything.
5. You approve (or redirect). **Jarvis builds and tests**.
6. Done — or next sprint begins.

## Folder Structure

```
agents/avengers/
  tony-stark/
    system.prompt.md   # Tony Stark's full agent instructions
    meta.json          # Model: gpt-4.1
    user.template.md   # How to invoke Tony
  steve-rogers/
    system.prompt.md   # Steve Rogers's full agent instructions
    meta.json          # Model: gpt-4.1
    user.template.md   # How to invoke Steve
  README.md            # This file
```

## Trigger Phrases

- "Ask Tony" / "Tony, design this" → invokes Tony Stark architect agent
- "Ask Steve" / "Steve, research this" / "Steve, break the tie" → invokes Steve Rogers agent
- "Avengers, assemble" → Jarvis runs Tony first, then Steve if needed, then presents plan to user

## Ground Rules

- Tony and Jarvis debate architecture. Steve breaks ties.
- Nothing gets built until the user approves the plan.
- Jarvis is the sole executor. Tony and Steve are advisors only.
- All three use `rtk` prefix for shell commands.
