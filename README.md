# ResilienceOS (Public Base)

Offline-first “Resilience OS” starter kit: local dashboard + watchdog + backup tooling.

This repo is intentionally **GDPR-safe**:
- No personal identity data
- No bank/paypal exports
- No private docs/reports
- No AI models (`.gguf`, `.safetensors`, …)
- No Kiwix / Wikipedia `.zim` files

You clone this base, then you add your **own** private context locally (and keep it out of Git).

## Docs
- `docs/INSTALL.md` — install & first boot
- `docs/ARCHITECTURE.md` — how the pieces connect
- `docs/PRIVACY.md` — GDPR boundary & what never goes to Git
- `docs/BROWSER_AUTOMATION.md` — how an agent can “drive the browser” safely
- `docs/DEEP_RESEARCH_PROMPT.md` — S-tier research prompt (evidence rules + query pack)

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

## Versioning
See `CHANGELOG.md`. GitHub Releases are tagged (`vX.Y.Z`).
