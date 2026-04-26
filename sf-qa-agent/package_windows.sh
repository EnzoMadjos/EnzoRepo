#!/usr/bin/env bash
# package_windows.sh
# Builds the Windows distribution zip for Gmail delivery.
# Run from the sf-qa-agent project root.
# Output: sf-qa-agent-windows.zip (well under 25 MB)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ZIP_NAME="sf-qa-agent-windows.zip"
STAGING="$(mktemp -d)/SalesforceQA-Install"
APP_STAGING="$STAGING/app"
DOCS_STAGING="$STAGING/docs"
ASSETS_STAGING="$STAGING/assets"

echo "========================================"
echo "  SF QA Test Agent — Windows Packager"
echo "========================================"
echo ""
echo "Staging to: $STAGING"
echo ""

# -----------------------------------------------------------------------
# Create staging structure
# -----------------------------------------------------------------------
mkdir -p "$APP_STAGING/templates"
mkdir -p "$APP_STAGING/secure"
mkdir -p "$DOCS_STAGING"
mkdir -p "$ASSETS_STAGING"
mkdir -p "$STAGING/dist"   # empty — PyInstaller writes here

# -----------------------------------------------------------------------
# Copy launcher + installer (root of zip)
# -----------------------------------------------------------------------
cp windows-dist/install.bat   "$STAGING/install.bat"
cp windows-dist/launcher.py   "$STAGING/launcher.py"
cp windows-dist/debug.bat     "$STAGING/debug.bat"

# -----------------------------------------------------------------------
# Copy app source
# -----------------------------------------------------------------------
for f in sf_app.py auth.py config.py sf_client.py sf_executor.py \
          llm_planner.py org_profiles.py app_logger.py file_parser.py \
          requirements.txt .env.example; do
    if [ -f "$f" ]; then
        cp "$f" "$APP_STAGING/$f"
    fi
done

# HTML template
cp templates/qa.html "$APP_STAGING/templates/qa.html"

# -----------------------------------------------------------------------
# Copy documentation
# -----------------------------------------------------------------------
cp README.md                 "$DOCS_STAGING/README.md"
cp CONNECTED_APP_SETUP.md    "$DOCS_STAGING/CONNECTED_APP_SETUP.md"

# -----------------------------------------------------------------------
# Create a plain-text QUICK_START.txt for the zip root
# -----------------------------------------------------------------------
cat > "$STAGING/QUICK_START.txt" << 'EOF'
SF QA Test Agent — Quick Start
===============================

REQUIREMENTS BEFORE INSTALLING
--------------------------------
1. Python 3.10+   →  https://www.python.org/downloads/
   - During install CHECK: "Add Python to PATH"

2. Ollama         →  https://ollama.com/download
   - Install, then run install.bat (it will pull the AI model automatically)

INSTALLATION
------------
1. Extract this zip anywhere (e.g. C:\SalesforceQA\)
2. Right-click install.bat → "Run as administrator"
   - Follow the on-screen prompts
   - First-time AI model download is ~2 GB; keep the window open
3. When done, a shortcut appears on your Desktop: "SF QA Test Agent"

RUNNING THE APP
---------------
Double-click the "SF QA Test Agent" desktop icon.
Your browser will open to http://localhost:8200

FIRST USE
---------
- Log in with your Salesforce credentials (Never stored to disk in plain text)
- See docs/README.md and docs/CONNECTED_APP_SETUP.md for full details

TROUBLESHOOTING
---------------
- "Python not found" — re-install Python and check "Add to PATH"
- "Ollama not found" — install Ollama from https://ollama.com/download
- App won't start — open a terminal in the app\ folder and run:
    .venv\Scripts\python.exe -m uvicorn sf_app:app --port 8200
  Then visit http://localhost:8200

UNINSTALL
---------
Delete the extracted folder and the Desktop shortcut. Nothing else is written
to your system aside from the Python venv inside the app\ folder.

EOF

# -----------------------------------------------------------------------
# Create icon placeholder README
# -----------------------------------------------------------------------
cat > "$ASSETS_STAGING/README.txt" << 'EOF'
Place your app icon here as "icon.ico".
If this file is absent, the installer will use the default Windows icon.
The icon must be Windows .ico format (256x256 recommended).
EOF

# -----------------------------------------------------------------------
# Zip everything (using Python — no zip command required)
# -----------------------------------------------------------------------
echo "Creating zip..."

# ── Stamp relay credentials into the packaged .env.example ──────────────────
# Reads RELAY_TOKEN and NGROK_DOMAIN (or RELAY_PUBLIC_URL) from relay/.env
# so Vanessa's installer pre-populates her .env automatically — no manual step.

RELAY_ENV="$SCRIPT_DIR/relay/.env"
STAMPED_ENV="$APP_STAGING/.env.example"

RELAY_TOKEN_VAL=""

if [[ -f "$RELAY_ENV" ]]; then
    RELAY_TOKEN_VAL=$(grep -E '^RELAY_TOKEN=' "$RELAY_ENV" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true)
fi

if [[ -n "$RELAY_TOKEN_VAL" ]]; then
    sed -i "s|^RELAY_TOKEN=.*|RELAY_TOKEN=${RELAY_TOKEN_VAL}|" "$STAMPED_ENV"
    echo "  RELAY_TOKEN stamped into .env.example ✓"
else
    echo "  WARNING: RELAY_TOKEN not set in relay/.env — users will need to add it manually."
fi

# NOTE: RELAY_URL is intentionally left blank — Vanessa pastes it via the admin UI
echo "  RELAY_URL left blank (user pastes URL via admin panel) ✓"

python3 - <<PYEOF
import zipfile, os, sys

staging   = "$STAGING"
zip_out   = "$SCRIPT_DIR/$ZIP_NAME"
root_name = "SalesforceQA-Install"

skip_dirs  = {'__pycache__', '.git', '.venv'}
skip_exts  = {'.pyc', '.pyo'}

with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for dirpath, dirnames, filenames in os.walk(staging):
        # Prune ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            if os.path.splitext(fname)[1] in skip_exts:
                continue
            full = os.path.join(dirpath, fname)
            arcname = root_name + full[len(staging):]
            zf.write(full, arcname)

size_mb = os.path.getsize(zip_out) / (1024 * 1024)
print(f"Size: {size_mb:.2f} MB")
if size_mb > 24:
    print("WARNING: File is over 24 MB — may not attach to Gmail.")
PYEOF

# -----------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------
SIZE_KB=$(du -k "$SCRIPT_DIR/$ZIP_NAME" | cut -f1)
SIZE_MB=$(echo "scale=2; $SIZE_KB/1024" | bc)

echo ""
echo "========================================"
echo "  Done: $ZIP_NAME  (${SIZE_MB} MB)"
echo "  Gmail limit: 25 MB"
echo "========================================"
echo ""
echo "Contents:"
python3 -c "
import zipfile
with zipfile.ZipFile('$SCRIPT_DIR/$ZIP_NAME') as z:
    for i in z.infolist():
        kb = i.file_size // 1024
        print(f'  {i.filename}  ({kb} KB)')
"
