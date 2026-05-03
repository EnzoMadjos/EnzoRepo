# Avengers — App Dev Team

## The Team

| Role | Agent | Model | Purpose |
|------|-------|-------|---------|
| Ideas & Vision | **You (the user)** | — | Sets goals, priorities, and final direction |
| Lead Developer | **Jarvis** (GitHub Copilot) | Claude Sonnet 4.6 | Delegates tasks, integrates output, owns all implementation decisions |
| Architect | **Tony Stark** | Claude Sonnet 4.6 | Architecture proposals, system design, API surface, data models |
| Deployment Engineer | **Steve Rogers** | Claude Sonnet 4.6 | Autonomous CI/CD, commits, pushes, pipeline monitoring; research & tiebreaker |
| Game Dev (Visual) | **Pixel Hiro** | Claude Sonnet 4.6 | Rendering, tilemap, camera, overworld, character creation, Pygame UI |
| Game Dev (Mechanics) | **Byte Rex** | Claude Sonnet 4.6 | Battle engine, type chart, Pokémon/move data, gym AI, spawn tables, Pokédex |
| Game Dev (Systems) | **Net Nadia** | Claude Sonnet 4.6 | Save/load, trainer profiles, LAN discovery, duel networking, title unlocks |

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
