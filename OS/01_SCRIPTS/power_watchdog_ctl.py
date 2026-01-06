#!/usr/bin/env python3
"""
Power Watchdog Control (offline-first, stdlib-only)
===================================================
Installs/starts/stops the LaunchAgent for the Power Watchdog and provides status.

This script intentionally avoids "silent deletion" from the dashboard; actions are
explicit and reversible.

Usage:
  python3 OS/01_SCRIPTS/power_watchdog_ctl.py status
  python3 OS/01_SCRIPTS/power_watchdog_ctl.py plan
  python3 OS/01_SCRIPTS/power_watchdog_ctl.py install
  python3 OS/01_SCRIPTS/power_watchdog_ctl.py start
  python3 OS/01_SCRIPTS/power_watchdog_ctl.py stop
  python3 OS/01_SCRIPTS/power_watchdog_ctl.py uninstall
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


LABEL = "com.resilience-os.power-watchdog"

SCRIPT_DIR = Path(__file__).resolve().parent
OS_DIR = SCRIPT_DIR.parent
ROOT = OS_DIR.parent

TEMPLATE = OS_DIR / "com.resilience-os.power-watchdog.plist"
AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
INSTALLED = AGENTS_DIR / TEMPLATE.name

APP_SUPPORT = Path.home() / "Library" / "Application Support"
RUNTIME_HOME = APP_SUPPORT / "ResilienceOS" / "power_watchdog"
RUNTIME_HOME.mkdir(parents=True, exist_ok=True)

RUNTIME_SCRIPT = RUNTIME_HOME / "power_watchdog_service.py"
RUNTIME_CONFIG = RUNTIME_HOME / "power_watchdog_config.json"
RUNTIME_STATUS = RUNTIME_HOME / "status.json"
RUNTIME_LOG = RUNTIME_HOME / "power_watchdog.log"
RUNTIME_STDOUT = RUNTIME_HOME / "stdout.log"
RUNTIME_STDERR = RUNTIME_HOME / "stderr.log"

WATCHDOG_HOME_ENV = "RESILIENCE_WATCHDOG_HOME"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = (proc.stdout or "") + (proc.stderr or "")
        return int(proc.returncode), out.strip()
    except Exception as exc:
        return 1, str(exc)


def launchctl_list() -> str:
    _, out = run(["launchctl", "list"])
    return out


def is_loaded() -> bool:
    out = launchctl_list()
    return LABEL in out


def plan_commands() -> List[str]:
    return [
        f"python3 {ROOT}/OS/01_SCRIPTS/power_watchdog_ctl.py install",
        f"python3 {ROOT}/OS/01_SCRIPTS/power_watchdog_ctl.py start",
        f"python3 {ROOT}/OS/01_SCRIPTS/power_watchdog_ctl.py status",
        f"python3 {ROOT}/OS/01_SCRIPTS/power_watchdog_ctl.py stop",
        f"python3 {ROOT}/OS/01_SCRIPTS/power_watchdog_ctl.py uninstall",
    ]


def install() -> Dict[str, Any]:
    """
    Installs a LaunchAgent that runs from a TCC-safe location.
    Rationale: launchd jobs can be blocked from reading ~/Downloads ("Operation not permitted").
    """
    service_src = ROOT / "OS" / "01_SCRIPTS" / "power_watchdog_service.py"
    config_src = ROOT / "OS" / "00_CORE_DATA" / "power_watchdog_config.json"
    if not service_src.exists():
        return {"ok": False, "error": "missing_service", "path": str(service_src)}

    # Copy service + config into Application Support so launchd can read it.
    try:
        RUNTIME_HOME.mkdir(parents=True, exist_ok=True)
        RUNTIME_SCRIPT.write_text(service_src.read_text(encoding="utf-8"), encoding="utf-8")
        if config_src.exists():
            RUNTIME_CONFIG.write_text(config_src.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            # Minimal default config if repo config is missing.
            RUNTIME_CONFIG.write_text(json.dumps({"enabled": True, "sources": []}, indent=2), encoding="utf-8")
    except Exception as exc:
        return {"ok": False, "error": f"copy_failed: {exc}"}

    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>{LABEL}</string>

    <key>ProgramArguments</key>
    <array>
      <string>/usr/bin/python3</string>
      <string>{str(RUNTIME_SCRIPT)}</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
      <key>{WATCHDOG_HOME_ENV}</key>
      <string>{str(RUNTIME_HOME)}</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>WorkingDirectory</key>
    <string>{str(RUNTIME_HOME)}</string>

    <key>StandardOutPath</key>
    <string>{str(RUNTIME_STDOUT)}</string>
    <key>StandardErrorPath</key>
    <string>{str(RUNTIME_STDERR)}</string>
  </dict>
</plist>
"""
    INSTALLED.write_text(plist, encoding="utf-8")
    return {"ok": True, "installed": str(INSTALLED), "runtime_home": str(RUNTIME_HOME), "runtime_script": str(RUNTIME_SCRIPT)}


