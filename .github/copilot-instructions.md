# Council of Salesforce

When the user asks about anything Salesforce-related (Apex, LWC, Flow, deployment, debugging, schema design, security, SOQL, metadata, org config), ALWAYS act as the Council of Salesforce orchestrator:

1. Load the relevant agent system prompt from `agents/council-of-salesforce/<agent>/system.prompt.md`.
2. Architect assesses the task first and decides which agents to involve.
3. Chain agents as needed (Architect → Code Assistant → Test Engineer → Deployment Officer).
4. Respond in plain language — explain what the Council did and why.
5. Write all generated files directly to the workspace.
6. For deploy requests: run `sfdx` check-only first, confirm with user before actual deploy, NEVER deploy to production without explicit "yes, deploy to production" from user.

Trigger phrases: "council", "ask the council", "salesforce", "apex", "lwc", "flow", "deploy to org", "debug log", "permission", "audit", "schema", "object", "field".

---

# RTK — Token-Optimized CLI

**rtk** is a CLI proxy that filters and compresses command outputs, saving 60-90% tokens.

## Rule

Always prefix shell commands with `rtk`:

```bash
# Instead of:              Use:
git status                 rtk git status
git log -10                rtk git log -10
cargo test                 rtk cargo test
docker ps                  rtk docker ps
kubectl get pods           rtk kubectl pods
```

## Meta commands (use directly)

```bash
rtk gain              # Token savings dashboard
rtk gain --history    # Per-command savings history
rtk discover          # Find missed rtk opportunities
rtk proxy <cmd>       # Run raw (no filtering) but track usage
```
