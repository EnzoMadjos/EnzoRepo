#!/bin/bash
# ATLAS startup script — launches the full ATLAS assistant stack

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECURE_DIR="$SCRIPT_DIR/secure"
API_KEY_FILE="$SECURE_DIR/atlas_api.key"
PORT=8200

echo "============================================"
echo "  ATLAS — Personal AI Assistant"
echo "  Maayong pagbalik, Pre!"
echo "============================================"

# Check install has been run
if [ ! -d "$SCRIPT_DIR/venv" ] || [ ! -f "$API_KEY_FILE" ]; then
    echo "[WARN] ATLAS is not set up yet. Running installer first..."
    bash "$SCRIPT_DIR/install.sh"
fi

# Load API key
export ATLAS_API_KEY=$(cat "$API_KEY_FILE")
echo "[OK] API key loaded."

# Load .env if present (sets ATLAS_CLOUD_API_KEY, ATLAS_WORKSPACE, etc.)
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    echo "[OK] .env loaded."
fi

# Check Ollama is running
if ! ollama list &>/dev/null; then
    echo "[WARN] Ollama is not running. Starting it..."
    ollama serve &>/dev/null &
    sleep 3
fi

# Rebuild ATLAS model if missing
if ! ollama list | grep -q "^atlas"; then
    echo "[INFO] ATLAS model not found — building from Modelfile..."
    cd "$SCRIPT_DIR" && ollama create atlas -f Modelfile
fi
echo "[OK] ATLAS model ready."

echo "[OK] Starting ATLAS on http://localhost:$PORT ..."
echo "--------------------------------------------"
echo "  API Key: $ATLAS_API_KEY"
echo "  Chat UI: http://localhost:$PORT/"
echo "--------------------------------------------"

cd "$SCRIPT_DIR" && venv/bin/uvicorn app:app --host 127.0.0.1 --port $PORT
