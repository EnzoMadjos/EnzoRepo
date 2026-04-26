#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# go_online.sh  —  Bring the SF QA support relay online in ONE command.
#
# What it does:
#   1. Starts relay/relay_server.py  (receives logs, serves patch.zip)
#   2. Starts ngrok to expose it publicly
#   3. Waits for ngrok to hand out a URL
#   4. Prints the URL you need to share (or auto-updates relay/.env if you
#      use a paid ngrok static domain)
#   5. Watches for received logs and prints them live
#
# Requirements:
#   - relay/.env exists with RELAY_TOKEN set
#   - ngrok is installed:  https://ngrok.com/download
#     Free tier works fine. Optional: claim a free static domain at
#     https://dashboard.ngrok.com/domains  and set NGROK_DOMAIN in relay/.env
#
# Usage:
#   bash go_online.sh            # start everything
#   bash go_online.sh --stop     # kill relay + ngrok
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELAY_DIR="$SCRIPT_DIR/relay"
ENV_FILE="$RELAY_DIR/.env"
PID_FILE="$RELAY_DIR/.relay.pid"

# ── Stop mode ────────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--stop" ]]; then
    echo ""
    if [[ -f "$PID_FILE" ]]; then
        while IFS= read -r pid; do
            kill "$pid" 2>/dev/null && echo "  Stopped PID $pid" || true
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    pkill -f "relay_server.py" 2>/dev/null || true
    pkill -f "ngrok http"      2>/dev/null || true
    echo "  Relay server stopped."
    echo ""
    exit 0
fi

# ── Guards ────────────────────────────────────────────────────────────────────

if [[ ! -f "$ENV_FILE" ]]; then
    echo ""
    echo "  ✗ relay/.env not found."
    echo "    Run this first to create it:"
    echo "      cp relay/.env.example relay/.env"
    echo "    Then set RELAY_TOKEN to a strong random string:"
    echo "      python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    echo ""
    exit 1
fi

# Load relay config
source <(grep -E '^[A-Z_]+=.*' "$ENV_FILE" | grep -v '^#')
RELAY_PORT="${RELAY_PORT:-9100}"
RELAY_TOKEN="${RELAY_TOKEN:-}"
NGROK_DOMAIN="${NGROK_DOMAIN:-}"

if [[ -z "$RELAY_TOKEN" ]]; then
    echo ""
    echo "  ✗ RELAY_TOKEN is not set in relay/.env"
    echo "    Generate one:  python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    echo "    Then paste it into relay/.env as:  RELAY_TOKEN=<value>"
    echo ""
    exit 1
fi

# Check ngrok
if ! command -v ngrok &>/dev/null; then
    echo ""
    echo "  ✗ ngrok not found. Install it:"
    echo "    https://ngrok.com/download"
    echo "    (Free account, then run: ngrok config add-authtoken <your-token>)"
    echo ""
    exit 1
fi

# ── Find Python ───────────────────────────────────────────────────────────────

VENV_PYTHON=""
for candidate in \
    "$SCRIPT_DIR/.venv/bin/python" \
    "$SCRIPT_DIR/../.venv/bin/python" \
    "$(which python3 2>/dev/null)" \
    "$(which python  2>/dev/null)"; do
    if [[ -x "$candidate" ]]; then
        VENV_PYTHON="$candidate"
        break
    fi
done

if [[ -z "$VENV_PYTHON" ]]; then
    echo "  ✗ Python not found. Activate your venv first."
    exit 1
fi

# Install relay deps if needed
"$VENV_PYTHON" -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "  Installing relay dependencies…"
    "$VENV_PYTHON" -m pip install fastapi uvicorn python-dotenv --quiet
}

# ── Start relay server ────────────────────────────────────────────────────────

echo ""
echo "=========================================================="
echo "  SF QA Support Relay — Coming Online"
echo "=========================================================="
echo ""

RELAY_LOG="$RELAY_DIR/.relay.log"
PATCH_STATUS="no patch.zip (update feature will be disabled)"
[[ -f "$RELAY_DIR/patch.zip" ]] && PATCH_STATUS="patch.zip READY ✓"

echo "  Token   : ${RELAY_TOKEN:0:8}…  (${#RELAY_TOKEN} chars)"
echo "  Port    : $RELAY_PORT"
echo "  Patch   : $PATCH_STATUS"
echo ""

