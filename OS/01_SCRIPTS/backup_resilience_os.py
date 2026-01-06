#!/usr/bin/env python3
"""
ResilienceOS Backup (offline-first)
==================================
Creates a restorable backup on an external drive:
1) Live mirror (rsync) of the working tree (excluding common caches)
2) Timestamped mirror + snapshot tarball
3) Optional git bundle (full repo history) if .git exists

Default destination: /Volumes/KiwixVault/ResilienceOS_BACKUPS
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def run(cmd: List[str], cwd: Optional[Path] = None, timeout: Optional[int] = None) -> Dict[str, object]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "code": int(proc.returncode),
            "cmd": cmd,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except Exception as exc:
        return {"ok": False, "code": -1, "cmd": cmd, "error": str(exc)}


EXCLUDES = [
    ".DS_Store",
    "Thumbs.db",
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "node_modules/",
    "venv/",
    ".venv/",
    ".idea/",
    ".vscode/",
    "OS/logs/",
]


def pick_default_dest() -> Path:
    """
    Prefer KiwixVault (Knowledge Vault), fallback to Jedi_OS_Backup, then local home.
    """
    candidates = [
        Path("/Volumes/KiwixVault/ResilienceOS_BACKUPS"),
        Path("/Volumes/Jedi_OS_Backup/ResilienceOS_BACKUPS"),
        Path.home() / "ResilienceOS_BACKUPS",
    ]
    for c in candidates:
        try:
            if c.parent.exists():
                return c
        except Exception:
            continue
    return Path("/Volumes/KiwixVault/ResilienceOS_BACKUPS")


def ensure_dest(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)


def rsync_mirror(src: Path, dest: Path, delete: bool) -> Dict[str, object]:
    if shutil.which("rsync") is None:
        return {"ok": False, "error": "rsync_not_found"}
    cmd = ["rsync", "-a", "--human-readable"]
    if delete:
        cmd.append("--delete")
    for pat in EXCLUDES:
        cmd.extend(["--exclude", pat])
    cmd.extend([str(src) + "/", str(dest) + "/"])
    return run(cmd, timeout=60 * 60)


def make_tar_snapshot(src: Path, out_file: Path) -> Dict[str, object]:
    if shutil.which("tar") is None:
        return {"ok": False, "error": "tar_not_found"}
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["tar", "-czf", str(out_file)]
    for pat in EXCLUDES:
        cmd.extend(["--exclude", pat])
    cmd.extend(["-C", str(src.parent), src.name])
    return run(cmd, timeout=60 * 60)


def make_git_bundle(src: Path, out_file: Path) -> Dict[str, object]:
    if shutil.which("git") is None:
        return {"ok": False, "error": "git_not_found"}
    if not (src / ".git").exists():
        return {"ok": False, "error": "no_git_dir"}
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "bundle", "create", str(out_file), "--all"]
    return run(cmd, cwd=src, timeout=60 * 60)


def git_identity(src: Path) -> Dict[str, object]:
    if shutil.which("git") is None or not (src / ".git").exists():
        return {"ok": False}
    head = run(["git", "rev-parse", "HEAD"], cwd=src)
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=src)
    status = run(["git", "status", "--porcelain=v1"], cwd=src)
    return {"ok": True, "head": head, "branch": branch, "status": status}

def sha256_file(path: Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_bytes)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def artifact_record(path: Path) -> Dict[str, object]:
    try:
        return {
            "path": str(path),
            "bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        }
    except Exception as exc:
        return {"path": str(path), "error": str(exc)}


def write_restore_instructions(out_dir: Path, stamp: str) -> None:
    text = f"""# ResilienceOS Backup — Restore Instructions
Backup stamp: `{stamp}`

## Option A: Restore files from snapshot tarball
1) Choose a target folder (example):
   - `mkdir -p ~/ResilienceOS_restore_{stamp}`
2) Extract:
   - `tar -xzf snapshot.tar.gz -C ~/ResilienceOS_restore_{stamp}`

## Option B: Restore full git history from bundle
1) Clone from the bundle:
   - `git clone repo.bundle ~/ResilienceOS_repo_{stamp}`
2) (Optional) Check out the default branch:
   - `cd ~/ResilienceOS_repo_{stamp} && git status`

## Integrity
- Verify SHA256 values in `MANIFEST.json`.
"""
    (out_dir / "RESTORE.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default=str(pick_default_dest()), help="Destination root folder.")
    parser.add_argument("--delete", action="store_true", help="Mirror: delete files in dest not present in src.")
    parser.add_argument("--no-mirror", action="store_true", help="Skip rsync mirror.")
    parser.add_argument("--no-snapshot", action="store_true", help="Skip tar snapshot.")
    parser.add_argument("--no-bundle", action="store_true", help="Skip git bundle.")
    args = parser.parse_args()

    src = repo_root()
    dest_root = Path(args.dest).expanduser()
    ensure_dest(dest_root)

    stamp = now_stamp()
    out_dir = dest_root / stamp
    ensure_dest(out_dir)

    manifest: Dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_root": str(src),
        "dest_root": str(dest_root),
        "stamp": stamp,
        "excludes": EXCLUDES,
        "git": git_identity(src),
        "steps": {},
        "artifacts": [],
    }

    # Live mirror (stable) for "1:1" use-case
    if not args.no_mirror:
        live_dir = dest_root / "_CURRENT_MIRROR"
        ensure_dest(live_dir)
        manifest["steps"]["live_mirror"] = rsync_mirror(src, live_dir, delete=True)

    # Timestamped mirror (for forensic restore)
    if not args.no_mirror:
        mirror_dir = out_dir / "mirror"
        ensure_dest(mirror_dir)
        manifest["steps"]["mirror"] = rsync_mirror(src, mirror_dir, delete=bool(args.delete))

    if not args.no_snapshot:
        tar_path = out_dir / "snapshot.tar.gz"
        manifest["steps"]["snapshot"] = make_tar_snapshot(src, tar_path)
        if tar_path.exists():
            manifest["artifacts"].append(artifact_record(tar_path))

    if not args.no_bundle:
        bundle_path = out_dir / "repo.bundle"
        manifest["steps"]["git_bundle"] = make_git_bundle(src, bundle_path)
        if bundle_path.exists():
            manifest["artifacts"].append(artifact_record(bundle_path))

    write_restore_instructions(out_dir, stamp)

    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    ok = True
    for k, v in (manifest.get("steps") or {}).items():
        if isinstance(v, dict) and v.get("ok") is False:
            ok = False
    print(json.dumps({"ok": ok, "backup_dir": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
