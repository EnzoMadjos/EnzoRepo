#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# PITOGO Barangay App — Client Installer (Linux / WSL2)
#
# Run on each clerk / staff PC. No Docker needed — just the app.
# Connects to the leader PC's PostgreSQL over LAN.
# Usage: bash install_client.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$APP_DIR/.env"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   PITOGO Barangay App — Client Setup                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Check Python ───────────────────────────────────────────────────────────
echo "[ 1/5 ] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo ""
    echo "  ERROR: Python 3 is not installed."
    echo "  Install: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
PY_VER=$(python3 --version 2>&1)
echo "  ✓ $PY_VER"

# ── 2. Ask for leader IP ──────────────────────────────────────────────────────
echo "[ 2/5 ] Configuring connection..."
echo ""

# Pre-fill from saved file if exists
SAVED_IP=""
[ -f "$APP_DIR/secure/leader_ip.txt" ] && SAVED_IP=$(cat "$APP_DIR/secure/leader_ip.txt" | tr -d '[:space:]')

if [ -n "$SAVED_IP" ]; then
    read -rp "  Leader PC IP address [$SAVED_IP]: " INPUT_IP
    LEADER_IP="${INPUT_IP:-$SAVED_IP}"
else
    read -rp "  Leader PC IP address (e.g. 192.168.1.10): " LEADER_IP
fi

if [ -z "$LEADER_IP" ]; then
    echo "  ERROR: Leader IP is required."
    exit 1
fi
echo "  ✓ Leader IP: $LEADER_IP"

# Ask for DB password (copy from leader's .env)
echo ""
read -rsp "  Database password (copy from leader's .env → DB_PASS): " DB_PASS
echo ""
if [ -z "$DB_PASS" ]; then
    echo "  ERROR: Database password is required."
    exit 1
fi

# ── 3. Install Python dependencies ───────────────────────────────────────────
echo "[ 3/5 ] Installing dependencies..."

# Create venv if not present
if [ ! -d "$APP_DIR/.venv" ]; then
    python3 -m venv "$APP_DIR/.venv"
    echo "  ✓ Virtual environment created"
fi

"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
echo "  ✓ Dependencies installed"

# ── 4. Write .env for client mode ─────────────────────────────────────────────
echo "[ 4/5 ] Writing configuration..."
[ -f "$ENV_FILE" ] || cp "$APP_DIR/.env.example" "$ENV_FILE"

_set_env() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}
_set_env "NODE_ROLE"   "client"
_set_env "DB_BACKEND"  "postgres"
_set_env "DB_HOST"     "$LEADER_IP"
_set_env "DB_PORT"     "5432"
_set_env "DB_NAME"     "pitogo"
_set_env "DB_USER"     "pitogo"
_set_env "DB_PASS"     "$DB_PASS"
echo "  ✓ Config written to .env"

# ── 5. Start the app ──────────────────────────────────────────────────────────
echo "[ 5/5 ] Starting Pitogo App (client mode)..."
APP_PORT=$(grep "^APP_PORT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' ')
APP_PORT="${APP_PORT:-8300}"

# Write a start script for future use
cat > "$APP_DIR/start.sh" << 'STARTSCRIPT'
#!/usr/bin/env bash
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$APP_DIR/.venv/bin/activate"
PORT=$(grep "^APP_PORT=" "$APP_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d ' ')
PORT="${PORT:-8300}"
exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
STARTSCRIPT
chmod +x "$APP_DIR/start.sh"

# Launch
"$APP_DIR/.venv/bin/uvicorn" app:app --host 0.0.0.0 --port "$APP_PORT" &
sleep 2

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   PITOGO App is LIVE  (Client Mode)                  ║"
echo "║                                                      ║"
printf "║   Browser:   http://localhost:%-24s║\n" "${APP_PORT}"
printf "║   Leader DB: %-39s║\n" "${LEADER_IP}:5432"
echo "║                                                      ║"
echo "║   To restart later: bash start.sh                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
