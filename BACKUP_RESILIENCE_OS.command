#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

python3 "$ROOT/OS/01_SCRIPTS/backup_resilience_os.py"

