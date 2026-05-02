#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# PITOGO Barangay App — Leader Installer (Linux / WSL2)
#
# Run once on the main office PC. Installs PostgreSQL + the app together.
# Usage: bash install_leader.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$APP_DIR/.env"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   PITOGO Barangay App — Leader Setup                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Check Docker ───────────────────────────────────────────────────────────
echo "[ 1/6 ] Checking Docker..."
if ! command -v docker &>/dev/null; then
    echo ""
    echo "  ERROR: Docker is not installed."
    echo "  Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
if ! docker compose version &>/dev/null; then
    echo ""
    echo "  ERROR: Docker Compose v2 is required."
    echo "  Update Docker Desktop or install the compose plugin."
    exit 1
fi
echo "  ✓ Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# ── 2. Create .env from example if not present ───────────────────────────────
echo "[ 2/6 ] Setting up environment..."
if [ ! -f "$ENV_FILE" ]; then
    cp "$APP_DIR/.env.example" "$ENV_FILE"
    echo "  ✓ Created .env from template"
fi

# Generate DB password if empty or missing
CURRENT_PASS=$(grep "^DB_PASS=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' ')
if [ -z "$CURRENT_PASS" ]; then
    DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    # Update or append DB_PASS
    if grep -q "^DB_PASS=" "$ENV_FILE"; then
        sed -i "s|^DB_PASS=.*|DB_PASS=$DB_PASS|" "$ENV_FILE"
    else
        echo "DB_PASS=$DB_PASS" >> "$ENV_FILE"
    fi
    echo "  ✓ Generated secure database password"
else
    echo "  ✓ Using existing database password"
fi

# Ensure DB vars are set for leader mode
_set_env() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}
_set_env "DB_BACKEND" "postgres"
_set_env "DB_HOST"    "localhost"
_set_env "DB_PORT"    "5432"
_set_env "DB_NAME"    "pitogo"
_set_env "DB_USER"    "pitogo"
_set_env "NODE_ROLE"  "leader"
echo "  ✓ DB config written to .env"

# ── 3. Pull PostgreSQL image ──────────────────────────────────────────────────
echo "[ 3/6 ] Pulling PostgreSQL 16 image..."
docker pull postgres:16-alpine
echo "  ✓ Image ready"

# ── 4. Start services ─────────────────────────────────────────────────────────
echo "[ 4/6 ] Starting PostgreSQL + Pitogo App..."
cd "$APP_DIR"
docker compose --profile leader up -d --build
echo "  ✓ Containers started"

# ── 5. Wait for DB to be healthy ──────────────────────────────────────────────
echo "[ 5/6 ] Waiting for database to be ready..."
DB_USER=$(grep "^DB_USER=" "$ENV_FILE" | cut -d= -f2 | tr -d ' ')
DB_NAME=$(grep "^DB_NAME=" "$ENV_FILE" | cut -d= -f2 | tr -d ' ')
MAX_WAIT=60
WAITED=0
until docker compose exec -T db pg_isready -U "${DB_USER:-pitogo}" -d "${DB_NAME:-pitogo}" -q 2>/dev/null; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ERROR: Database did not start within ${MAX_WAIT}s."
        echo "  Run: docker compose logs db"
        exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done
echo "  ✓ Database is ready (${WAITED}s)"

# ── 6. Run migrations ─────────────────────────────────────────────────────────
echo "[ 6/6 ] Running database migrations..."
docker compose exec -T app alembic upgrade head
echo "  ✓ Database schema is up to date"

# ── Done ──────────────────────────────────────────────────────────────────────
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
APP_PORT=$(grep "^APP_PORT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 | tr -d ' ')
APP_PORT="${APP_PORT:-8300}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   PITOGO App is LIVE                                 ║"
echo "║                                                      ║"
printf "║   Browser:  http://%-34s║\n" "${LAN_IP}:${APP_PORT}"
echo "║                                                      ║"
printf "║   Client PCs → use Leader IP: %-23s║\n" "$LAN_IP"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Save leader IP to file so client installer can reference it
echo "$LAN_IP" > "$APP_DIR/secure/leader_ip.txt"
echo "  Leader IP saved to secure/leader_ip.txt"
echo ""
