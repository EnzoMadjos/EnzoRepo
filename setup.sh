#!/usr/bin/env bash
# Jarvis Full Setup — run once on any new Linux/Mac machine after cloning the repo.
# Sets up: graphifyy, uv/uvx, context-mode, Docker MCP images, mcp.json, Copilot instructions.
# Usage: bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FILE="$SCRIPT_DIR/.github/jarvis.instructions.md"

echo "=== Jarvis Setup ==="
echo "Workspace: $SCRIPT_DIR"
echo ""

# ── 1. graphifyy ──────────────────────────────────────────────────────────────
if ! command -v graphify &>/dev/null; then
  echo "Installing graphifyy..."
  pip install "graphifyy[sql,office,mcp]" -q && echo "✔ graphifyy installed"
else
  echo "✔ graphifyy already installed"
fi

# ── 2. uv / uvx ───────────────────────────────────────────────────────────────
if ! command -v uvx &>/dev/null; then
  echo "Installing uv (provides uvx)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  echo "✔ uv/uvx installed"
else
  echo "✔ uvx already installed: $(command -v uvx)"
fi

# ── 3. context-mode (npm global) ──────────────────────────────────────────────
if ! command -v context-mode &>/dev/null; then
  if command -v npm &>/dev/null; then
    echo "Installing context-mode..."
    npm install -g context-mode -q && echo "✔ context-mode installed"
  else
    echo "⚠ npm not found — skipping context-mode. Install Node.js first, then run: npm install -g context-mode"
  fi
else
  echo "✔ context-mode already installed: $(command -v context-mode)"
fi

# ── 4. Docker MCP images ──────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
  echo ""
  echo "Pulling MCP Docker images (this may take a few minutes on first run)..."
  MCP_IMAGES=(
    "mcp/memory"
    "mcp/sequentialthinking"
    "mcp/context7"
    "mcp/playwright"
    "mcp/fetch"
    "mcp/git"
    "ghcr.io/github/github-mcp-server"
  )
  for img in "${MCP_IMAGES[@]}"; do
    echo "  → $img"
    docker pull "$img" -q && echo "    ✔ ready"
  done
  echo "✔ All MCP Docker images ready"
else
  echo "⚠ Docker not found — skipping image pulls. Install Docker, then re-run this script."
fi

# ── 5. Generate .vscode/mcp.json from template ────────────────────────────────
TEMPLATE="$SCRIPT_DIR/.vscode/mcp.json.template"
MCP_OUT="$SCRIPT_DIR/.vscode/mcp.json"
if [ -f "$TEMPLATE" ]; then
  UVX_PATH=$(command -v uvx 2>/dev/null || echo "$HOME/.local/bin/uvx")
  CONTEXT_MODE_PATH=$(command -v context-mode 2>/dev/null || echo "$HOME/.npm-global/bin/context-mode")
  sed -e "s|{{WORKSPACE}}|$SCRIPT_DIR|g" \
      -e "s|{{UVX}}|$UVX_PATH|g" \
      -e "s|{{CONTEXT_MODE}}|$CONTEXT_MODE_PATH|g" \
      "$TEMPLATE" > "$MCP_OUT"
  echo "✔ Generated .vscode/mcp.json"
else
  echo "⚠ .vscode/mcp.json.template not found — skipping mcp.json generation"
fi

# ── 6. .vscode/settings.json — enable auto-tasks ─────────────────────────────
SETTINGS_FILE="$SCRIPT_DIR/.vscode/settings.json"
if [ ! -f "$SETTINGS_FILE" ]; then
  echo '{ "task.allowAutomaticTasks": "on" }' > "$SETTINGS_FILE"
  echo "✔ Created .vscode/settings.json (auto-tasks enabled)"
fi

# ── 7. Install Jarvis Copilot instructions ────────────────────────────────────
echo ""
RAW_URL="https://raw.githubusercontent.com/EnzoMadjos/EnzoRepo/main/.github/jarvis.instructions.md"
DEST_DIRS=(
  "$HOME/.config/Code/User/prompts"            # VS Code local (Linux)
  "$HOME/.config/Code - Insiders/User/prompts" # VS Code Insiders (Linux)
  "$HOME/Library/Application Support/Code/User/prompts"  # VS Code local (Mac)
)

installed=0
for dir in "${DEST_DIRS[@]}"; do
  if [ -d "$dir" ] || mkdir -p "$dir" 2>/dev/null; then
    if [ -f "$LOCAL_FILE" ]; then
      cp "$LOCAL_FILE" "$dir/jarvis.instructions.md"
    else
      curl -fsSL "$RAW_URL" -o "$dir/jarvis.instructions.md"
    fi
    echo "✔ Copilot instructions → $dir"
    installed=1
  fi
done

# VS Code Server (remote SSH)
VSCODE_SERVER_PROMPTS="$HOME/.vscode-server/data/User/prompts"
if [ -d "$VSCODE_SERVER_PROMPTS" ]; then
  if [ -f "$LOCAL_FILE" ]; then
    cp "$LOCAL_FILE" "$VSCODE_SERVER_PROMPTS/jarvis.instructions.md"
  else
    curl -fsSL "$RAW_URL" -o "$VSCODE_SERVER_PROMPTS/jarvis.instructions.md"
  fi
  echo "✔ Copilot instructions → $VSCODE_SERVER_PROMPTS"
  installed=1
fi

if [ $installed -eq 0 ]; then
  echo "⚠ No VS Code User/prompts folder found. Install VS Code first, then re-run."
fi

echo ""
echo "All done, boss. Restart VS Code — Jarvis + Avengers team are active in every workspace."
echo "MCP servers auto-start when you open the ai-lab folder."
