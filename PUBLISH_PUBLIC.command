#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== ResilienceOS Public Publish (safe mode) =="
python3 OS/01_SCRIPTS/verify_public_export.py .

echo ""
echo "Next steps (manual):"
echo "  git init"
echo "  git add ."
echo "  git commit -m "ResilienceOS Base (public)""
echo "  git remote add origin https://github.com/<USER>/<REPO>.git"
echo "  git branch -M main"
echo "  git push -u origin main"