def start() -> Dict[str, Any]:
    if not INSTALLED.exists():
        res = install()
        if not res.get("ok"):
            return res
    # Ensure we reload to pick up updated plist/runtime paths.
    if is_loaded():
        run(["launchctl", "unload", str(INSTALLED)])
    code, out = run(["launchctl", "load", str(INSTALLED)])
    return {"ok": code == 0, "action": "start", "code": code, "output": out, "runtime_home": str(RUNTIME_HOME)}


def stop() -> Dict[str, Any]:
    if not INSTALLED.exists():
        return {"ok": True, "action": "stop", "note": "not_installed"}
    code, out = run(["launchctl", "unload", str(INSTALLED)])
    return {"ok": code == 0, "action": "stop", "code": code, "output": out}


def uninstall() -> Dict[str, Any]:
    stop()
    try:
        if INSTALLED.exists():
            INSTALLED.unlink()
        return {"ok": True, "action": "uninstall", "removed": str(INSTALLED)}
    except Exception as exc:
        return {"ok": False, "action": "uninstall", "error": str(exc)}


def status() -> Dict[str, Any]:
    return {
        "ok": True,
        "time": now_iso(),
        "label": LABEL,
        "installed": INSTALLED.exists(),
        "installed_path": str(INSTALLED),
        "loaded": is_loaded(),
        "runtime_home": str(RUNTIME_HOME),
        "runtime_script": str(RUNTIME_SCRIPT),
        "config_file": str(RUNTIME_CONFIG),
        "status_file": str(RUNTIME_STATUS),
        "log_file": str(RUNTIME_LOG),
        "stdout_file": str(RUNTIME_STDOUT),
        "stderr_file": str(RUNTIME_STDERR),
        "last_status": safe_read_json(RUNTIME_STATUS) if RUNTIME_STATUS.exists() else {},
        "plan_commands": plan_commands(),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps(status(), indent=2, ensure_ascii=False))
        return
    cmd = sys.argv[1].lower()
    if cmd == "plan":
        print(json.dumps({"ok": True, "plan_commands": plan_commands()}, indent=2, ensure_ascii=False))
        return
    if cmd == "install":
        print(json.dumps(install(), indent=2, ensure_ascii=False))
        return
    if cmd == "start":
        print(json.dumps(start(), indent=2, ensure_ascii=False))
        return
    if cmd == "stop":
        print(json.dumps(stop(), indent=2, ensure_ascii=False))
        return
    if cmd == "uninstall":
        print(json.dumps(uninstall(), indent=2, ensure_ascii=False))
        return
    if cmd == "status":
        print(json.dumps(status(), indent=2, ensure_ascii=False))
        return
    raise SystemExit("Usage: power_watchdog_ctl.py [plan|install|start|stop|uninstall|status]")


if __name__ == "__main__":
    main()
