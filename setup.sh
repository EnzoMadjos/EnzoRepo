#!/usr/bin/env bash
# Jarvis Setup — installs Copilot instructions to VS Code user prompts folder
# Run once on any Linux/Mac machine after cloning the repo.
# Usage: bash setup.sh

set -e

# Install graphifyy (team knowledge graph tool) if not already installed
if ! command -v graphify &>/dev/null; then
  echo "Installing graphifyy..."
  pip install "graphifyy[sql,office,mcp]" -q && echo "✔ graphifyy installed"
fi

RAW_URL="https://raw.githubusercontent.com/EnzoMadjos/EnzoRepo/main/.github/jarvis.instructions.md"
DEST_DIRS=(
  "$HOME/.config/Code/User/prompts"           # VS Code local (Linux)
  "$HOME/.config/Code - Insiders/User/prompts" # VS Code Insiders (Linux)
  "$HOME/Library/Application Support/Code/User/prompts"  # VS Code local (Mac)
)

# Also install directly from local file if we're inside the repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_FILE="$SCRIPT_DIR/.github/jarvis.instructions.md"

installed=0
for dir in "${DEST_DIRS[@]}"; do
  if [ -d "$dir" ] || mkdir -p "$dir" 2>/dev/null; then
    if [ -f "$LOCAL_FILE" ]; then
      cp "$LOCAL_FILE" "$dir/jarvis.instructions.md"
    else
      curl -fsSL "$RAW_URL" -o "$dir/jarvis.instructions.md"
    fi
    echo "✔ Installed to $dir"
    installed=1
  fi
done

# VS Code Server (remote SSH) — install here too
VSCODE_SERVER_PROMPTS="$HOME/.vscode-server/data/User/prompts"
if [ -d "$VSCODE_SERVER_PROMPTS" ]; then
  if [ -f "$LOCAL_FILE" ]; then
    cp "$LOCAL_FILE" "$VSCODE_SERVER_PROMPTS/jarvis.instructions.md"
  else
    curl -fsSL "$RAW_URL" -o "$VSCODE_SERVER_PROMPTS/jarvis.instructions.md"
  fi
  echo "✔ Installed to $VSCODE_SERVER_PROMPTS"
  installed=1
fi

if [ $installed -eq 0 ]; then
  echo "⚠ No VS Code User/prompts folder found. Install VS Code first, then re-run."
  exit 1
fi

echo ""
echo "Done. Restart VS Code — Jarvis + Avengers team are now active in every workspace."
