# Architecture (Public Base)

## Goal
Run a small, offline-first “ops OS” locally:
- Dashboard on `localhost`
- Optional watchdog service
- Backups to an external drive

## Components

### Dashboard (UI)
- `OS/05_DASHBOARD/` (Vanilla HTML/CSS/JS)
- Pulls from the local API:
  - `GET /api/status`
  - `GET /api/staleness`
  - `GET /api/trends`

### Dashboard Server (API)
- `OS/01_SCRIPTS/dashboard_server.py`
- Reads `OS/00_CORE_DATA/omega_kernel.json` and `OS/00_CORE_DATA/value_ledger.json`
- Writes runtime state to `OS/logs/` (ignored by git)

### One-Click Boot
- `OMEGA_ONE_CLICK.command` → `OS/01_SCRIPTS/omega_one_click.py`
- Picks a free port, starts the server, checks readiness endpoints.

### Watchdog (optional)
- `OS/01_SCRIPTS/power_watchdog_service.py` + `power_watchdog_ctl.py`
- Polls RSS sources and raises native notifications.

### Backup
- `BACKUP_RESILIENCE_OS.command` → `OS/01_SCRIPTS/backup_resilience_os.py`
- Produces:
  - `_CURRENT_MIRROR/` (rsync mirror)
  - `<timestamp>/snapshot.tar.gz` + `repo.bundle` + `MANIFEST.json`

## Data Separation (GDPR boundary)
- Public: code + `*.example.json` templates
- Private (local only): real `OS/00_CORE_DATA/*.json`, exports, identity, reports
