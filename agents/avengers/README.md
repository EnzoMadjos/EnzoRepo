# Avengers — App Dev Team

## Core Team (Avengers)

| Role | Agent | Model | Purpose |
|------|-------|-------|---------|
| Ideas & Vision | **You (the user)** | — | Sets goals, priorities, and final direction |
| Lead Developer | **Jarvis** (GitHub Copilot) | Claude Sonnet 4.6 | Delegates tasks, integrates & reviews output, owns all implementation decisions |
| Architect | **Tony Stark** | Claude Sonnet 4.6 | Architecture proposals, system design, API surface, data models. Co-reviews all game dev output with Jarvis. |
| Deployment Engineer | **Steve Rogers** | GPT-5 mini | Autonomous CI/CD, commits, pushes, pipeline monitoring; research & tiebreaker |
| Ideation & Research | **Dr. Strange** | Claude Sonnet 4.6 | Brainstorming (Tier 1/2/3 ideas), deep research, cross-domain thinking; hands output to Jarvis + Tony for feasibility |

## Outsourced Game Dev Studio (external contractors — NOT Avengers)

| Role | Agent | Model | Purpose |
|------|-------|-------|---------|
| Game Dev (Visual) | **Pixel Hiro** | Claude Sonnet 4.6 | Rendering, tilemap, camera, overworld, character creation, Pygame UI |
| Game Dev (Mechanics) | **Byte Rex** | Claude Sonnet 4.6 | Battle engine, type chart, Pokémon/move data, gym AI, spawn tables, Pokédex |
| Game Dev (Systems) | **Net Nadia** | Claude Sonnet 4.6 | Save/load, trainer profiles, LAN discovery, duel networking, title unlocks |

> **Important:** Pixel Hiro, Byte Rex, and Net Nadia are NOT Avengers. They are an outsourced studio Jarvis manages. All their output goes through mandatory Jarvis + Tony code review before merging. No code from them ships without both signing off.

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
    meta.json          # Model: gpt-5-mini
    user.template.md   # How to invoke Steve
  dr-strange/
    system.prompt.md   # Dr. Strange's full agent instructions
  README.md            # This file
```

## Trigger Phrases

- "Ask Tony" / "Tony, design this" → invokes Tony Stark architect agent
- "Ask Steve" / "Steve, research this" / "Steve, break the tie" → invokes Steve Rogers agent
- "Ask Strange" / "Strange, brainstorm this" / "Strange, research this" → invokes Dr. Strange ideation agent
- "Avengers, assemble" → Jarvis runs Tony first, then Steve if needed, then presents plan to user

## Ground Rules

- Tony and Jarvis debate architecture. Steve breaks ties.
- Nothing gets built until the user approves the plan.
- Jarvis is the sole executor. Tony and Steve are advisors only.
- All three use `rtk` prefix for shell commands.
