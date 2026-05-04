# New Machine Setup (Linux)

Clone and run one command — setup.sh handles everything:

```bash
git clone https://github.com/EnzoMadjos/EnzoRepo.git ai-lab
cd ai-lab
bash setup.sh
```

What `setup.sh` does automatically:
1. Installs **graphifyy** (knowledge graph CLI) via pip
2. Installs **uv/uvx** (Python tool runner, needed for Salesforce + Brain MCPs)
3. Installs **context-mode** globally via npm (context-window MCP server)
4. Pulls all **MCP Docker images**: `mcp/memory`, `mcp/sequentialthinking`, `mcp/context7`, `mcp/playwright`, `mcp/fetch`, `mcp/git`, `ghcr.io/github/github-mcp-server`
5. Generates **`.vscode/mcp.json`** from `.vscode/mcp.json.template` with correct paths for this machine
6. Ensures **`.vscode/settings.json`** has `task.allowAutomaticTasks: on` (so MCP Docker tasks auto-start on folder open)
7. Installs **Jarvis Copilot instructions** to all VS Code prompts folders found on the machine

After setup:
- Open the `ai-lab` folder in VS Code
- The two auto-tasks fire on folder open: Docker image pre-warm + Context7 SSE server start
- Enter your GitHub PAT when the GitHub MCP server prompts (first use only — VS Code remembers it)
- Salesforce MCP prompts for instance URL / client ID / secret on first use

Prerequisites (must be installed before running setup.sh):
- Git, Python 3.10+, Node.js + npm, Docker

---

# Deployment workflow (skeleton)

Deployment workflow (skeleton)

This repository includes a deployment workflow skeleton at `.github/workflows/deploy.yml`.

Current selection: SSH-based local deployment (Cloud Run is optional and documented below).

What it does:
- Builds a Docker image and pushes it to GitHub Container Registry (GHCR).
- Deploys to a self-hosted VM over SSH by pulling the GHCR image and restarting the container.

Required repository secrets (SSH deploy):
- `SSH_HOST` — Hostname or IP of the remote server.
- `SSH_USER` — SSH user to connect as (must have permission to run Docker).
- `SSH_PRIVATE_KEY` — Private key (PEM) for SSH access (add as Actions secret).
- `SSH_PORT` — Optional SSH port (defaults to 22 if not set).
- `GHCR_TOKEN` — Used on the remote host to authenticate with GHCR so `docker pull` can succeed (if GHCR image is private).

Next steps to enable SSH deploy now:
1. Add the required SSH secrets in the repository settings → Secrets → Actions.
2. Ensure the remote host has Docker installed and the SSH user can run Docker commands.
3. Trigger the workflow (manually via Actions → Deploy or by pushing to `main`) after secrets are in place.

Notes:
- `Steve Rogers` is recorded as Deployment Officer and will watch the pipeline and notify of progress and issues.
- I will not push secrets; please add them in repository secrets before triggering the deploy job.

SSH Deployment (how-to)

If you want to deploy to a self-hosted VM over SSH, the workflow now includes an SSH deploy step that:

- Logs in to GHCR on the remote host using the `GHCR_TOKEN` secret.
- Pulls `ghcr.io/${{ github.repository_owner }}/enzo-repo:latest` on the remote host.
- Stops and removes an existing container named `enzo-app` and runs the new image.

Required secrets for SSH deploy (add these in repository settings > Secrets):
- `SSH_HOST` — Hostname or IP of the remote server.
- `SSH_USER` — SSH user to connect as (must have permission to run Docker).
- `SSH_PRIVATE_KEY` — Private key (PEM) for SSH access.
- `SSH_PORT` — Optional SSH port (defaults to 22 if not set).
- `GHCR_TOKEN` — Used on the remote host to authenticate with GHCR so `docker pull` can succeed.

Remote host prerequisites:
- Docker must be installed on the remote server and the SSH user should be able to run Docker commands (either in the `docker` group or via passwordless `sudo`).
- If you prefer `docker compose`, update the deploy step in `.github/workflows/deploy.yml` to run `docker compose pull` and `docker compose up -d` instead of `docker run`.

Security notes:
- Never store private keys in the repository. Use GitHub Secrets.
- Consider restricting the deploy key to only the deployment host and rotating it regularly.

Cloud Run Deployment (recommended)

I replaced the SSH deploy with an optional Cloud Run deployment job in `.github/workflows/deploy.yml`.

What it does:
- Authenticates to GCP using the `GCP_SERVICE_ACCOUNT_KEY` secret.
- Configures Docker auth for pushing to Google Container Registry (GCR).
- Tags the previously-built image and pushes it to `gcr.io/${{ secrets.GCP_PROJECT }}/enzo-repo:latest`.
- Deploys that image to the Cloud Run service specified by `CLOUD_RUN_SERVICE`.

Required repository secrets for Cloud Run deploy:
- `GCP_SERVICE_ACCOUNT_KEY` — JSON key for a service account with roles: `roles/run.admin`, `roles/iam.serviceAccountUser`, and `roles/storage.admin` (or equivalent permissions to push images to GCR/Artifact Registry and deploy Cloud Run).
- `GCP_PROJECT` — GCP project id.
- `GCP_REGION` — Cloud Run region (e.g., `us-central1`).
- `CLOUD_RUN_SERVICE` — Cloud Run service name to deploy to.

GCP setup checklist:
1. Enable APIs: Cloud Run API, IAM API, Container Registry or Artifact Registry API.
2. Create a service account and grant it the roles above.
3. Create and download a JSON key and add it to GitHub Secrets as `GCP_SERVICE_ACCOUNT_KEY`.

Notes:
- The Cloud Run job is guarded by a condition so it only runs when `GCP_SERVICE_ACCOUNT_KEY` is set. Add the secrets before triggering the workflow.
- If you prefer using Artifact Registry instead of GCR, modify the workflow to push to your Artifact Registry repo and update the Cloud Run `image` accordingly.


