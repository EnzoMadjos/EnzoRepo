#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# create_patch.sh  —  Build a patch.zip for remote deployment
#
# Usage:
#   bash create_patch.sh                 # auto-detect all git changes
#   bash create_patch.sh sf_app.py templates/qa.html   # specific files only
#
# Output:  patch.zip  (in this folder)
#
# After running:
#   1. Upload patch.zip to Google Drive  (make it publicly accessible)
#   2. Right-click → Get link → change to "Anyone with the link"
#   3. Convert share link to direct-download:
#        Share URL:   https://drive.google.com/file/d/FILE_ID/view?usp=sharing
#        Direct URL:  https://drive.google.com/uc?export=download&id=FILE_ID
#   4. Paste the direct URL into her .env:   UPDATE_URL=<direct URL>
#   5. She opens Admin panel → "Check for Update" → "Apply Update"
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_ZIP="$APP_DIR/patch.zip"
TEMP_DIR="$(mktemp -d)"
PATCH_APP_DIR="$TEMP_DIR/patch"   # files go inside a "patch/" folder in zip

cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

echo ""
echo "SF QA Agent — Patch Builder"
echo "──────────────────────────────────────────"

# ── Determine which files to include ────────────────────────────────────────

if [[ $# -gt 0 ]]; then
    # Files passed explicitly on command-line
    FILES=("$@")
    echo "Mode: manual — ${#FILES[@]} file(s) specified"
else
    # Auto-detect from git
    if ! git -C "$APP_DIR" rev-parse --git-dir &>/dev/null; then
        echo "ERROR: Not a git repo and no files specified."
        echo "Usage: bash create_patch.sh <file1> [file2 ...]"
        exit 1
    fi

    mapfile -t FILES < <(
        git -C "$APP_DIR" diff --name-only HEAD 2>/dev/null
        git -C "$APP_DIR" diff --name-only --cached 2>/dev/null
        git -C "$APP_DIR" ls-files --others --exclude-standard 2>/dev/null
    )
    # Deduplicate
    mapfile -t FILES < <(printf '%s\n' "${FILES[@]}" | sort -u)

    echo "Mode: auto (git changes) — ${#FILES[@]} file(s) detected"
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo ""
    echo "No files to patch (no git changes and no files specified)."
    exit 0
fi

# ── Copy files into temp patch folder ───────────────────────────────────────

ALLOWED_EXTS=".py .html .css .js .txt .json .md"
BLOCKED_FILES="auth.py config.py"
INCLUDED=()
SKIPPED=()

for f in "${FILES[@]}"; do
    abs="$APP_DIR/$f"
    [[ -f "$abs" ]] || { SKIPPED+=("$f  (not found)"); continue; }

    base="$(basename "$f")"
    ext="${f##*.}"; ext=".$ext"

    # Skip binary / non-patchable extensions
    if [[ ! " $ALLOWED_EXTS " =~ " $ext " ]]; then
        SKIPPED+=("$f  (extension $ext not allowed)"); continue
    fi
    # Never include security-critical files
    if [[ " $BLOCKED_FILES " =~ " $base " ]]; then
        SKIPPED+=("$f  (protected — skipped for safety)"); continue
    fi

    dest="$PATCH_APP_DIR/$f"
    mkdir -p "$(dirname "$dest")"
    cp "$abs" "$dest"
    INCLUDED+=("$f")
done

echo ""
echo "Including ${#INCLUDED[@]} file(s):"
for f in "${INCLUDED[@]}"; do echo "  ✔ $f"; done

if [[ ${#SKIPPED[@]} -gt 0 ]]; then
    echo ""
    echo "Skipping ${#SKIPPED[@]} file(s):"
    for f in "${SKIPPED[@]}"; do echo "  ⚠ $f"; done
fi

if [[ ${#INCLUDED[@]} -eq 0 ]]; then
    echo ""; echo "Nothing to patch after filtering. Exiting."
    exit 1
fi

# ── Create zip ───────────────────────────────────────────────────────────────

[[ -f "$PATCH_ZIP" ]] && rm "$PATCH_ZIP"

(cd "$TEMP_DIR" && zip -r "$PATCH_ZIP" patch/) > /dev/null

echo ""
echo "──────────────────────────────────────────"
echo "  patch.zip created: $PATCH_ZIP"
SIZE=$(du -h "$PATCH_ZIP" | cut -f1)
echo "  Size: $SIZE"
echo ""
echo "  NEXT STEPS:"
echo "  1. Upload patch.zip to Google Drive (set sharing to 'Anyone with link')"
echo "  2. Get the FILE_ID from the share URL:"
echo "       https://drive.google.com/file/d/FILE_ID/view..."
echo "  3. Build the direct download URL:"
echo "       https://drive.google.com/uc?export=download&id=FILE_ID"
echo "  4. Edit her .env and set:"
echo "       UPDATE_URL=https://drive.google.com/uc?export=download&id=FILE_ID"
echo "  5. Tell her: Admin Panel → Check for Update → Apply Update"
echo "──────────────────────────────────────────"
echo ""
