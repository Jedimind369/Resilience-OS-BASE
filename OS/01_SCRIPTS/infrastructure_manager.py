#!/usr/bin/env python3
"""
INFRASTRUCTURE MANAGER: PID-basiertes Prozess-Management für Resilience OS
Löst: Port-Kollisionen, Zombie-Prozesse, sauberes Herunterfahren
Usage:
  python3 infrastructure_manager.py status
  python3 infrastructure_manager.py start dashboard
  python3 infrastructure_manager.py stop watchdog
  python3 infrastructure_manager.py restart all
  python3 infrastructure_manager.py cleanup
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# PFADE
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parents[1]  # Prepper Central root
DATA_DIR = BASE_DIR / "OS" / "00_CORE_DATA"
LOG_DIR = BASE_DIR / "OS" / "logs"
REGISTRY_FILE = DATA_DIR / "service_registry.json"
CONFIG_FILE = DATA_DIR / "ports_config.json"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_registry() -> dict:
    """
    Registry schema (current): dict[name] -> {pid, port, ...}
    Back-compat: if the registry file contains a list, migrate it to dict.
    """
    if not REGISTRY_FILE.exists():
        return {}
    try:
        raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        migrated: dict = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            migrated[str(name)] = {
                "pid": item.get("pid"),
                "port": item.get("port"),
                "start_time": item.get("start_time"),
                "note": item.get("note"),
            }
        save_json(REGISTRY_FILE, migrated)
        return migrated
    return {}


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _can_connect(host: str, port: int, family: int) -> bool:
    try:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            return s.connect_ex((host, int(port))) == 0
    except Exception:
        return False


def is_port_in_use(port: int) -> bool:
    """Prüft, ob ein TCP-Port auf localhost belegt ist."""
    if port is None:
        return False
    # Check IPv4 + IPv6 to catch common macOS cases where another service binds only on ::.
    return _can_connect("127.0.0.1", int(port), socket.AF_INET) or _can_connect("::1", int(port), socket.AF_INET6)


def is_pid_running(pid: int) -> bool:
    """Prüft, ob ein Prozess mit dieser PID noch existiert."""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # Signal 0 prüft nur Existenz
        return True
    except (OSError, ProcessLookupError):
        return False


def get_port_owner(port: int) -> str:
    """Findet den Prozess, der einen Port belegt (via lsof)."""
    if port is None:
        return ""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True,
            timeout=5
        )
        pids = [ln.strip() for ln in (result.stdout or "").splitlines() if ln.strip()]
        # keep stable order, but de-dupe
        seen = set()
        uniq = []
        for p in pids:
            if p in seen:
                continue
            seen.add(p)
            uniq.append(p)
        return ",".join(uniq)
    except Exception:
        return ""

def get_port_owner_pids(port: int) -> set:
    owner = get_port_owner(port)
    pids = set()
    for part in (owner or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            pids.add(int(part))
        except Exception:
            continue
    return pids


def start_service(name: str) -> bool:
    """Startet einen Dienst aus ports_config.json."""
    config = load_json(CONFIG_FILE)
    registry = load_registry()

    if name not in config:
        print(f"❌ Dienst '{name}' nicht in ports_config.json gefunden.")
        return False

    svc_cfg = config[name]
    port = svc_cfg.get("port")
    cmd = svc_cfg.get("command", [])
    desc = svc_cfg.get("description", name)

    # Special: dashboard should be started via omega_one_click.py (readiness probes + auto-port).
    if name == "dashboard":
        print("🚀 Starte dashboard via omega_one_click.py (robust)…")
        try:
            subprocess.run(
                [sys.executable, "OS/01_SCRIPTS/omega_one_click.py"],
                cwd=str(BASE_DIR),
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        pidfile = BASE_DIR / "OS" / "logs" / "dashboard_server.pid"
        portfile = BASE_DIR / "OS" / "logs" / "dashboard_server.port"
        pid = None
        try:
            pid = int(pidfile.read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
        picked_port = None
        try:
            picked_port = int(portfile.read_text(encoding="utf-8").strip())
        except Exception:
            picked_port = port
        registry["dashboard"] = {
            "pid": pid,
            "port": picked_port,
            "command": ["python3", "OS/01_SCRIPTS/omega_one_click.py"],
            "start_time": datetime.now().isoformat(),
            "note": "managed_by_omega_one_click",
        }
        save_json(REGISTRY_FILE, registry)
        print(f"✅ dashboard ready (pid={pid or '--'} port={picked_port or '--'})")
        return True

    # Special: watchdog is managed via launchd (power_watchdog_ctl), not by spawning a second copy.
    if name == "watchdog":
        print("🚀 Starte watchdog via power_watchdog_ctl.py (launchd)…")
        payload = {}
        ok = False
        try:
            proc = subprocess.run(
                [sys.executable, "OS/01_SCRIPTS/power_watchdog_ctl.py", "start"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
            )
            out = (proc.stdout or "").strip()
            payload = json.loads(out) if out.startswith("{") else {}
            ok = bool(payload.get("ok"))
        except Exception:
            payload = {}
            ok = False
        registry["watchdog"] = {
            "pid": None,
            "port": None,
            "command": ["python3", "OS/01_SCRIPTS/power_watchdog_ctl.py", "start"],
            "start_time": datetime.now().isoformat(),
            "note": "managed_by_launchd",
            "last": payload,
        }
        save_json(REGISTRY_FILE, registry)
        print("✅ watchdog start issued" if ok else "⚠️ watchdog start may have failed (check watchdog stderr log)")
        return ok

    # 1. Check: Läuft er schon laut Registry?
    if name in registry:
        old_pid = registry[name].get("pid")
        if is_pid_running(old_pid):
            print(f"⚠️  {name} läuft bereits (PID {old_pid}).")
            return True
        else:
            print(f"🧹 Bereinige toten Eintrag für '{name}'...")
            del registry[name]
            save_json(REGISTRY_FILE, registry)

    # 2. Check: Ist der Port blockiert?
    if port and is_port_in_use(port):
        owner = get_port_owner(port)
        print(f"⛔ Port {port} ist belegt! (PID: {owner or 'unbekannt'})")
        print(f"   Tipp: kill {owner} oder wähle anderen Port.")
        return False

    # 3. Starten
    print(f"🚀 Starte {name} ({desc})...")
    log_file_path = LOG_DIR / f"{name}.log"
    
    try:
        log_file = open(log_file_path, "a", encoding="utf-8")
        log_file.write(f"\n=== START {datetime.now().isoformat()} ===\n")
        log_file.flush()

        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True  # Detach from terminal
        )

        # Kurz warten und prüfen, ob Prozess sofort crashed
        time.sleep(0.5)
        if proc.poll() is not None:
            print(f"❌ {name} ist sofort gecrasht! Check {log_file_path}")
            return False

        # 4. Registrieren
        registry[name] = {
            "pid": proc.pid,
            "port": port,
            "command": cmd,
            "start_time": datetime.now().isoformat(),
            "log_file": str(log_file_path)
        }
        save_json(REGISTRY_FILE, registry)
        
        if port:
            print(f"✅ {name} gestartet (PID {proc.pid}, Port {port}).")
        else:
            print(f"✅ {name} gestartet (PID {proc.pid}).")
        return True

    except FileNotFoundError as e:
        print(f"❌ Befehl nicht gefunden: {cmd[0]}")
        print(f"   Details: {e}")
        return False
    except Exception as e:
        print(f"❌ Fehler beim Starten: {e}")
        return False


def stop_service(name: str, force: bool = False) -> bool:
    """Stoppt einen Dienst sauber (SIGTERM, dann SIGKILL)."""
    registry = load_registry()

    if name == "dashboard":
        pidfile = BASE_DIR / "OS" / "logs" / "dashboard_server.pid"
        portfile = BASE_DIR / "OS" / "logs" / "dashboard_server.port"
        pid = None
        try:
            pid = int(pidfile.read_text(encoding="utf-8").strip())
        except Exception:
            pid = registry.get("dashboard", {}).get("pid")
        print(f"🛑 Stoppe dashboard (pid={pid or '--'})…")
        if pid and is_pid_running(int(pid)):
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
        for p in (pidfile, portfile):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        if "dashboard" in registry:
            del registry["dashboard"]
            save_json(REGISTRY_FILE, registry)
        print("✅ dashboard gestoppt (best-effort).")
        return True

    if name == "watchdog":
        print("🛑 Stoppe watchdog via power_watchdog_ctl.py (launchd)…")
        try:
            subprocess.run(
                [sys.executable, "OS/01_SCRIPTS/power_watchdog_ctl.py", "stop"],
                cwd=str(BASE_DIR),
                check=False,
                timeout=20,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        if "watchdog" in registry:
            del registry["watchdog"]
            save_json(REGISTRY_FILE, registry)
        print("✅ watchdog stop issued.")
        return True

    if name not in registry:
        print(f"ℹ️  Dienst '{name}' ist nicht registriert.")
        return True

    pid = registry[name].get("pid")
    print(f"🛑 Stoppe {name} (PID {pid})...")

    if is_pid_running(pid):
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            
            # Grace period
            for _ in range(10):
                time.sleep(0.3)
                if not is_pid_running(pid):
                    break
            
            if is_pid_running(pid) and not force:
                print("   ...reagiert nicht auf SIGTERM, erzwinge SIGKILL.")
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
                
        except ProcessLookupError:
            pass  # Already dead
        except Exception as e:
            print(f"⚠️  Fehler beim Stoppen: {e}")

    del registry[name]
    save_json(REGISTRY_FILE, registry)
    print(f"✅ {name} gestoppt.")
    return True


def restart_service(name: str) -> bool:
    """Stoppt und startet einen Dienst neu."""
    stop_service(name)
    time.sleep(1)
    return start_service(name)


def status() -> None:
    """Zeigt den Status aller registrierten Dienste."""
    registry = load_registry()
    config = load_json(CONFIG_FILE)
    
    print(f"\n{'='*60}")
    print(f"📊 INFRASTRUCTURE STATUS ({datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*60}")
    print(f"{'SERVICE':<15} {'PID':<8} {'PORT':<8} {'STATUS':<12} {'UPTIME'}")
    print("-" * 60)

    def dashboard_runtime():
        pidfile = BASE_DIR / "OS" / "logs" / "dashboard_server.pid"
        portfile = BASE_DIR / "OS" / "logs" / "dashboard_server.port"
        pid = None
        port = None
        try:
            pid = int(pidfile.read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
        try:
            port = int(portfile.read_text(encoding="utf-8").strip())
        except Exception:
            port = None
        alive = is_pid_running(pid) if pid else False
        return pid, port, alive

    def watchdog_runtime():
        try:
            proc = subprocess.run(
                [sys.executable, "OS/01_SCRIPTS/power_watchdog_ctl.py", "status"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            payload = json.loads((proc.stdout or "").strip() or "{}")
            return bool(payload.get("loaded"))
        except Exception:
            return False

    # Prefer config order (the "source of truth" for what exists).
    for name, cfg in (config.items() if isinstance(config, dict) else []):
        if name == "dashboard":
            pid, port, alive = dashboard_runtime()
            state = "🟢 RUNNING" if alive else "⚫ STOPPED"
            print(f"{name:<15} {(pid or '-'): <8} {(port or '-'): <8} {state:<12} -")
            # Sync registry to the actual pid/port files (avoids stale manual entries).
            try:
                registry["dashboard"] = {
                    "pid": pid,
                    "port": port,
                    "start_time": registry.get("dashboard", {}).get("start_time"),
                    "note": "synced_from_pidfile",
                }
                save_json(REGISTRY_FILE, registry)
            except Exception:
                pass
            continue
        if name == "watchdog":
            alive = watchdog_runtime()
            state = "🟢 RUNNING" if alive else "⚫ STOPPED"
            print(f"{name:<15} {'-':<8} {'-':<8} {state:<12} -")
            continue

        info = registry.get(name) if isinstance(registry, dict) else None
        managed = isinstance(cfg, dict) and cfg.get("managed") is not False
        if isinstance(info, dict) and info.get("pid") is not None:
            pid = info.get("pid")
            port = info.get("port") or "-"
            alive = is_pid_running(pid)
            state = "🟢 RUNNING" if alive else ("🔴 DEAD" if managed else "⚪ EXTERNAL")
            print(f"{name:<15} {pid:<8} {port:<8} {state:<12} -")
        else:
            port = (cfg.get("port") if isinstance(cfg, dict) else None) or "-"
            label = "⚫ STOPPED" if managed else "⚪ EXTERNAL"
            print(f"{name:<15} {'-':<8} {port:<8} {label:<12} -")

    print("-" * 60)
    
    # Prüfe auf Port-Konflikte
    conflicts = []
    for name, cfg in (config.items() if isinstance(config, dict) else []):
        if isinstance(cfg, dict) and cfg.get("managed") is False:
            continue
        port = cfg.get("port")
        if not port:
            continue
        if not is_port_in_use(port):
            continue

        owner_pids = get_port_owner_pids(port)

        if name == "dashboard":
            # Only warn if the port is owned by someone else (not our dashboard pid).
            pid, picked_port, alive = dashboard_runtime()
            if alive and picked_port == port and pid and pid in owner_pids:
                continue
            conflicts.append((name, port, ",".join(str(p) for p in sorted(owner_pids)) or get_port_owner(port)))
            continue

        info = registry.get(name, {}) if isinstance(registry, dict) else {}
        reg_pid = info.get("pid")
        if reg_pid and is_pid_running(reg_pid) and int(reg_pid) in owner_pids:
            continue

        # If service isn't running (or unknown), but port is used, it is a real conflict.
        if not reg_pid or not is_pid_running(reg_pid):
            conflicts.append((name, port, ",".join(str(p) for p in sorted(owner_pids)) or get_port_owner(port)))
    
    if conflicts:
        print("\n⚠️  PORT-KONFLIKTE:")
        for name, port, owner in conflicts:
            print(f"   {name}: Port {port} belegt von PID {owner}")


def cleanup() -> None:
    """Bereinigt tote Einträge aus der Registry und alte Logs."""
    registry = load_registry()
    cleaned = 0
    
    for name in list(registry.keys()):
        pid = registry[name].get("pid")
        if not is_pid_running(pid):
            print(f"🧹 Entferne toten Eintrag: {name} (PID {pid})")
            del registry[name]
            cleaned += 1
    
    save_json(REGISTRY_FILE, registry)
    
    # Alte Logs löschen (> 7 Tage)
    old_logs = 0
    cutoff = time.time() - (7 * 24 * 3600)
    for log_file in LOG_DIR.glob("*.log"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
            old_logs += 1
    
    print(f"✅ Cleanup: {cleaned} tote Einträge, {old_logs} alte Logs gelöscht.")


def start_all() -> None:
    """Startet alle Dienste aus der Konfiguration."""
    config = load_json(CONFIG_FILE)
    for name, cfg in config.items():
        if isinstance(cfg, dict) and cfg.get("managed") is False:
            continue
        start_service(name)


def stop_all() -> None:
    """Stoppt alle registrierten Dienste."""
    config = load_json(CONFIG_FILE)
    if isinstance(config, dict):
        targets = [name for name, cfg in config.items() if not (isinstance(cfg, dict) and cfg.get("managed") is False)]
    else:
        targets = []
    for name in targets:
        stop_service(name)


def print_usage() -> None:
    print("""
