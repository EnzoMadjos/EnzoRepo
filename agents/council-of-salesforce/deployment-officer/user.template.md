Repo layout: {{path}}
Target env: {{sandbox/stage/prod}}
Steps: validate -> test -> check-only deploy -> (manual approve) -> deploy
Deliverables: `.github/workflows/*.yml`, `scripts/deploy.sh`, `rollback_plan.md`

Example: "Target: sandbox. Steps: run static checks, run Apex tests, run sfdx check-only deploy. Deliverable: workflow YAML."
