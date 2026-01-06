#!/usr/bin/env python3
"""
CONTEXT LOADER: Baut den System-Prompt für lokale LLMs zusammen.
Kopiert Identity + Ports + Rules in die Zwischenablage für schnelles Einfügen.

Usage:
  python3 load_context.py         # Kopiert Context in Zwischenablage
  python3 load_context.py --print # Gibt Context auf stdout aus
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

# PFADE
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parents[1]  # Prepper Central root
CORE_DIR = BASE_DIR / "OS" / "00_CORE_DATA"
CRISIS_DIR = BASE_DIR / "OS" / "06_CRISIS"
REPORTS_DIR = BASE_DIR / "OS" / "03_REPORTS"
LOGS_DIR = BASE_DIR / "OS" / "logs"


def read_file(path: Path) -> str:
    """Liest eine Datei sicher."""
    if not path.exists():
        return f"(file not found: {path.name})"
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as e:
        return f"(error reading {path.name}: {e})"


def read_json_pretty(path: Path) -> str:
    """Liest JSON und formatiert es schön."""
    if not path.exists():
        return f"(file not found: {path.name})"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"(error reading {path.name}: {e})"


def copy_to_clipboard(text: str) -> bool:
    """Kopiert Text in die macOS Zwischenablage."""
    try:
        process = subprocess.Popen(
            'pbcopy',
            env={'LANG': 'en_US.UTF-8'},
            stdin=subprocess.PIPE
        )
        process.communicate(text.encode('utf-8'))
        return process.returncode == 0
    except Exception:
        return False


def read_portfile() -> int:
    try:
        raw = (LOGS_DIR / "dashboard_server.port").read_text(encoding="utf-8").strip()
        port = int(raw)
        return port if 1 <= port <= 65535 else 3000
    except Exception:
        return 3000


def fetch_new_chat_pack(port: int) -> Optional[str]:
    url = f"http://127.0.0.1:{int(port)}/api/new_chat_pack"
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=2) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        text = data.get("text")
        return str(text) if text else None
    except Exception:
        return None


def session_log_tail(max_entries: int = 10) -> str:
    try:
        path = REPORTS_DIR / "SESSION_LOG.md"
        if not path.exists():
            return "(no session log yet)"
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        entries = [ln for ln in lines if ln.startswith("- [")]
        tail = entries[-max_entries:] if entries else []
        return "\n".join(tail) if tail else "(no entries yet)"
    except Exception as exc:
        return f"(session log unavailable: {exc})"


def kernel_extract() -> str:
    path = CORE_DIR / "omega_kernel.json"
    if not path.exists():
        return "(file not found: omega_kernel.json)"
    try:
        kernel: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        balances = kernel.get("current_balances", {}) or {}
        runway = (kernel.get("financial_intelligence", {}) or {}).get("runway_calculation", {}) or {}
        extract = {"current_balances": balances, "runway_calculation": runway}
        return json.dumps(extract, indent=2, ensure_ascii=False)
    except Exception as exc:
        return f"(kernel parsing failed: {exc})"


def build_context() -> str:
    """Baut den vollständigen System-Kontext zusammen."""

    port = read_portfile()
    dashboard_url = f"http://127.0.0.1:{int(port)}"
    new_chat_pack = fetch_new_chat_pack(port)

    profile = read_json_pretty(CORE_DIR / "profile.json")
    offline_state = read_json_pretty(CORE_DIR / "offline_state.json")
    ports = read_json_pretty(CORE_DIR / "ports_config.json")
    offline_min = read_file(CRISIS_DIR / "OFFLINE_CONTEXT_MIN.txt")
    memory_min = read_file(CRISIS_DIR / "MEMORY_INDEX_MIN.txt")
    master_min = read_file(CRISIS_DIR / "MASTER_START_MIN.txt")
    sess_tail = session_log_tail(max_entries=10)
    kernel_summary = kernel_extract()
    
    # Zusammenbauen
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    prompt = f"""
================================================================================
 RESILIENCE OS - SYSTEM CONTEXT PACKAGE
 Generated: {timestamp}
================================================================================

[DASHBOARD]
- URL: {dashboard_url}
- Portfile: OS/logs/dashboard_server.port

--------------------------------------------------------------------------------

[NEW CHAT PACK (MIN) - preferred]
{new_chat_pack if new_chat_pack else "(dashboard not reachable: run OMEGA_ONE_CLICK.command)"}

--------------------------------------------------------------------------------

[PROFILE (Evidence-first)]
{profile}

--------------------------------------------------------------------------------

[OFFLINE STATE]
{offline_state}

--------------------------------------------------------------------------------

[INFRASTRUCTURE / PORTS]
{ports}

--------------------------------------------------------------------------------

[FINANCIAL STATUS (KERNEL EXTRACT)]
{kernel_summary}

--------------------------------------------------------------------------------

[CRISIS STATUS (MIN)]
{offline_min}

--------------------------------------------------------------------------------

[MEMORY INDEX (MIN)]
{memory_min}

--------------------------------------------------------------------------------

[SESSION LOG (tail)]
{sess_tail}

--------------------------------------------------------------------------------

[MASTER START (MIN)]
{master_min}

================================================================================
 END CONTEXT - Paste this at the start of a new AI chat
================================================================================
"""
    return prompt.strip()


def main():
    context = build_context()
    
    if "--print" in sys.argv:
        print(context)
    else:
        if copy_to_clipboard(context):
            print("✅ System Context in Zwischenablage kopiert.")
            print(f"   Größe: {len(context):,} Zeichen")
            print("👉 Einfügen in: DeepSeek / Llama / ChatGPT / Claude")
        else:
            print("❌ Zwischenablage nicht verfügbar. Hier ist der Context:\n")
            print(context)


if __name__ == "__main__":
    main()
