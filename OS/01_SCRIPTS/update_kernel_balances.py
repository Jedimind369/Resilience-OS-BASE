#!/usr/bin/env python3
"""
OMEGA Balance Updater
Updates omega_kernel.json balances and recalculates runway.

Usage examples:
  python3 update_kernel_balances.py --volksbank 30.42 --revolut-eur 9.33 --telekom 42.95
  python3 update_kernel_balances.py --volksbank 240.50 --revolut-eur 9.33 --timestamp 2026-01-02T09:03:00+01:00
  python3 update_kernel_balances.py  # Recalculate derived fields using current values
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update omega_kernel current balances and runway.")
    parser.add_argument("--volksbank", type=float, help="Volksbank available balance (EUR).")
    parser.add_argument("--revolut-eur", type=float, help="Revolut EUR balance.")
    parser.add_argument("--telekom", type=float, help="Telekom pending outflow (EUR).")
    parser.add_argument("--timestamp", help="Timestamp for current_balances._last_updated (ISO-8601).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    kernel_path = Path(__file__).resolve().parents[1] / "00_CORE_DATA" / "omega_kernel.json"

    with open(kernel_path, "r", encoding="utf-8") as f:
        kernel = json.load(f)

    balances = kernel.get("current_balances", {})
    if args.volksbank is not None:
        balances["volksbank_available"] = round(float(args.volksbank), 2)
    if args.revolut_eur is not None:
        balances["revolut_eur"] = round(float(args.revolut_eur), 2)
    if args.timestamp:
        balances["_last_updated"] = args.timestamp
    else:
        balances["_last_updated"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    telekom = args.telekom
    if telekom is None:
        telekom = float(kernel.get("pending_transactions", {}).get("outflows", {}).get("telekom", {}).get("amount", 0) or 0)

    voba = float(balances.get("volksbank_available", 0) or 0)
    rev = float(balances.get("revolut_eur", 0) or 0)
    net = round(voba + rev - float(telekom), 2)
    balances["net_liquidity"] = net
    balances["calculation"] = "volksbank + revolut_eur - telekom_pending"
    kernel["current_balances"] = balances

    fi = kernel.get("financial_intelligence", {})
    burn = abs(float(fi.get("burn_rate_2025", {}).get("monthly_avg", 0) or 0))
    runway_days = round((net / (burn / 30)) if burn else 0, 2)
    fi["runway_calculation"] = {
        "net_liquidity": net,
        "monthly_burn": round(burn, 2),
        "runway_days": runway_days,
        "next_inflow": fi.get("runway_calculation", {}).get("next_inflow", ""),
    }
    kernel["financial_intelligence"] = fi

    with open(kernel_path, "w", encoding="utf-8") as f:
        json.dump(kernel, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {kernel_path}")
    print(f"   volksbank_available: {voba:.2f}")
    print(f"   revolut_eur:         {rev:.2f}")
    print(f"   telekom_pending:     {float(telekom):.2f}")
    print(f"   net_liquidity:       {net:.2f}")
    print(f"   runway_days:         {runway_days:.2f}")


if __name__ == "__main__":
    main()
