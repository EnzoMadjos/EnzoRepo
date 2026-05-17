#!/usr/bin/env bash
# ── Live Seller App Launcher ─────────────────────────────────────
# macOS / Linux. Run from the project root.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Activate venv if it exists ───────────────────────────────────
VENV_PATH="$SCRIPT_DIR/.venv"
if [ -d "$VENV_PATH" ]; then
  source "$VENV_PATH/bin/activate"
  echo "[Launcher] venv activated: $VENV_PATH"
else
  # Fall back to workspace venv
  WS_VENV="/home/enzo/ai-lab/.venv"
  if [ -d "$WS_VENV" ]; then
    source "$WS_VENV/bin/activate"
    echo "[Launcher] Using workspace venv: $WS_VENV"
  else
    echo "[Launcher] WARNING: No venv found — using system Python"
  fi
fi

# ── Check Ollama ─────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
  if ! ollama list 2>/dev/null | grep -q phi4-mini; then
    echo "[Launcher] Pulling phi4-mini..."
    ollama pull phi4-mini
  else
    echo "[Launcher] phi4-mini ready ✅"
  fi
else
  echo "[Launcher] WARNING: Ollama not found — cloud fallback will be used"
fi

# ── Create required directories ──────────────────────────────────
mkdir -p secure static/css static/js templates

# ── Start ─────────────────────────────────────────────────────────
PORT="${LIVE_SELLER_PORT:-8500}"
HOST="${LIVE_SELLER_HOST:-0.0.0.0}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🛍️  Live Seller App"
echo "  http://localhost:$PORT"
echo "  iPhone PWA: http://$(hostname -I | awk '{print $1}'):$PORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

uvicorn app:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload
