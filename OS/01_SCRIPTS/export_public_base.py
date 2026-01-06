#!/usr/bin/env python3
"""
Export a GDPR-friendly "base system" snapshot for GitHub.

This script creates a new folder that contains:
- core scripts + dashboard (minimal runnable subset)
- public docs (generic, no personal context / no identity)
- example config templates (no personal data)

It intentionally excludes:
- Sources/, Psychotherapie/, SYSTEM_CONTEXT/
- OS/03_REPORTS/, OS/99_DERIVED_TEXT/, OS/logs/
- private state/data files under OS/00_CORE_DATA
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


PUBLIC_EXCLUDES = {
    "Sources",
    "Psychotherapie",
    "SYSTEM_CONTEXT",
    "Upwork Outreach",
    "stunspotPrompts",
    "prepper central erweiterung",
}

ESSENTIAL_SCRIPTS = [
    # One-click boot + dashboard
    "omega_one_click.py",
    "dashboard_server.py",
    "dashboard_smoke_test.py",
    "history_tracker.py",
    # Infrastructure / process mgmt
    "infrastructure_manager.py",
    # Watchdog (optional, but part of the “base OS” story)
    "power_watchdog_service.py",
    "power_watchdog_ctl.py",
    # Context / clipboard
    "load_context.py",
    # Backups + public export itself
    "backup_resilience_os.py",
    "export_public_base.py",
    "verify_public_export.py",
    # Helpful, still safe to include (no private data required)
    "update_kernel_balances.py",
]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dst: Path) -> None:
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path, ignore_globs: List[str]) -> None:
    def _ignore(_dir: str, names: List[str]) -> set:
        ignored = set()
        for n in names:
            # always ignore caches
            if n in {".DS_Store", "__pycache__", "node_modules", ".git", ".idea", ".vscode"}:
                ignored.add(n)
                continue
        return ignored

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=False)
    # second pass: remove ignored patterns by glob (simple)
    for pat in ignore_globs:
        for p in dst.rglob(pat):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    p.unlink()
                except Exception:
                    pass


def write_json(dst: Path, data: object) -> None:
    ensure_dir(dst.parent)
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(dst: Path, text: str) -> None:
    ensure_dir(dst.parent)
    dst.write_text(text.strip() + "\n", encoding="utf-8")


def write_public_root_readme(dst_root: Path) -> None:
    write_text(dst_root / "README.md", """
# ResilienceOS (Public Base)

Offline-first “Resilience OS” starter kit: local dashboard + watchdog + backup tooling.

This repo is intentionally **GDPR-safe**:
- No personal identity data
- No bank/paypal exports
- No private docs/reports
- No AI models (`.gguf`, `.safetensors`, …)
- No Kiwix / Wikipedia `.zim` files

You clone this base, then you add your **own** private context locally (and keep it out of Git).

## Quickstart (Mac / Linux)
1) Copy example configs (first run):
   - `cp OS/00_CORE_DATA/omega_kernel.example.json OS/00_CORE_DATA/omega_kernel.json`
   - `cp OS/00_CORE_DATA/value_ledger.example.json OS/00_CORE_DATA/value_ledger.json`
   - `cp OS/00_CORE_DATA/ports_config.example.json OS/00_CORE_DATA/ports_config.json`
   - `cp OS/00_CORE_DATA/power_watchdog_config.example.json OS/00_CORE_DATA/power_watchdog_config.json`
   - `cp OS/00_CORE_DATA/paypal_category_rules.example.json OS/00_CORE_DATA/paypal_category_rules.json`

2) Start the dashboard (lowest friction):
   - Double-click `OMEGA_ONE_CLICK.command`
   - Open the printed URL (it may use a non-3000 port automatically)

3) Sanity check:
   - `python3 OS/01_SCRIPTS/dashboard_smoke_test.py`

## Optional: Background “Power Watchdog”
Start/stop:
- `python3 OS/01_SCRIPTS/power_watchdog_ctl.py start`
- `python3 OS/01_SCRIPTS/power_watchdog_ctl.py stop`

## Optional: Backups (to external drive)
- Double-click `BACKUP_RESILIENCE_OS.command`
- Or: `python3 OS/01_SCRIPTS/backup_resilience_os.py --dest /Volumes/KiwixVault/ResilienceOS_BACKUPS --delete`