# Kill any stale process on that port
fuser -k "${RELAY_PORT}/tcp" 2>/dev/null || true

cd "$RELAY_DIR"
"$VENV_PYTHON" relay_server.py > "$RELAY_LOG" 2>&1 &
RELAY_PID=$!
echo "$RELAY_PID" > "$PID_FILE"

# Wait for relay to be up
echo -n "  Starting relay server"
for i in {1..15}; do
    sleep 0.5
    if curl -s "http://localhost:${RELAY_PORT}/ping" &>/dev/null; then
        echo " ✓"
        break
    fi
    echo -n "."
    if [[ $i -eq 15 ]]; then
        echo ""
        echo "  ✗ Relay did not start. Check $RELAY_LOG"
        cat "$RELAY_LOG"
        exit 1
    fi
done

# ── Start ngrok ───────────────────────────────────────────────────────────────

NGROK_LOG="$RELAY_DIR/.ngrok.log"

if [[ -n "$NGROK_DOMAIN" ]]; then
    echo -n "  Starting ngrok (static domain: $NGROK_DOMAIN)"
    ngrok http "${RELAY_PORT}" --domain="$NGROK_DOMAIN" --log=stdout > "$NGROK_LOG" 2>&1 &
else
    echo -n "  Starting ngrok (random URL)"
    ngrok http "${RELAY_PORT}" --log=stdout > "$NGROK_LOG" 2>&1 &
fi
NGROK_PID=$!
echo "$NGROK_PID" >> "$PID_FILE"

# ── Wait for ngrok URL ────────────────────────────────────────────────────────

PUBLIC_URL=""
echo -n "  Waiting for ngrok URL"
for i in {1..20}; do
    sleep 1
    # Try ngrok local API first (most reliable)
    PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
        | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tunnels = d.get('tunnels', [])
    for t in tunnels:
        url = t.get('public_url','')
        if url.startswith('https'):
            print(url)
            break
except: pass
" 2>/dev/null || true)
    if [[ -n "$PUBLIC_URL" ]]; then
        echo " ✓"
        break
    fi
    echo -n "."
    if [[ $i -eq 20 ]]; then
        echo ""
        echo "  ✗ Could not get ngrok URL. Check $NGROK_LOG"
        cat "$NGROK_LOG" | head -30
        exit 1
    fi
done

# ── Auto-save URL to relay/.env for next time ────────────────────────────────

if grep -q "^RELAY_PUBLIC_URL=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^RELAY_PUBLIC_URL=.*|RELAY_PUBLIC_URL=$PUBLIC_URL|" "$ENV_FILE"
else
    echo "RELAY_PUBLIC_URL=$PUBLIC_URL" >> "$ENV_FILE"
fi

# ── Print the info Enzo needs ──────────────────────────────────────────────────

echo ""
echo "=========================================================="
echo ""
echo "  ✅  RELAY IS ONLINE"
echo ""
echo "  Public URL : $PUBLIC_URL"
echo "  Token      : $RELAY_TOKEN"
echo ""
if [[ -z "$NGROK_DOMAIN" ]]; then
    echo "  ⚠  This URL changes every session (free ngrok)."
    echo "     To get a permanent free URL:"
    echo "       1. https://dashboard.ngrok.com/domains → Claim a free static domain"
    echo "       2. Add to relay/.env:  NGROK_DOMAIN=your-domain.ngrok-free.app"
    echo "     Then this URL never changes — bake it into the installer once."
    echo ""
fi
echo "  Vanessa's .env should have:"
echo "    RELAY_URL=$PUBLIC_URL"
echo "    RELAY_TOKEN=$RELAY_TOKEN"
echo ""
echo "  Received logs will print here in real-time."
echo "  To stop:  bash go_online.sh --stop   (or Ctrl+C)"
echo "=========================================================="
echo ""

# ── Tail the relay log live ───────────────────────────────────────────────────

cleanup() {
    echo ""
    echo "  Shutting down…"
    kill "$RELAY_PID" "$NGROK_PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "  Relay offline."
    exit 0
}
trap cleanup INT TERM

# Stream relay output to the terminal (logs land here in real-time)
tail -f "$RELAY_LOG" &
TAIL_PID=$!

# Keep alive — wait for relay process to exit
wait "$RELAY_PID" 2>/dev/null || true
kill "$TAIL_PID" 2>/dev/null || true
cleanup
