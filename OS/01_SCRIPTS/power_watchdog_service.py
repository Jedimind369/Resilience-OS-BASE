#!/usr/bin/env python3
"""
Power Watchdog Service (offline-first, stdlib-only)
===================================================
Polls a small set of official-ish RSS/Atom feeds and alerts on keyword hits.
Designed for blackout scenarios: runs even with intermittent internet, never crashes,
logs everything locally, and de-dupes alerts.

This script is intended to be run via launchd (LaunchAgent), but can also be run
manually for debugging.
"""

from __future__ import annotations

import json
import os
import re
from html.entities import name2codepoint
from html import unescape as html_unescape
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
OS_DIR = SCRIPT_DIR.parent
CORE = OS_DIR / "00_CORE_DATA"

# macOS privacy: launchd jobs can be blocked from reading ~/Downloads.
# Allow relocating the watchdog "home" (config + logs + status) to a safe directory.
WATCHDOG_HOME_ENV = "RESILIENCE_WATCHDOG_HOME"
WATCHDOG_HOME = os.environ.get(WATCHDOG_HOME_ENV, "").strip()

if WATCHDOG_HOME:
    BASE_DIR = Path(WATCHDOG_HOME).expanduser().resolve()
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH = BASE_DIR / "power_watchdog_config.json"
    SEEN_PATH = BASE_DIR / "seen_news.txt"
    STATUS_PATH = BASE_DIR / "status.json"
    LOG_PATH = BASE_DIR / "power_watchdog.log"
else:
    LOGS_DIR = OS_DIR / "logs" / "power_watchdog"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH = CORE / "power_watchdog_config.json"
    SEEN_PATH = LOGS_DIR / "seen_news.txt"
    STATUS_PATH = LOGS_DIR / "status.json"
    LOG_PATH = LOGS_DIR / "power_watchdog.log"

MAX_LOG_BYTES = 1_000_000


@dataclass(frozen=True)
class Entry:
    source: str
    title: str
    link: str
    uid: str
    published: Optional[str]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def rotate_log_if_needed() -> None:
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > MAX_LOG_BYTES:
            rotated = LOGS_DIR / "power_watchdog.log.1"
            if rotated.exists():
                rotated.unlink()
            LOG_PATH.replace(rotated)
    except Exception:
        return


def log(msg: str) -> None:
    rotate_log_if_needed()
    line = f"[{now_iso()}] {msg}\n"
    try:
        LOG_PATH.write_text("", encoding="utf-8") if not LOG_PATH.exists() else None
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def load_config() -> Dict[str, Any]:
    cfg = safe_read_json(CONFIG_PATH) if CONFIG_PATH.exists() else {}
    if not cfg:
        cfg = {"enabled": True, "check_interval_seconds": 300, "sources": []}
    return cfg


