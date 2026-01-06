#!/usr/bin/env python3
"""
Dashboard Smoke Test (offline-only)
Validates that the localhost dashboard is reachable and key endpoints work.

Writes a JSON report to OS/03_REPORTS/.
"""

from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def resolve_paths() -> Dict[str, Path]:
    scripts_dir = Path(__file__).resolve().parent
    os_dir = scripts_dir.parent
    logs = os_dir / "logs"
    return {
        "OS_DIR": os_dir,
        "REPORTS": os_dir / "03_REPORTS",
        "PORTFILE": logs / "dashboard_server.port",
        "OUT": os_dir / "03_REPORTS" / f"DASHBOARD_SMOKE_TEST_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json",
    }

def resolve_base_url(paths: Dict[str, Path]) -> str:
    env_url = os.environ.get("OMEGA_DASHBOARD_URL")
    if env_url:
        return env_url.rstrip("/")
    env_port = os.environ.get("OMEGA_DASHBOARD_PORT")
    if env_port:
        try:
            p = int(env_port)
            if 1 <= p <= 65535:
                return f"http://127.0.0.1:{p}"
        except Exception:
            pass
    try:
        portfile = paths.get("PORTFILE")
        if portfile and Path(portfile).exists():
            raw = Path(portfile).read_text(encoding="utf-8").strip()
            p = int(raw)
            if 1 <= p <= 65535:
                return f"http://127.0.0.1:{p}"
    except Exception:
        pass
    return "http://127.0.0.1:3000"


def fetch(url: str, timeout: int = 5) -> Tuple[int, Dict[str, str], str]:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.read().decode("utf-8", errors="replace")
        return status, headers, body


def fetch_json(url: str, timeout: int = 5) -> Tuple[int, Dict[str, str], Any]:
    status, headers, body = fetch(url, timeout=timeout)
    return status, headers, json.loads(body)

def post_json(url: str, payload: Dict[str, Any], timeout: int = 10) -> Tuple[int, Dict[str, str], Any]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.read().decode("utf-8", errors="replace")
        return status, headers, json.loads(body)


def wait_port(host: str, port: int, timeout_s: int = 5) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(0.2)
    return False

def retry(fn, attempts: int = 2, delay_s: float = 1.0):
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if i < attempts - 1:
                time.sleep(delay_s)
    if last_exc:
        raise last_exc
    raise RuntimeError("retry_failed")


def main() -> None:
    paths = resolve_paths()
    base = resolve_base_url(paths)
    started_at = datetime.now().isoformat()

    report: Dict[str, Any] = {
        "started_at": started_at,
        "base": base,
        "checks": [],
        "pass": True,
    }

    try:
        port = int(base.rsplit(":", 1)[-1])
    except Exception:
        port = 3000

    if not wait_port("127.0.0.1", port, timeout_s=5):
        report["pass"] = False
        report["error"] = "dashboard_port_not_listening"
    else:
        def record(name: str, ok: bool, detail: Any = None) -> None:
            report["checks"].append({"name": name, "ok": ok, "detail": detail})
            if not ok:
                report["pass"] = False

        # Root HTML
        try:
            status, headers, html = fetch(base + "/", timeout=5)
            record("GET /", status == 200, {"status": status})
            record("cache_headers_present", "cache-control" in headers and "no-store" in headers.get("cache-control", "").lower(), headers.get("cache-control"))
            record("csp_present", "content-security-policy" in headers, headers.get("content-security-policy"))
            css_ok = "style.css?v=" in html
            js_ok = "app.js?v=" in html
            record("ui_cache_bust_present", css_ok and js_ok, {"css": css_ok, "js": js_ok})
        except (HTTPError, URLError) as exc:
            record("GET /", False, str(exc))

        # Core JSON endpoints
        for ep in [
            "/api/capabilities",
            "/api/status",
            "/api/trends",
            "/api/staleness",
            "/api/offline_brain",
            "/api/mobile_prompt",
            "/api/offline_context",
            "/api/new_chat_pack",
            "/api/memory_index",
            "/api/sources_coverage",
            "/api/run_status",
            "/api/ai_status",
            "/api/tm_cleanup_plan",
            "/api/kiwix_download",
            "/api/storage_status",
            "/api/mission_log",
            "/api/power_watchdog_status",
        ]:
            try:
                status, _, data = fetch_json(base + ep, timeout=8)
                record(f"GET {ep}", status == 200 and isinstance(data, dict), {"status": status, "keys": list(data.keys())[:10]})
            except Exception as exc:
                record(f"GET {ep}", False, str(exc))

        # AI query (small prompt) - allow one retry (Ollama may be warming up)
        try:
            status, _, data = retry(
                lambda: post_json(base + "/api/ai_query", {"prompt": "Reply only: OK", "tier": "ECO"}, timeout=35),
                attempts=2,
                delay_s=2.0,
            )
            ok = status == 200 and isinstance(data, dict) and "ok" in data and "text" in data
            record(
                "POST /api/ai_query",
                ok,
                {"status": status, "ok": (data or {}).get("ok"), "engine": (data or {}).get("engine"), "model": (data or {}).get("model")},
            )
        except Exception as exc:
            record("POST /api/ai_query", False, str(exc))

        # Model check (can be slower / first-call flaky if Ollama is waking up)
        try:
            status, _, data = retry(lambda: fetch_json(base + "/api/model_check", timeout=25), attempts=2, delay_s=2.0)
            ok = status == 200 and isinstance(data, dict) and "ok" in data and "model" in data
            record("GET /api/model_check", ok, {"status": status, "ok": (data or {}).get("ok"), "model": (data or {}).get("model")})
        except Exception as exc:
            record("GET /api/model_check", False, str(exc))

        # Run refresh once (non-blocking) + poll status
        try:
            status, _, data = fetch_json(base + "/api/run_once", timeout=5)
            record("GET /api/run_once", status == 200 and isinstance(data, dict) and data.get("running") is True, {"status": status})
            done = False
            for _ in range(120):
                time.sleep(0.5)
                _, _, st = fetch_json(base + "/api/run_status", timeout=5)
                if not st.get("running"):
                    done = True
                    record("run_once_exit_code", st.get("exit_code") == 0, st)
                    record("run_status_log_tail", bool((st.get("log_tail") or "").strip()), "populated" if (st.get("log_tail") or "").strip() else "empty")
                    break
            if not done:
                record("run_once_timeout", False, "run did not finish within 60s")
        except Exception as exc:
            record("run_once_flow", False, str(exc))

    paths["REPORTS"].mkdir(parents=True, exist_ok=True)
    report["ended_at"] = datetime.now().isoformat()
    paths["OUT"].write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({"pass": report["pass"], "report": str(paths["OUT"])}, indent=2))


if __name__ == "__main__":
    main()
