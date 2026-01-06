#!/usr/bin/env python3
"""
OMEGA One-Click Launcher (offline-first)

What it does:
1) Refresh offline brain status (thin-model readiness)
2) Ensure the dashboard server is running and open it in the browser
3) Trigger a background refresh run (KPI snapshot + council audit) so the UI shows progress immediately
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def resolve_paths() -> dict:
    scripts_dir = Path(__file__).resolve().parent
    os_dir = scripts_dir.parent
    root_dir = os_dir.parent
    logs = os_dir / "logs"
    return {
        "ROOT": root_dir,
        "OS_DIR": os_dir,
        "SCRIPTS": scripts_dir,
        "LOGS": logs,
        "DASHBOARD_SERVER": scripts_dir / "dashboard_server.py",
        "META_ORCH": scripts_dir / "meta_orchestrator.py",
        "OFFLINE_BRAIN_CHECK": scripts_dir / "offline_brain_check.py",
        "PIDFILE": logs / "dashboard_server.pid",
        "PORTFILE": logs / "dashboard_server.port",
        "SERVER_LOG": logs / "dashboard_server.log",
    }


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except Exception:
        return False
    return True


def dashboard_ready(url: str) -> bool:
    """
    Verify the running server exposes the expected API surface.
    This prevents "stale" servers from keeping old endpoints alive.
    """
    try:
        for ep in (
            "/api/capabilities",
            "/api/run_status",
            "/api/ai_status",
            "/api/memory_index",
            "/api/sources_coverage",
            "/api/storage_status",
            "/api/new_chat_pack",
            "/api/trends",
        ):
            req = Request(url + ep, method="GET")
            with urlopen(req, timeout=2) as resp:
                if getattr(resp, "status", 200) != 200:
                    return False
        return True
    except (HTTPError, URLError, TimeoutError, ValueError):
        return False
    except Exception:
        return False


def trigger_run_once(url: str) -> bool:
    try:
        req = Request(url + "/api/run_once", method="GET")
        with urlopen(req, timeout=3) as resp:
            return getattr(resp, "status", 200) == 200
    except Exception:
        return False


def find_dashboard_server_pids() -> list[int]:
    """
    Best-effort: find running dashboard_server.py processes even if the pidfile is stale/missing.
    """
    try:
        out = subprocess.check_output(["ps", "ax", "-o", "pid=,command="], text=True)
    except Exception:
        return []
    pids: list[int] = []
    for line in out.splitlines():
        if "dashboard_server.py" not in line:
            continue
        if "OS/01_SCRIPTS/dashboard_server.py" not in line and "dashboard_server.py" not in line:
            continue
        parts = line.strip().split(maxsplit=1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except Exception:
            continue
        if pid > 0:
            pids.append(pid)
    return sorted(set(pids))

def _can_connect(host: str, port: int, family: int) -> bool:
    try:
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((host, int(port))) == 0
    except Exception:
        return False

def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """
    macOS quirk: another process can bind only on IPv6 (::) while IPv4 bind still succeeds.
    Treat the port as "busy" if either 127.0.0.1 or ::1 accepts connections.
    """
    if _can_connect("127.0.0.1", int(port), socket.AF_INET) or _can_connect("::1", int(port), socket.AF_INET6):
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, int(port)))
            return True
    except Exception:
        return False

def pick_port(preferred: int = 3000, max_tries: int = 25) -> int:
    env = os.environ.get("OMEGA_DASHBOARD_PORT")
    if env:
        try:
            cand = int(env)
            if 1 <= cand <= 65535 and is_port_free(cand):
                return cand
        except Exception:
            pass
    start = int(preferred)
    for i in range(max_tries):
        cand = start + i
        if is_port_free(cand):
            return cand
    # Worst-case fallback: let the server fail loudly.
    return int(preferred)

def read_portfile(paths: dict) -> Optional[int]:
    try:
        if paths.get("PORTFILE") and Path(paths["PORTFILE"]).exists():
            raw = Path(paths["PORTFILE"]).read_text(encoding="utf-8").strip()
            port = int(raw)
            if 1 <= port <= 65535:
                return port
    except Exception:
        return None
    return None

def write_portfile(paths: dict, port: int) -> None:
    try:
        Path(paths["PORTFILE"]).write_text(str(int(port)), encoding="utf-8")
    except Exception:
        pass

def ensure_dashboard_server(paths: dict, port: int) -> int:
    paths["LOGS"].mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{int(port)}"

    if paths["PIDFILE"].exists():
        try:
            pid = int(paths["PIDFILE"].read_text(encoding="utf-8").strip())
        except Exception:
            pid = -1
        if pid > 0 and is_pid_running(pid):
            # If the stored PID is alive, trust the stored portfile first (if any).
            stored_port = read_portfile(paths) or port
            stored_url = f"http://127.0.0.1:{int(stored_port)}"
            if dashboard_ready(stored_url):
                return pid
            try:
                os.kill(pid, 15)
            except Exception:
                pass
            time.sleep(0.4)
        try:
            paths["PIDFILE"].unlink()
        except Exception:
            pass
        try:
            paths["PORTFILE"].unlink()
        except Exception:
            pass

    # If something else is already serving the dashboard correctly, don't spawn a duplicate.
    if dashboard_ready(url):
        return -1

    # If the port is occupied by an older dashboard_server.py (not tracked by pidfile), replace it.
    stale_pids = find_dashboard_server_pids()
    if stale_pids:
        for pid in stale_pids:
            try:
                os.kill(pid, 15)
            except Exception:
                pass
        time.sleep(0.6)

    # If the port is taken by a different process (e.g. node on 3000), pick a free one.
    if not is_port_free(port):
        port = pick_port(preferred=port)
        url = f"http://127.0.0.1:{int(port)}"

    with open(paths["SERVER_LOG"], "a", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, str(paths["DASHBOARD_SERVER"]), "--port", str(int(port))],
            stdout=log,
            stderr=log,
            cwd=str(paths["ROOT"]),
        )
    paths["PIDFILE"].write_text(str(proc.pid), encoding="utf-8")
    write_portfile(paths, port)
    return int(proc.pid)


def main() -> None:
    paths = resolve_paths()
    port = pick_port(preferred=3000)
    url = f"http://127.0.0.1:{int(port)}"

    # Fast prep (ensures OS/06_CRISIS/MODELS and offline_brain.json are up to date).
    try:
        subprocess.run([sys.executable, str(paths["OFFLINE_BRAIN_CHECK"])], check=False)
    except Exception:
        pass

    pid = ensure_dashboard_server(paths, port)

    # If the server picked a different port (e.g. 3000 was occupied), re-read it.
    resolved_port = read_portfile(paths) or port
    url = f"http://127.0.0.1:{int(resolved_port)}"

    try:
        subprocess.run(["open", url], check=False)
    except Exception:
        pass

    # Trigger a background refresh so the UI updates without waiting for the command to finish.
    # If this fails, the user can always click "Run Refresh" in the dashboard.
    trigger_run_once(url)

    print(f"[ok] dashboard server pid={pid} url={url}")


if __name__ == "__main__":
    main()