def load_seen() -> set:
    try:
        if not SEEN_PATH.exists():
            return set()
        return set(SEEN_PATH.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        return set()


def append_seen(uid: str) -> None:
    try:
        with SEEN_PATH.open("a", encoding="utf-8") as f:
            f.write(uid + "\n")
    except Exception:
        pass


def fetch(url: str, timeout_s: int, max_bytes: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ResilienceOS/PowerWatchdog"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("feed_too_large")
        return data


def looks_like_html(data: bytes) -> bool:
    head = data[:600].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head


def parse_html_links(data: bytes, *, source: str, base_url: str) -> List[Entry]:
    """
    Best-effort HTML extraction for sites that don't expose a working RSS.
    We only extract links that look like "press releases" to avoid noise.
    """
    text = data.decode("utf-8", errors="replace")
    anchors = re.findall(r'(?is)<a\b[^>]*href=["\\\']([^"\\\']+)["\\\'][^>]*>(.*?)</a>', text)
    out: List[Entry] = []
    for href, label in anchors[:4000]:
        href = href.strip()
        if not href or href.startswith("#"):
            continue
        if not (href.startswith("http://") or href.startswith("https://") or href.startswith("/")):
            continue
        if href.startswith("/"):
            href = urljoin(base_url, href)
        # Filter: berlin press releases are consistently "pressemitteilung.<id>.php"
        if "berlin.de" in base_url and "pressemitteilung." not in href:
            continue
        title = re.sub(r"(?is)<[^>]+>", " ", label)
        title = html_unescape(" ".join(title.split()))
        if not title or len(title) < 12:
            continue
        uid = href
        out.append(Entry(source=source, title=title, link=href, uid=uid, published=None))
        if len(out) >= 80:
            break
    return out


def text_of(node: Optional[ET.Element]) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def find_first_text(parent: ET.Element, tags: Iterable[str]) -> str:
    for t in tags:
        el = parent.find(t)
        if el is not None:
            v = text_of(el)
            if v:
                return v
    return ""


def extract_link_rss(item: ET.Element) -> str:
    # RSS: <link>...</link>
    link = text_of(item.find("link")) or text_of(item.find("{*}link"))
    if link:
        return link
    # Some feeds use <link href="..."/>
    link_el = item.find("link") or item.find("{*}link")
    if link_el is not None and link_el.attrib.get("href"):
        return str(link_el.attrib.get("href"))
    return ""


def extract_link_atom(entry: ET.Element) -> str:
    # Atom: <link rel="alternate" href="..."/>
    for link_el in entry.findall("{*}link"):
        rel = (link_el.attrib.get("rel") or "").lower()
        href = link_el.attrib.get("href") or ""
        if href and (rel in {"", "alternate"}):
            return href
    # fallback: any link
    for link_el in entry.findall("{*}link"):
        href = link_el.attrib.get("href") or ""
        if href:
            return href
    return ""


def parse_feed(data: bytes, source: str) -> List[Entry]:
    # Some "official" feeds are not strict XML (e.g. unescaped '&' in titles).
    # Stdlib-only best-effort: sanitize common invalid tokens before parsing.
    text = data.decode("utf-8", errors="replace")
    text = "".join(ch for ch in text if ch in {"\t", "\n", "\r"} or ord(ch) >= 32)

    # Convert HTML named entities (e.g. &nbsp;) into numeric entities.
    def fix_named_entity(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in {"amp", "lt", "gt", "apos", "quot"}:
            return f"&{name};"
        cp = name2codepoint.get(name)
        return f"&#{cp};" if cp else f"&amp;{name};"

    text = re.sub(r"&([A-Za-z][A-Za-z0-9]+);", fix_named_entity, text)
    # Escape stray ampersands not part of an entity.
    text = re.sub(r"&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9]+;)", "&amp;", text)
    try:
        root = ET.fromstring(text.encode("utf-8", errors="ignore"))
    except Exception:
        # Fallback: tolerate broken RSS by regex-parsing <item> blocks.
        out: List[Entry] = []
        items = re.findall(r"(?is)<item\b[^>]*>(.*?)</item>", text)
        for raw in items[:200]:
            t = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", raw)
            l = re.search(r"(?is)<link\b[^>]*>(.*?)</link>", raw)
            g = re.search(r"(?is)<guid\b[^>]*>(.*?)</guid>", raw)
            p = re.search(r"(?is)<pubDate\b[^>]*>(.*?)</pubDate>", raw)
            title = html_unescape((t.group(1) if t else "").strip())
            link = html_unescape((l.group(1) if l else "").strip())
            uid = html_unescape((g.group(1) if g else "").strip()) or link or title
            pub = html_unescape((p.group(1) if p else "").strip()) or None
            # Strip CDATA wrappers.
            title = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", title, flags=re.S).strip() or "(no title)"
            link = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", link, flags=re.S).strip()
            if title:
                out.append(Entry(source=source, title=title, link=link, uid=uid, published=pub))
        return out

    # RSS: //item (namespace-agnostic)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{*}item")
    out: List[Entry] = []
    if items:
        for it in items:
            title = find_first_text(it, ["title", "{*}title"]) or "(no title)"
            link = extract_link_rss(it)
            uid = find_first_text(it, ["guid", "{*}guid", "{*}id"]) or link or title
            pub = find_first_text(it, ["pubDate", "{*}pubDate", "{*}published", "{*}updated"])
            out.append(Entry(source=source, title=title, link=link, uid=uid, published=pub or None))
        return out

    # Atom: //entry (namespace-agnostic)
    entries = root.findall(".//{*}entry")
    for en in entries:
        title = find_first_text(en, ["{*}title"]) or "(no title)"
        link = extract_link_atom(en)
        uid = find_first_text(en, ["{*}id"]) or link or title
        pub = find_first_text(en, ["{*}updated", "{*}published"])
        out.append(Entry(source=source, title=title, link=link, uid=uid, published=pub or None))
    return out


def match(title: str, cfg: Dict[str, Any]) -> bool:
    logic = cfg.get("match_logic") or {}
    title_l = title.lower()

    negatives = [str(x).lower() for x in (logic.get("negative_keywords") or [])]
    if any(n and n in title_l for n in negatives):
        return False

    locations = [str(x).lower() for x in (logic.get("locations") or [])]
    topics = [str(x).lower() for x in (logic.get("topics") or [])]
    hit_loc = any(k and k in title_l for k in locations)
    hit_topic = any(k and k in title_l for k in topics)

    if bool(logic.get("require_one_location", True)) and not hit_loc:
        return False
    if bool(logic.get("require_one_topic", True)) and not hit_topic:
        return False
    return True


def notify(title: str, body: str, sound: Optional[str]) -> None:
    # Notification is best-effort; failures are logged but not fatal.
    try:
        safe_body = body.replace('"', "'")
        safe_title = title.replace('"', "'")
        script = f'display notification "{safe_body}" with title "{safe_title}"'
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass
    if sound:
        try:
            subprocess.run(["afplay", sound], check=False)
        except Exception:
            pass


def update_status(**kwargs: Any) -> None:
    base: Dict[str, Any] = {}
    if STATUS_PATH.exists():
        base = safe_read_json(STATUS_PATH)
    base.update(kwargs)
    write_json_atomic(STATUS_PATH, base)


def prime_seen(entries: List[Entry], seen: set) -> None:
    # On first run, mark current items as seen to avoid notification spam.
    for e in entries[:50]:
        if e.uid not in seen:
            append_seen(e.uid)
            seen.add(e.uid)


def as_public_item(e: Entry) -> Dict[str, Any]:
    return {
        "title": e.title,
        "link": e.link,
        "published": e.published,
        "uid": e.uid,
    }


def run_once(cfg: Dict[str, Any], seen: set) -> Tuple[int, int]:
    sources = cfg.get("sources") or []
    timeout_s = int(cfg.get("request_timeout_seconds") or 10)
    max_bytes = int(cfg.get("max_feed_bytes") or 2_000_000)
    notif = cfg.get("notification") or {}
    notif_title = str(notif.get("title") or "⚡ POWER UPDATE")
    sound = str(notif.get("sound") or "") or None
    show_link = bool(notif.get("show_link_in_body", True))

    hits = 0
    checked = 0
    last_error = None
    latest_items: Dict[str, List[Dict[str, Any]]] = {}

    for src in sources:
        name = str((src or {}).get("name") or "source")
        url = str((src or {}).get("url") or "")
        if not url:
            continue
        checked += 1
        try:
            data = fetch(url, timeout_s=timeout_s, max_bytes=max_bytes)
            if looks_like_html(data):
                entries = parse_html_links(data, source=name, base_url=url)
            else:
                entries = parse_feed(data, source=name)
            latest_items[name] = [as_public_item(e) for e in entries[:10]]
            # Prime once if empty.
            if (not seen) and bool(cfg.get("prime_on_first_run", True)):
                prime_seen(entries, seen)
                log(f"[prime] {name}: primed {min(len(entries), 50)} items as seen")
                continue
            for e in entries[:80]:
                if e.uid in seen:
                    continue
                if match(e.title, cfg):
                    hits += 1
                    body = e.title
                    if show_link and e.link:
                        body = f"{e.title}\n{e.link}"
                    log(f"HIT ({name}): {e.title}")
                    notify(notif_title, body, sound)
                    update_status(
                        last_hit_at=now_iso(),
                        last_hit_title=e.title,
                        last_hit_link=e.link,
                        last_hit_source=name,
                    )
                append_seen(e.uid)
                seen.add(e.uid)
        except Exception as exc:
            last_error = f"{name}: {exc}"
            log(f"warn: {last_error}")

    update_status(
        ok=True,
        updated_at=now_iso(),
        checked_sources=checked,
        hits=hits,
        last_error=last_error,
        latest_items=latest_items,
    )
    return checked, hits


def main() -> None:
    log("service starting")
    update_status(ok=True, started_at=now_iso(), pid=os.getpid())

    while True:
        cfg = load_config()
        if not bool(cfg.get("enabled", True)):
            update_status(ok=True, updated_at=now_iso(), note="disabled_in_config")
            time.sleep(60)
            continue

        interval = int(cfg.get("check_interval_seconds") or 300)
        interval = max(30, min(interval, 3600))

        seen = load_seen()
        try:
            run_once(cfg, seen)
        except Exception as exc:
            log(f"error: run_once_failed: {exc}")
            update_status(ok=False, updated_at=now_iso(), last_error=str(exc))

        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("service stopped (KeyboardInterrupt)")
