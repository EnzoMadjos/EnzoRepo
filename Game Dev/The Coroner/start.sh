#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="/home/enzo/ai-lab/.venv"
source "$VENV/bin/activate"

# Ensure phi4-mini is pulled
echo "[Coroner] Checking Ollama model..."
ollama pull phi4-mini 2>/dev/null || echo "[Coroner] Warning: could not pull phi4-mini. Continuing..."

echo "[Coroner] Starting on http://0.0.0.0:8400"
exec uvicorn app:app --host 0.0.0.0 --port 8400 --reload
