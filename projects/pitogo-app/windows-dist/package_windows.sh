#!/usr/bin/env bash
# package_windows.sh — create a distributable ZIP of the PITOGO app for Windows.
# Usage: bash windows-dist/package_windows.sh [version]
# Output: pitogo-app-<version>.zip in the current directory.

set -euo pipefail

VERSION="${1:-$(date +%Y%m%d)}"
OUT="pitogo-app-${VERSION}.zip"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo ""
echo "  PITOGO Windows Packager"
echo "  Version : ${VERSION}"
echo "  Source  : ${APP_DIR}"
echo "  Output  : ${OUT}"
echo ""

cd "${APP_DIR}"

zip -r "${APP_DIR}/${OUT}" . \
  --exclude "*.pyc" \
  --exclude "*/__pycache__/*" \
  --exclude "*/.venv/*" \
  --exclude ".venv/*" \
  --exclude "*.db" \
  --exclude "secure/users.json" \
  --exclude "secure/pitogo.log" \
  --exclude "secure/patch_private.pem" \
  --exclude "secure/sessions.json" \
  --exclude "secure/log_archives/*" \
  --exclude "secure/storage/*" \
  --exclude ".git/*" \
  --exclude "graphify-out/*" \
  --exclude "*.egg-info/*" \
  --exclude "__pycache__/*" \
  --exclude ".pytest_cache/*"

SIZE=$(du -sh "${APP_DIR}/${OUT}" | cut -f1)
echo ""
echo "  Done — ${OUT} (${SIZE})"
echo "  Copy this file to the Windows machine and extract it."
echo "  Then run: windows-dist\\install.bat"
echo ""
