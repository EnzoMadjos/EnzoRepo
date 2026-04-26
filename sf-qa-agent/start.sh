#!/usr/bin/env bash
# start.sh — start the SF QA Agent (Ollama + uvicorn)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load port from .env if present
PORT=8200
if [ -f .env ]; then
  _PORT=$(grep -E '^APP_PORT=' .env | cut -d= -f2 | tr -d '[:space:]')
  [ -n "$_PORT" ] && PORT="$_PORT"
fi

echo "========================================"
echo "  SF QA Test Agent"
echo "========================================"

# 1. Check .env exists
if [ ! -f .env ]; then
  echo ""
  echo "  ERROR: .env file not found."
  echo "  Copy .env.example to .env and fill in your credentials."
  echo ""
  exit 1
fi

# 2. Start Ollama if not already running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
  echo "  Starting Ollama..."
  ollama serve > /tmp/ollama.log 2>&1 &
  sleep 2
else
  echo "  Ollama already running."
fi

# 3. Start the FastAPI app
echo "  Starting server on http://localhost:${PORT}"
echo ""
uvicorn sf_app:app --host 0.0.0.0 --port "$PORT" --reload