## Before publishing anywhere (always)
- `python3 OS/01_SCRIPTS/verify_public_export.py .`

## Publish (safe)
- Double-click `PUBLISH_PUBLIC.command` (preflight + next steps)
""")


def example_core_data(dst_root: Path) -> None:
    core = dst_root / "OS" / "00_CORE_DATA"
    ensure_dir(core)

    write_json(core / "omega_kernel.example.json", {
        "_last_updated": "1970-01-01T00:00:00Z",
        "current_balances": {
            "volksbank_available": 0.0,
            "revolut_eur": 0.0,
            "net_liquidity": 0.0
        },
        "pending_transactions": {"inflows": {}},
        "financial_intelligence": {"runway_calculation": {"runway_days": 0.0, "monthly_burn": 0.0}}
    })

    write_json(core / "value_ledger.example.json", {
        "summary": {"priority_actions": []},
        "priority_actions": [],
    })

    write_json(core / "ports_config.example.json", {
        "dashboard": {"port": 3000, "managed": True, "command": ["python3", "OS/01_SCRIPTS/omega_one_click.py"]},
        "watchdog": {"managed": True, "command": ["python3", "OS/01_SCRIPTS/power_watchdog_ctl.py", "start"]},
        "ollama": {"managed": False, "port": 11434, "command": ["ollama", "serve"]},
    })

    write_json(core / "power_watchdog_config.example.json", {
        "enabled": True,
        "check_interval_seconds": 300,
        "keywords": ["Stromausfall", "Wiederversorgung", "Stromnetz"],
        "sources": [
            {"name": "rbb24", "url": "https://www.rbb24.de/aktuell/index.xml/allitems=true/feed=rss"},
            {"name": "berlin.de", "url": "https://www.berlin.de/presse/pressemitteilungen/index/feed"}
        ]
    })

    write_json(core / "paypal_category_rules.example.json", {
        "version": 1,
        "default_category": "UNCATEGORIZED",
        "rules": []
    })

    write_text(core / "README.md", """
Core Data (Public)
=================
This folder contains **example** configs only.

For real operation, copy `*.example.json` to the expected filenames:
- `omega_kernel.json`
- `value_ledger.json`
- `ports_config.json`
- `power_watchdog_config.json`
- `paypal_category_rules.json`

Never commit real personal/financial data.
""")


def public_docs(dst_root: Path) -> None:
    crisis = dst_root / "OS" / "06_CRISIS"
    ensure_dir(crisis)
    write_text(crisis / "MASTER_START_PUBLIC.md", """
# ResilienceOS — Master Start (Public, Offline-First)
Goal: boot the system in <60 seconds and keep it usable with small context windows.

1) Double-click `OMEGA_ONE_CLICK.command`
2) Dashboard opens automatically (port is stored in `OS/logs/dashboard_server.port`)
3) Use **Copy NEW CHAT PACK** to start a new AI chat with consistent context

Safety:
- Evidence-first: never invent numbers
- Keep private data out of Git
""")

    write_text(crisis / "INSTALL_PUBLIC.md", """
# ResilienceOS — Install (Public Base)

## What you need
- Python 3 (ships with macOS)
- A browser

## Install
1) Clone this repo:
   - `git clone <REPO_URL>`
2) Copy configs from templates:
   - `cp OS/00_CORE_DATA/*.example.json OS/00_CORE_DATA/` (and rename each to drop `.example`)
3) Start:
   - `./OMEGA_ONE_CLICK.command`

## Add your own private context (local only)
Create a local folder like `OS/00_PRIVATE/` and store any identity / financial exports there.
This folder must stay out of Git (already ignored).
""")

    write_text(crisis / "PRIVACY_BOUNDARY.md", """
# Privacy Boundary (GDPR)

This repo is intended to be published publicly.

Never commit:
- Personal identity (names, addresses, IDs, phone, email)
- Bank/PayPal exports and transaction logs
- Private documents (`Sources/`, `Psychotherapie/`, `SYSTEM_CONTEXT/`, reports)
- AI model files (`*.gguf`, `*.safetensors`, `*.bin`, `*.pt`, …)
- Kiwix / Wikipedia `.zim` knowledge vaults

