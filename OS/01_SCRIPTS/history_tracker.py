#!/usr/bin/env python3
"""
HISTORY TRACKER: Finanz-Zeitmaschine für Resilience OS
Speichert tägliche Snapshots und berechnet Trends (vs. Gestern).
"""

import json
import os
import datetime
from pathlib import Path

# PFADE (relativ zum Skript-Verzeichnis)
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
KERNEL_PATH = BASE_DIR / "00_CORE_DATA" / "omega_kernel.json"
HISTORY_PATH = BASE_DIR / "00_CORE_DATA" / "metrics_history.json"

def load_json(path):
    """Lädt JSON-Datei sicher."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(path, data):
    """Speichert JSON-Datei mit Indent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_metrics(kernel):
    """Extrahiert die wichtigsten Metriken aus dem Kernel."""
    balances = kernel.get("current_balances", {})
    runway_calc = kernel.get("financial_intelligence", {}).get("runway_calculation", {})
    
    return {
        "net_liquidity": balances.get("net_liquidity", 0),
        "volksbank": balances.get("volksbank_available", 0),
        "revolut": balances.get("revolut_eur", 0),
        "runway_days": runway_calc.get("runway_days", 0),
        "burn_rate": runway_calc.get("monthly_burn", 0),
    }

def _metrics_equal(a, b):
    keys = ["net_liquidity", "volksbank", "revolut", "runway_days", "burn_rate"]
    try:
        return all(a.get(k) == b.get(k) for k in keys)
    except Exception:
        return False

def update_history():
    """
    Macht einen Snapshot der aktuellen Werte.
    Ersetzt existing entry für heute, falls vorhanden.
    Behält maximal 30 Tage History.
    """
    kernel = load_json(KERNEL_PATH)
    history_data = load_json(HISTORY_PATH)
    
    # Ensure history is a list
    if not isinstance(history_data, list):
        history_data = []
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().isoformat()
    
    # Aktuelle Werte extrahieren
    metrics = extract_metrics(kernel)
    snapshot = {"date": today, "timestamp": timestamp, **metrics}

    # Heute nur schreiben, wenn nötig (daily snapshot, nicht jede Minute).
    existing_today = None
    for h in history_data:
        if h.get("date") == today:
            existing_today = h
            break

    force = os.environ.get("OMEGA_FORCE_SNAPSHOT") == "1"
    if existing_today and not force:
        if _metrics_equal(existing_today, snapshot):
            return history_data
        # metrics changed -> replace
        history_data = [h for h in history_data if h.get("date") != today]
        history_data.append(snapshot)
    else:
        # no entry today yet OR forced
        history_data = [h for h in history_data if h.get("date") != today]
        history_data.append(snapshot)

    # Nach Datum sortieren und auf 30 Tage begrenzen
    history_data = sorted(history_data, key=lambda x: x.get("date", ""))[-30:]
    
    save_json(HISTORY_PATH, history_data)
    return history_data

def calc_trend(current, previous):
    """Berechnet prozentuale Änderung."""
    if previous == 0:
        return 0 if current == 0 else 100.0
    return round(((current - previous) / abs(previous)) * 100, 1)

def get_trends():
    """
    Vergleicht Heute vs. Gestern (oder letzten verfügbaren Tag).
    Ruft update_history() auf, um sicherzustellen dass Heute drin ist.
    """
    history = update_history()
    
    # Default Trends (noch keine History)
    default_trends = {
        "runway_trend": 0,
        "liquidity_trend": 0,
        "days_of_data": len(history),
        "comparison_date": None
    }
    
    if len(history) < 2:
        return default_trends
    
    current = history[-1]
    previous = history[-2]
    
    return {
        "runway_trend": calc_trend(
            current.get("runway_days", 0), 
            previous.get("runway_days", 0)
        ),
        "liquidity_trend": calc_trend(
            current.get("net_liquidity", 0), 
            previous.get("net_liquidity", 0)
        ),
        "days_of_data": len(history),
        "comparison_date": previous.get("date"),
        "current_date": current.get("date")
    }

def get_history_summary():
    """Gibt eine kompakte Zusammenfassung der History zurück."""
    history = load_json(HISTORY_PATH)
    if not isinstance(history, list) or not history:
        return {"status": "empty", "entries": 0}
    
    return {
        "status": "ok",
        "entries": len(history),
        "oldest": history[0].get("date") if history else None,
        "newest": history[-1].get("date") if history else None,
        "latest_snapshot": history[-1] if history else None
    }

if __name__ == "__main__":
    print("=== History Tracker ===")
    print(f"Kernel: {KERNEL_PATH}")
    print(f"History: {HISTORY_PATH}")
    print()
    
    trends = get_trends()
    print("Trends (vs. Gestern):")
    print(json.dumps(trends, indent=2, ensure_ascii=False))
    
    print()
    summary = get_history_summary()
    print("History Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
