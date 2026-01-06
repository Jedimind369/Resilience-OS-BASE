#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
python3 "$ROOT/OS/01_SCRIPTS/omega_one_click.py"

