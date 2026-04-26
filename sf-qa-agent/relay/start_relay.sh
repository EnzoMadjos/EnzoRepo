#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# start_relay.sh  —  Start the SF QA support relay server
#
# Usage:
#   bash relay/start_relay.sh
#
# What it does:
#   1. Starts relay_server.py on port 9100 (or RELAY_PORT in .env)
#   2. Prints instructions for exposing it via ngrok
#   3. Received logs land in relay/received_logs/
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Check .env ────────────────────────────────────────────────────────────────

if [[ ! -f ".env" ]]; then
    echo ""
    echo "  No relay/.env found — creating from template…"
    cp .env.example .env
    echo ""
    echo "  ⚠  ACTION REQUIRED:"
    echo "     1. Edit relay/.env and set RELAY_TOKEN to a strong random string:"
    echo "        python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    echo "     2. Copy that token to Vanessa's app .env: RELAY_TOKEN=<same value>"
    echo "     3. Run this script again."
    echo ""
    exit 1
fi

# Load port from .env
RELAY_PORT="$(grep -E '^RELAY_PORT=' .env 2>/dev/null | cut -d= -f2 || echo 9100)"
RELAY_PORT="${RELAY_PORT:-9100}"

# ── Dependency check ──────────────────────────────────────────────────────────

VENV_PYTHON=""
for candidate in \
    "../.venv/bin/python" \
    "../../.venv/bin/python" \
    "$(which python3 2>/dev/null)" \
    "$(which python 2>/dev/null)"; do
    if [[ -x "$candidate" ]]; then
        VENV_PYTHON="$candidate"
        break
    fi
done

if [[ -z "$VENV_PYTHON" ]]; then
    echo "ERROR: No Python found. Activate your venv or install Python."
    exit 1
fi

# Install relay dependencies if needed
"$VENV_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "  Installing relay dependencies…"
    "$VENV_PYTHON" -m pip install fastapi uvicorn python-dotenv --quiet
}

# ── Banner ────────────────────────────────────────────────────────────────────

echo ""
echo "======================================================"
echo "  SF QA Relay Server — Starting"
echo "======================================================"
echo ""
echo "  After the server starts, open a NEW terminal and run:"
echo "    ngrok http ${RELAY_PORT}"
echo ""
echo "  Then copy the  https://xxxx.ngrok-free.app  URL"
echo "  into Vanessa's app .env:"
echo "    RELAY_URL=https://xxxx.ngrok-free.app"
echo "    RELAY_TOKEN=<same token as relay/.env>"
echo ""
echo "  Received logs will appear here in real-time."
echo "  Press Ctrl+C to stop the server."
echo "======================================================"
echo ""

# ── Start ─────────────────────────────────────────────────────────────────────

exec "$VENV_PYTHON" relay_server.py