INFRASTRUCTURE MANAGER - Resilience OS
=======================================
Usage:
  python3 infrastructure_manager.py status           # Zeige alle Dienste
  python3 infrastructure_manager.py start <name>     # Starte Dienst
  python3 infrastructure_manager.py stop <name>      # Stoppe Dienst
  python3 infrastructure_manager.py restart <name>   # Restart Dienst
  python3 infrastructure_manager.py start all        # Starte alle
  python3 infrastructure_manager.py stop all         # Stoppe alle
  python3 infrastructure_manager.py cleanup          # Bereinige tote Einträge

Dienste werden in ports_config.json definiert.
PIDs werden in service_registry.json gespeichert.
Logs liegen in OS/logs/<name>.log
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        status()
        sys.exit(0)

    action = sys.argv[1].lower()
    target = sys.argv[2].lower() if len(sys.argv) > 2 else None

    if action == "status":
        status()
    elif action == "cleanup":
        cleanup()
    elif action == "start":
        if target == "all":
            start_all()
        elif target:
            start_service(target)
        else:
            print("❌ Service Name fehlt. Beispiel: start dashboard")
    elif action == "stop":
        if target == "all":
            stop_all()
        elif target:
            stop_service(target)
        else:
            print("❌ Service Name fehlt.")
    elif action == "restart":
        if target == "all":
            stop_all()
            time.sleep(1)
            start_all()
        elif target:
            restart_service(target)
        else:
            print("❌ Service Name fehlt.")
    elif action in ["-h", "--help", "help"]:
        print_usage()
    else:
        print(f"❌ Unbekannte Aktion: {action}")
        print_usage()