Use `python3 OS/01_SCRIPTS/verify_public_export.py .` as a preflight check.
Optional: add your own patterns:
- `python3 OS/01_SCRIPTS/verify_public_export.py . --extra-patterns OS/00_PRIVATE/verify_patterns.txt`
""")

    write_text(crisis / "PUBLISH_PUBLIC.md", """
# Publish to GitHub (safe workflow)

Recommended: publish this base as its **own repo** (clean history).

If you must publish into an existing repo, publish into a **new branch** (do not overwrite `main` blindly):

1) Verify:
   - `python3 OS/01_SCRIPTS/verify_public_export.py .`
2) Create and push branch:
   - `git checkout -b public-base`
   - `git add .`
   - `git commit -m "ResilienceOS Base (public)"`
   - `git push -u origin public-base`

Then set the default branch on GitHub to `public-base` (optional).
""")

def write_publish_command(dst_root: Path) -> None:
    script = """#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== ResilienceOS Public Publish (safe mode) =="
python3 OS/01_SCRIPTS/verify_public_export.py .

echo ""
echo "Next steps (manual):"
echo "  git init"
echo "  git add ."
echo "  git commit -m \"ResilienceOS Base (public)\""
echo "  git remote add origin https://github.com/<USER>/<REPO>.git"
echo "  git branch -M main"
echo "  git push -u origin main"
"""
    path = dst_root / "PUBLISH_PUBLIC.command"
    write_text(path, script)
    try:
        path.chmod(0o755)
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default=str(repo_root() / "_PUBLIC_BASE_EXPORT"), help="Destination directory.")
    args = parser.parse_args()

    src = repo_root()
    dest = Path(args.dest).expanduser().resolve()
    ensure_dir(dest)
    out = dest / f"Resilience-OS_BASE_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
    ensure_dir(out)

    included = {
        "copied_root_files": [],
        "copied_dirs": [
            "OS/05_DASHBOARD",
            "OS/06_CRISIS/*",
            "OS/00_CORE_DATA/*.example.json",
        ],
        "copied_scripts_allowlist": ESSENTIAL_SCRIPTS,
        "excluded_roots": sorted(list(PUBLIC_EXCLUDES)),
        "excluded_runtime": ["OS/logs", "OS/03_REPORTS", "OS/99_DERIVED_TEXT"],
    }

    # Root files (no private docs)
    for fname in ["OMEGA_ONE_CLICK.command", "BACKUP_RESILIENCE_OS.command"]:
        p = src / fname
        if p.exists():
            copy_file(p, out / fname)
            included["copied_root_files"].append(fname)

    # OS scripts (allowlist only)
    ensure_dir(out / "OS" / "01_SCRIPTS")
    for script in ESSENTIAL_SCRIPTS:
        p = src / "OS" / "01_SCRIPTS" / script
        if not p.exists():
            continue
        copy_file(p, out / "OS" / "01_SCRIPTS" / script)

    copy_tree(src / "OS" / "05_DASHBOARD", out / "OS" / "05_DASHBOARD", ignore_globs=[])

    # Public docs + example data
    public_docs(out)
    write_public_root_readme(out)
    example_core_data(out)
    write_publish_command(out)
    included["copied_root_files"].append("PUBLISH_PUBLIC.command")

    # Public .gitignore hardening for the export
    write_text(out / ".gitignore", """
.DS_Store
__pycache__/
*.pyc
node_modules/
.env

OS/logs/
OS/03_REPORTS/
OS/99_DERIVED_TEXT/
Sources/
Psychotherapie/
SYSTEM_CONTEXT/
Upwork Outreach/
stunspotPrompts/
prepper central erweiterung/
OS/00_PRIVATE/

OS/00_CORE_DATA/*.json
!OS/00_CORE_DATA/*.example.json
""")

    write_json(out / "EXPORT_MANIFEST.json", {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "included": included,
        "note": "This is a GDPR-friendly base export. Do not add private data.",
    })

    print(json.dumps({"ok": True, "export_dir": str(out)}, indent=2))


if __name__ == "__main__":
    main()
