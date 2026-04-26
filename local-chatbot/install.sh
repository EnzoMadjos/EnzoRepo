#!/bin/bash
# ATLAS — Installation & Setup Script
# Run this once on any new machine to set everything up.
# Pre, just drop this folder anywhere and run: bash install.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECURE_DIR="$SCRIPT_DIR/secure"

echo "============================================"
echo "  ATLAS — Installation & Setup"
echo "  Maayong pag-abot Pre! Setting up..."
echo "============================================"

# 1. Check Python
echo ""
echo "[1/7] Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python3 is not installed. Please install Python 3.10+ first."
    exit 1
fi
python3 --version
echo "[OK] Python found."

# 2. Check Ollama
echo ""
echo "[2/7] Checking Ollama..."
if ! command -v ollama &>/dev/null; then
    echo "[ERROR] Ollama is not installed."
    echo "        Please install it from: https://ollama.ai"
    exit 1
fi
echo "[OK] Ollama found."

# 3. Create virtual environment
echo ""
echo "[3/7] Setting up Python virtual environment..."
cd "$SCRIPT_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

# 4. Install dependencies
echo ""
echo "[4/7] Installing Python dependencies..."
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "[OK] Dependencies installed."

# 5. Create secure folder and generate keys
echo ""
echo "[5/7] Setting up secure folder..."
mkdir -p "$SECURE_DIR"
chmod 700 "$SECURE_DIR"

if [ ! -f "$SECURE_DIR/atlas_api.key" ]; then
    python3 - <<PY
import secrets
from pathlib import Path
key = secrets.token_urlsafe(32)
Path("$SECURE_DIR/atlas_api.key").write_text(key, encoding="utf-8")
print(f"[OK] New API key generated and saved.")
PY
else
    echo "[OK] API key already exists."
fi

if [ ! -f "$SECURE_DIR/atlas.key" ]; then
    python3 - <<PY
from cryptography.fernet import Fernet
from pathlib import Path
key = Fernet.generate_key()
Path("$SECURE_DIR/atlas.key").write_bytes(key)
print("[OK] Encryption key generated.")
PY
else
    echo "[OK] Encryption key already exists."
fi

# 6. Build ATLAS Ollama model
echo ""
echo "[6/7] Building ATLAS Ollama model..."
if ollama list | grep -q "^atlas"; then
    echo "[OK] ATLAS model already exists."
else
    cd "$SCRIPT_DIR" && ollama create atlas -f Modelfile
    echo "[OK] ATLAS model created."
fi

# 7. Initialize secure data files if missing
echo ""
echo "[7/7] Initializing secure data files..."
python3 - <<PY
import json
from pathlib import Path

secure = Path("$SECURE_DIR")

defaults = {
    "atlas_traits.json": [],
    "atlas_training.json": [],
    "atlas_trust.json": {
        "trusted": True,
        "granted_at": None,
        "scope": ["full"],
        "notes": "Full trusted access granted for the local ATLAS assistant.",
        "last_updated": None,
    },
    "atlas_nickname_profile.json": {
        "preferred": None,
        "options": ["Pre", "Lods"],
        "last_updated": None,
    },
}

for filename, default_data in defaults.items():
    target = secure / filename
    if not target.exists():
        target.write_text(json.dumps(default_data, indent=2), encoding="utf-8")
        print(f"[OK] Created {filename}")
    else:
        print(f"[OK] {filename} already exists.")
PY

# 8. Set passphrase for browser login
echo ""
echo "[8/8] Setting up browser passphrase..."
if [ -f "$SECURE_DIR/atlas_pass.json" ]; then
    echo "[OK] Passphrase already set. Change it anytime from the Settings tab in the UI."
else
    echo ""
    echo "  This is what you type in the browser to unlock ATLAS."
    echo "  Choose something only you will remember (min 4 characters)."
    echo ""
    while true; do
        read -rsp "  Enter your passphrase: " ATLAS_PASS
        echo ""
        read -rsp "  Confirm passphrase: " ATLAS_PASS2
        echo ""
        if [ "${#ATLAS_PASS}" -lt 4 ]; then
            echo "  [ERROR] Too short. At least 4 characters please."
        elif [ "$ATLAS_PASS" != "$ATLAS_PASS2" ]; then
            echo "  [ERROR] Passphrases don't match. Try again."
        else
            break
        fi
    done
    "$VENV_DIR/bin/python" - <<PY
import sys, os
sys.path.insert(0, "$SCRIPT_DIR")
os.chdir("$SCRIPT_DIR")
from auth_passphrase import set_passphrase
set_passphrase("""$ATLAS_PASS""")
print("[OK] Passphrase saved securely.")
PY
fi

echo ""
echo "============================================"
echo "  ATLAS Setup Complete!"
echo ""
echo "  To start ATLAS, run:"
echo "    ./start_atlas.sh"
echo ""
echo "  Then open the chat UI in your browser:"
echo "    http://127.0.0.1:8000/ui/"
echo ""
echo "  Login with your passphrase — no API key needed!"
echo "============================================"
