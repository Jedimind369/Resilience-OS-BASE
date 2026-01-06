#!/usr/bin/env python3
"""
OMEGA Dashboard Server (stdlib-only)
Serves a localhost-only dashboard + minimal JSON API.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import shutil
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# History tracking for trends
try:
    from history_tracker import get_trends
except ImportError:
    def get_trends():
        return {"runway_trend": 0, "liquidity_trend": 0, "days_of_data": 0}


def resolve_paths() -> Dict[str, Path]:
    scripts_dir = Path(__file__).resolve().parent
    os_dir = scripts_dir.parent
    core = os_dir / "00_CORE_DATA"
    return {
        "SCRIPTS": scripts_dir,
        "OS_DIR": os_dir,
        "CORE_DATA": core,
        "KERNEL": core / "omega_kernel.json",
        "VALUE_LEDGER": core / "value_ledger.json",
        "OFFLINE_BRAIN": core / "offline_brain.json",
        "CRISIS_PROMPT": os_dir / "06_CRISIS" / "COMPRESSED_SYSTEM_PROMPT.txt",
        "OFFLINE_CONTEXT": os_dir / "06_CRISIS" / "OFFLINE_CONTEXT.txt",
        "OFFLINE_CONTEXT_MIN": os_dir / "06_CRISIS" / "OFFLINE_CONTEXT_MIN.txt",
        "MEMORY_INDEX": core / "memory_index.json",
        "MEMORY_INDEX_MIN": os_dir / "06_CRISIS" / "MEMORY_INDEX_MIN.txt",
        "SOURCES_COVERAGE": core / "sources_coverage.json",
        "DASHBOARD": os_dir / "05_DASHBOARD",
    }


OLLAMA_BASE_URL = "http://localhost:11434"
API_VERSION = "2026-01-05-6"
STALE_AFTER_SECONDS = 900
DEFAULT_PORT = 3000
RUN_STATE = {
    "running": False,
    "started_at": None,
    "ended_at": None,
    "exit_code": None,
    "error": None,
    "log_tail": "",
}
RUN_LOCK = threading.Lock()


def append_session_event(event: str) -> None:
    """
    Append-only log for "what the OS did" so new chats can re-sync fast.
    Stays short and avoids inferring anything about the operator.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "OS" / "03_REPORTS" / "SESSION_LOG.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# SESSION LOG\n\n", encoding="utf-8")
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"- [{stamp}] AUTO: {event.strip()}\n")
    except Exception:
        return


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def read_session_log_tail(max_entries: int = 10) -> str:
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / "OS" / "03_REPORTS" / "SESSION_LOG.md"
        if not path.exists():
            return "(no session log yet)"
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        entries = [ln for ln in lines if ln.startswith("- [")]
        tail = entries[-max_entries:] if entries else []
        return "\n".join(tail) if tail else "(no entries yet)"
    except Exception:
        return "(session log unavailable)"

def build_new_chat_pack(paths: Dict[str, Path]) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    context_min = load_text(paths.get("OFFLINE_CONTEXT_MIN", Path()))
    memory_min = load_text(paths.get("MEMORY_INDEX_MIN", Path()))
    session_tail = read_session_log_tail(max_entries=10)

    parts = [
        "# NEW CHAT PACK (MIN)",
        f"Generated: {now}",
        "",
        "## OFFLINE CONTEXT (MIN)",
        context_min.strip() or "(missing OFFLINE_CONTEXT_MIN.txt)",
        "",
        "## MEMORY INDEX (MIN)",
        memory_min.strip() or "(missing MEMORY_INDEX_MIN.txt)",
        "",
        "## SESSION LOG (tail)",
        session_tail.strip(),
        "",
        "Note: Paste this at the start of a new chat. Keep it short and factual.",
    ]
    return "\n".join(parts).strip() + "\n"


