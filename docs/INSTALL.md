# Install & First Boot (Public Base)

## Requirements
- Python 3 (macOS ships with it)
- A browser

## 1) Clone
```bash
git clone https://github.com/Jedimind369/Resilience-OS-BASE.git
cd Resilience-OS-BASE
```

## 2) Copy configs from templates (first run)
```bash
cp OS/00_CORE_DATA/omega_kernel.example.json OS/00_CORE_DATA/omega_kernel.json
cp OS/00_CORE_DATA/value_ledger.example.json OS/00_CORE_DATA/value_ledger.json
cp OS/00_CORE_DATA/ports_config.example.json OS/00_CORE_DATA/ports_config.json
cp OS/00_CORE_DATA/power_watchdog_config.example.json OS/00_CORE_DATA/power_watchdog_config.json
cp OS/00_CORE_DATA/paypal_category_rules.example.json OS/00_CORE_DATA/paypal_category_rules.json
```

## 3) Start (lowest friction)
- Double-click `OMEGA_ONE_CLICK.command`

Or via terminal:
```bash
python3 OS/01_SCRIPTS/omega_one_click.py
```

## 4) Verify
```bash
python3 OS/01_SCRIPTS/dashboard_smoke_test.py
```

## 5) Keep private context private
Create `OS/00_PRIVATE/` for any personal identity/exports. This stays out of Git by default.