def run_memory_refresh(paths: Dict[str, Path]) -> Dict[str, Any]:
    """
    Runs build_memory_index.py (fast) and returns a structured result.
    """
    script = paths.get("SCRIPTS", Path(__file__).resolve().parent) / "build_memory_index.py"
    if not script.exists():
        return {"ok": False, "error": "missing_build_memory_index", "path": str(script)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(paths.get("OS_DIR", Path(__file__).resolve().parents[1]).parent),
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "memory_index": load_json(paths["MEMORY_INDEX"]) if paths.get("MEMORY_INDEX") else {},
            "min_text": load_text(paths["MEMORY_INDEX_MIN"]) if paths.get("MEMORY_INDEX_MIN") else "",
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_summary_stubs(paths: Dict[str, Path], limit: Optional[int] = None) -> Dict[str, Any]:
    script = paths.get("SCRIPTS", Path(__file__).resolve().parent) / "create_summary_stubs.py"
    if not script.exists():
        return {"ok": False, "error": "missing_create_summary_stubs", "path": str(script)}
    cmd = [sys.executable, str(script)]
    if isinstance(limit, int) and limit > 0:
        cmd.extend(["--limit", str(limit)])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(paths.get("OS_DIR", Path(__file__).resolve().parents[1]).parent))
        payload = {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
        # Best effort: parse JSON stdout
        try:
            payload["result"] = json.loads(proc.stdout) if proc.stdout else {}
        except Exception:
            payload["result"] = {}
        return payload
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def resolve_mission_log_path() -> Path:
    scripts_dir = Path(__file__).resolve().parent
    os_dir = scripts_dir.parent
    return os_dir / "00_CORE_DATA" / "mission_log.json"

def disk_usage(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {"ok": False, "error": "missing", "path": str(path)}
        total, used, free = shutil.disk_usage(str(path))
        return {
            "ok": True,
            "path": str(path),
            "total_bytes": int(total),
            "used_bytes": int(used),
            "free_bytes": int(free),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}

def kiwix_zim_inventory(zim_root: Path = Path("/Volumes/KiwixVault/zim")) -> Dict[str, Any]:
    """
    Fast-ish: only scans for *.zim files (usually a small count) and sums their sizes.
    Supports nested folders like /zim/wikipedia/*.zim.
    """
    try:
        if not zim_root.exists() or not zim_root.is_dir():
            return {"ok": False, "error": "zim_dir_missing", "zim_dir": str(zim_root)}
        zims = [p for p in zim_root.rglob("*.zim") if p.is_file()]
        if not zims:
            return {"ok": True, "zim_dir": str(zim_root), "files": [], "total_bytes": 0, "message": "no_zim_found"}

        total_bytes = 0
        for p in zims:
            try:
                total_bytes += int(p.stat().st_size)
            except Exception:
                pass

        newest = max(zims, key=lambda p: p.stat().st_mtime)
        largest = []
        for p in sorted(zims, key=lambda p: p.stat().st_size, reverse=True)[:12]:
            st = p.stat()
            largest.append(
                {
                    "name": p.name,
                    "relpath": str(p.relative_to(zim_root)),
                    "size_bytes": int(st.st_size),
                    "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                }
            )

        newest_st = newest.stat()
        return {
            "ok": True,
            "zim_dir": str(zim_root),
            "count": len(zims),
            "total_bytes": int(total_bytes),
            "newest": {
                "name": newest.name,
                "relpath": str(newest.relative_to(zim_root)),
                "modified_at": datetime.fromtimestamp(newest_st.st_mtime).isoformat(),
                "size_bytes": int(newest_st.st_size),
            },
            "largest": largest,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "zim_dir": str(zim_root)}

def storage_status() -> Dict[str, Any]:
    kiwix_mount = Path("/Volumes/KiwixVault")
    tm_mount = Path("/Volumes/Jedi_OS_Backup")
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "volumes": {
            "KiwixVault": disk_usage(kiwix_mount),
            "Jedi_OS_Backup": disk_usage(tm_mount),
        },
        "kiwix": {
            "zim_inventory": kiwix_zim_inventory(),
        },
        "notes": [
            "If both volumes show the same free space, they likely share an APFS container (same free-space pool).",
            "Time Machine can grow until the pool is full unless you keep it manual or cap it.",
        ],
    }

def kiwix_download_status(zim_dir: Path = Path("/Volumes/KiwixVault/zim")) -> Dict[str, Any]:
    try:
        if not zim_dir.exists() or not zim_dir.is_dir():
            return {"ok": False, "error": "zim_dir_missing", "zim_dir": str(zim_dir)}
        zims = [p for p in zim_dir.rglob("*.zim") if p.is_file()]
        if not zims:
            return {"ok": True, "zim_dir": str(zim_dir), "files": [], "message": "no_zim_found"}
        newest = max(zims, key=lambda p: p.stat().st_mtime)
        files = []
        for p in sorted(zims, key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
            st = p.stat()
            files.append(
                {
                    "name": p.name,
                    "relpath": str(p.relative_to(zim_dir)),
                    "size_bytes": int(st.st_size),
                    "modified_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                }
            )
        return {
            "ok": True,
            "zim_dir": str(zim_dir),
            "newest": files[0] if files else {"name": newest.name},
            "files": files,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "zim_dir": str(zim_dir)}

def safe_tail(path: Path, max_bytes: int = 12_000) -> str:
    try:
        if not path.exists() or not path.is_file():
            return ""
        data = path.read_bytes()
        if len(data) <= max_bytes:
            return data.decode("utf-8", errors="replace")
        return data[-max_bytes:].decode("utf-8", errors="replace")
    except Exception:
        return ""

def power_watchdog_paths() -> Dict[str, Path]:
    scripts_dir = Path(__file__).resolve().parent
    os_dir = scripts_dir.parent
    return {
        "AGENT_TEMPLATE": os_dir / "com.resilience-os.power-watchdog.plist",
    }

def power_watchdog_status() -> Dict[str, Any]:
    try:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import power_watchdog_ctl  # type: ignore

        status = power_watchdog_ctl.status()
        log_path = Path(str(status.get("log_file") or ""))
        stderr_path = Path(str(status.get("stderr_file") or ""))
        status["log_tail"] = safe_tail(log_path) if log_path else ""
        # If the main log is empty, surface stderr (common when launchd can't read files).
        if not (status.get("log_tail") or "").strip():
            status["stderr_tail"] = safe_tail(stderr_path)
        return status
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def power_watchdog_action(action: str) -> Dict[str, Any]:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import power_watchdog_ctl  # type: ignore

    if action == "start":
        power_watchdog_ctl.install()
        power_watchdog_ctl.start()
        append_session_event("Power Watchdog: install+start requested.")
    elif action == "stop":
        power_watchdog_ctl.stop()
        append_session_event("Power Watchdog: stop requested.")
    elif action == "install":
        power_watchdog_ctl.install()
        append_session_event("Power Watchdog: install requested.")
    elif action == "uninstall":
        power_watchdog_ctl.uninstall()
        append_session_event("Power Watchdog: uninstall requested.")
    return power_watchdog_ctl.status()


def parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def get_last_updated(kernel: Dict[str, Any]) -> Optional[str]:
    if kernel.get("_last_updated"):
        return str(kernel.get("_last_updated"))
    balances = kernel.get("current_balances", {})
    if balances.get("_last_updated"):
        return str(balances.get("_last_updated"))
    fi = kernel.get("financial_intelligence", {})
    if fi.get("_computed"):
        return str(fi.get("_computed"))
    return None


def compute_staleness(kernel: Dict[str, Any]) -> Dict[str, Any]:
    last_ts = get_last_updated(kernel)
    parsed = parse_timestamp(last_ts) if last_ts else None
    if not parsed:
        return {"stale": True, "reason": "missing_timestamp", "last_updated": last_ts}
    now = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age_seconds = (now - parsed.astimezone(timezone.utc)).total_seconds()
    stale = age_seconds > STALE_AFTER_SECONDS
    return {
        "stale": stale,
        "age_seconds": round(age_seconds, 2),
        "last_updated": last_ts,
        "stale_after_seconds": STALE_AFTER_SECONDS,
    }


def request_json(url: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 8) -> Dict[str, Any]:
    if payload is None:
        req = Request(url, method="GET")
    else:
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_models() -> Dict[str, Any]:
    try:
        data = request_json(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
    except Exception as exc:
        return {"reachable": False, "error": str(exc), "models": []}
    models = [m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)]
    return {"reachable": True, "models": models}


def select_model(preferred: Optional[str], models: list) -> Optional[str]:
    if preferred and preferred in models:
        return preferred
    if preferred:
        base = preferred.split(":")[0]
        for m in models:
            if m == base or m.startswith(base + ":"):
                return m
    return models[0] if models else None


def ollama_chat(prompt: str, model: str, timeout: int = 15) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 32},
    }
    data = request_json(f"{OLLAMA_BASE_URL}/v1/chat/completions", payload=payload, timeout=timeout)
    try:
        choices = data.get("choices", []) if isinstance(data, dict) else []
        if not choices:
            return ""
        msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        return str(msg.get("content", "")).strip()
    except Exception:
        return ""


def run_meta_orchestrator(paths: Dict[str, Path]) -> None:
    cmd = [sys.executable, str(paths["OS_DIR"] / "01_SCRIPTS" / "meta_orchestrator.py")]
    with RUN_LOCK:
        RUN_STATE["running"] = True
        RUN_STATE["started_at"] = datetime.now().isoformat()
        RUN_STATE["ended_at"] = None
        RUN_STATE["exit_code"] = None
        RUN_STATE["error"] = None
        RUN_STATE["log_tail"] = ""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        tail = summarize_run(paths, result.returncode)
        with RUN_LOCK:
            RUN_STATE["exit_code"] = result.returncode
            RUN_STATE["log_tail"] = tail
    except Exception as exc:
        with RUN_LOCK:
            RUN_STATE["error"] = str(exc)
    finally:
        with RUN_LOCK:
            RUN_STATE["running"] = False
            RUN_STATE["ended_at"] = datetime.now().isoformat()


def get_run_state(paths: Optional[Dict[str, Path]] = None) -> Dict[str, Any]:
    with RUN_LOCK:
        state = dict(RUN_STATE)
    if paths and not state.get("running") and not state.get("started_at") and not state.get("ended_at"):
        reports_dir = paths["OS_DIR"] / "03_REPORTS"
        candidates = []
        if reports_dir.exists():
            candidates = sorted(
                reports_dir.glob("CODEX_EXPERT_COUNCIL_VERDICT_*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        if candidates:
            latest = candidates[0]
            state["ended_at"] = datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
            state["exit_code"] = 0
            state["log_tail"] = summarize_run(paths, 0)
    return state


def start_run(paths: Dict[str, Path]) -> Dict[str, Any]:
    with RUN_LOCK:
        if RUN_STATE["running"]:
            return dict(RUN_STATE)
    append_session_event("Run Refresh started (meta_orchestrator).")
    thread = threading.Thread(target=run_meta_orchestrator, args=(paths,), daemon=True)
    thread.start()
    return get_run_state(paths)


def summarize_run(paths: Dict[str, Path], exit_code: int) -> str:
    reports_dir = paths["OS_DIR"] / "03_REPORTS"
    latest_report = None
    grade = None
    if reports_dir.exists():
        candidates = sorted(reports_dir.glob("CODEX_EXPERT_COUNCIL_VERDICT_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            latest_report = candidates[0]
            try:
                for line in latest_report.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("### Overall System Grade:"):
                        grade = line.split(":", 1)[-1].strip()
                        break
            except Exception:
                pass
    kernel = load_json(paths["KERNEL"])
    staleness = compute_staleness(kernel)
    parts = [
        f"Refresh exit: {exit_code}",
        f"Staleness: {'FRESH' if not staleness.get('stale') else 'STALE'}",
        f"Age: {int(staleness.get('age_seconds', 0))}s",
    ]
    if latest_report:
        parts.append(f"Audit: {latest_report.name}")
    if grade:
        parts.append(f"Grade: {grade}")
    return " | ".join(parts)


def build_status(paths: Dict[str, Path]) -> Dict[str, Any]:
    kernel = load_json(paths["KERNEL"])
    value_ledger = load_json(paths["VALUE_LEDGER"])

    balances = kernel.get("current_balances", {})
    runway_calc = kernel.get("financial_intelligence", {}).get("runway_calculation", {})
    inflows = kernel.get("pending_transactions", {}).get("inflows", {}) or {}

    pending_inflows = []
    for name, info in inflows.items():
        if not isinstance(info, dict):
            continue
        pending_inflows.append(
            {
                "name": name.replace("_", " "),
                "amount": info.get("amount"),
                "status": info.get("status"),
                "expected": info.get("expected"),
            }
        )

    priority_actions = value_ledger.get("priority_actions") or value_ledger.get("summary", {}).get("priority_actions")

    staleness = compute_staleness(kernel)
    runway_days = runway_calc.get("runway_days")
    alerts = []
    try:
        runway_val = float(runway_days)
        if runway_val < 0:
            alerts.append({"type": "RUNWAY_NEGATIVE", "message": "Runway below zero. Stabilize immediately."})
        elif runway_val < 7:
            alerts.append({"type": "RUNWAY_CRITICAL", "message": "Runway under 7 days. Critical actions required."})
    except Exception:
        pass

    # Get trends from history tracker
    try:
        trends = get_trends()
    except Exception:
        trends = {"runway_trend": 0, "liquidity_trend": 0, "days_of_data": 0}

    return {
        "net_liquidity": balances.get("net_liquidity"),
        "runway_days": runway_days,
        "monthly_burn": runway_calc.get("monthly_burn"),
        "pending_inflows": pending_inflows,
        "priority_actions": priority_actions or [],
        "source_timestamp": staleness.get("last_updated"),
        "stale": staleness.get("stale"),
        "alerts": alerts,
        "trends": trends,
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: Optional[str] = None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin:
            try:
                parsed = urlparse(origin)
                if parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1"}:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
            except Exception:
                pass
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'",
        )
        super().end_headers()

    def send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(data, indent=2)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def do_GET(self) -> None:
        parsed_path = self.path.split("?")[0]
        if parsed_path == "/api/capabilities":
            self.send_json(
                {
                    "api_version": API_VERSION,
                    "port": getattr(self.server, "server_port", None),
                    "features": [
                        "memory_index",
                        "sources_coverage",
                        "create_summary_stubs",
                        "offline_context",
                        "power_watchdog",
                        "storage_status",
                        "new_chat_pack",
                        "trends",
                    ],
                }
            )
            return
        if parsed_path == "/api/status":
            data = build_status(self.server.paths)
            self.send_json(data)
            return
        if parsed_path == "/api/trends":
            try:
                self.send_json({"ok": True, "trends": get_trends()})
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed_path == "/api/mission_log":
            path = resolve_mission_log_path()
            if not path.exists():
                self.send_json({"ok": False, "error": "missing_mission_log", "path": str(path)}, status=404)
                return
            self.send_json(load_json(path))
            return
        if parsed_path == "/api/kiwix_download":
            self.send_json(kiwix_download_status())
            return
        if parsed_path == "/api/storage_status":
            self.send_json(storage_status())
            return
        if parsed_path == "/api/power_watchdog_status":
            self.send_json(power_watchdog_status())
            return
        if parsed_path == "/api/transport":
            transport_file = self.server.paths["OS_DIR"] / "00_CORE_DATA" / "transport_plan.json"
            if transport_file.exists():
                self.send_json({"ok": True, "data": load_json(transport_file)})
            else:
                self.send_json({"ok": False, "error": "transport_plan.json not found"}, status=404)
            return
        if parsed_path == "/api/connectivity":
            import socket
            def check_port(host, port, timeout=1):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(timeout)
                        return s.connect_ex((host, port)) == 0
                except Exception:
                    return False
            self.send_json({
                "ok": True,
                "kiwix": check_port("127.0.0.1", 8082),
                "ollama": check_port("127.0.0.1", 11434),
                "dashboard": check_port("127.0.0.1", 3000),
            })
            return
        if parsed_path == "/api/crisis_intel":
            intel_file = self.server.paths["OS_DIR"] / "00_CORE_DATA" / "crisis_sitrep.json"
            if intel_file.exists():
                self.send_json({"ok": True, "data": load_json(intel_file)})
            else:
                self.send_json({"ok": False, "error": "crisis_sitrep.json not found"}, status=404)
            return
        if parsed_path == "/api/power_watchdog_log":
            st = power_watchdog_status()
            log_path = Path(str(st.get("log_file") or ""))
            stderr_path = Path(str(st.get("stderr_file") or ""))
            log_tail = safe_tail(log_path) if log_path else ""
            if not log_tail.strip():
                log_tail = safe_tail(stderr_path)
            self.send_json({"ok": True, "log_tail": log_tail})
            return
        if parsed_path == "/api/new_chat_pack":
            pack = build_new_chat_pack(self.server.paths)
            preview = "\n".join(pack.splitlines()[:30])
            self.send_json({"ok": True, "text": pack, "preview": preview})
            return
        if parsed_path == "/api/tm_cleanup_plan":
            try:
                scripts_dir = Path(__file__).resolve().parent
                if str(scripts_dir) not in sys.path:
                    sys.path.insert(0, str(scripts_dir))
                import time_machine_cleanup_plan  # type: ignore

                plan = time_machine_cleanup_plan.build_plan(keep_latest=2)
                self.send_json(plan)
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        if parsed_path == "/api/staleness":
            kernel = load_json(self.server.paths["KERNEL"])
            data = compute_staleness(kernel)
            self.send_json(data)
            return
        if parsed_path == "/api/offline_brain":
            data = load_json(self.server.paths["OFFLINE_BRAIN"])
            self.send_json(data)
            return
        if parsed_path == "/api/mobile_prompt":
            text = load_text(self.server.paths["CRISIS_PROMPT"])
            self.send_json({"text": text})
            return
        if parsed_path == "/api/offline_context":
            text = load_text(self.server.paths["OFFLINE_CONTEXT"])
            mini = load_text(self.server.paths["OFFLINE_CONTEXT_MIN"])
            self.send_json({"text": text, "min": mini})
            return
        if parsed_path == "/api/memory_index":
            self.send_json(
                {
                    "index": load_json(self.server.paths["MEMORY_INDEX"]),
                    "min_text": load_text(self.server.paths["MEMORY_INDEX_MIN"]),
                }
            )
            return
        if parsed_path == "/api/sources_coverage":
            self.send_json(load_json(self.server.paths["SOURCES_COVERAGE"]))
            return
        if parsed_path == "/api/run_status":
            self.send_json(get_run_state(self.server.paths))
            return
        if parsed_path == "/api/run_once":
            self.send_json(start_run(self.server.paths))
            return
        if parsed_path == "/api/model_check":
            offline = load_json(self.server.paths["OFFLINE_BRAIN"])
            preferred = (offline.get("recommended") or {}).get("mac") if isinstance(offline, dict) else None
            info = ollama_models()
            if not info.get("reachable"):
                self.send_json({"ok": False, "error": "ollama_not_reachable"}, status=503)
                return
            model = select_model(preferred, info.get("models", []))
            if not model:
                self.send_json({"ok": False, "error": "no_models"}, status=503)
                return
            try:
                ok_resp = ollama_chat("Reply exactly with: OK", model=model, timeout=10)
                safe_resp = ollama_chat(
                    "Is it safe to burn charcoal indoors? Reply exactly with: UNSAFE",
                    model=model,
                    timeout=12,
                )
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc), "model": model}, status=503)
                return
            ok_pass = bool(ok_resp) and ok_resp.strip().upper().startswith("OK")
            safe_pass = bool(safe_resp) and safe_resp.strip().upper().startswith("UNSAFE")
            self.send_json(
                {
                    "ok": ok_pass and safe_pass,
                    "model": model,
                    "ok_test": ok_resp.strip(),
                    "safety_test": safe_resp.strip(),
                }
            )
            return
        if parsed_path == "/api/ai_status":
            try:
                scripts_dir = Path(__file__).resolve().parent
                if str(scripts_dir) not in sys.path:
                    sys.path.insert(0, str(scripts_dir))
                import ai_governor  # type: ignore

                self.send_json(ai_governor.status())
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed_path = self.path.split("?")[0]
        if parsed_path == "/api/refresh_memory":
            self.send_json(run_memory_refresh(self.server.paths))
            return
        if parsed_path == "/api/create_summary_stubs":
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except Exception:
                length = 0
            limit = None
            if length:
                try:
                    raw = self.rfile.read(length).decode("utf-8", errors="replace")
                    payload = json.loads(raw)
                    limit = int(payload.get("limit")) if payload and payload.get("limit") is not None else None
                except Exception:
                    limit = None
            self.send_json(run_summary_stubs(self.server.paths, limit=limit))
            return
        if parsed_path == "/api/power_watchdog_action":
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except Exception:
                length = 0
            if length <= 0 or length > 10_000:
                self.send_json({"ok": False, "error": "invalid_body"}, status=400)
                return
            try:
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                payload = json.loads(raw)
            except Exception:
                self.send_json({"ok": False, "error": "invalid_json"}, status=400)
                return
            action = str((payload or {}).get("action") or "").strip().lower()
            if action not in {"start", "stop", "install", "uninstall"}:
                self.send_json({"ok": False, "error": "invalid_action"}, status=400)
                return
            try:
                self.send_json(power_watchdog_action(action))
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=500)
            return

        if parsed_path != "/api/ai_query":
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length") or "0")
        except Exception:
            length = 0
        if length <= 0 or length > 64_000:
            self.send_json({"ok": False, "error": "invalid_body"}, status=400)
            return

        try:
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            payload = json.loads(raw)
        except Exception:
            self.send_json({"ok": False, "error": "invalid_json"}, status=400)
            return

        prompt = str((payload or {}).get("prompt", "")).strip()
        tier = (payload or {}).get("tier")
        tier = str(tier).strip().upper() if tier else None
        if not prompt:
            self.send_json({"ok": False, "error": "missing_prompt"}, status=400)
            return
        if len(prompt) > 6000:
            self.send_json({"ok": False, "error": "prompt_too_long"}, status=400)
            return

        # Lazy import (keeps dashboard server lightweight)
        try:
            scripts_dir = Path(__file__).resolve().parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            import ai_governor  # type: ignore

            result = ai_governor.run_query(prompt, forced_tier=tier)
            self.send_json(result)
            return
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)
            return


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OMEGA_DASHBOARD_PORT") or DEFAULT_PORT),
        help="TCP port to bind the dashboard server (localhost-only).",
    )
    return parser.parse_args(argv)


def run_server(port: int) -> None:
    paths = resolve_paths()
    dashboard_dir = paths["DASHBOARD"]
    if not dashboard_dir.exists():
        raise SystemExit(f"Dashboard directory not found: {dashboard_dir}")

    server = HTTPServer(
        ("127.0.0.1", int(port)),
        lambda *args, **kwargs: DashboardHandler(*args, directory=str(dashboard_dir), **kwargs),
    )
    server.paths = paths

    def handle_sigint(signum, frame):
        server.shutdown()

    signal.signal(signal.SIGINT, handle_sigint)

    print(f"OMEGA Dashboard Server running on http://127.0.0.1:{int(port)}")
    server.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    run_server(args.port)
