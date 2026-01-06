#!/usr/bin/env python3
"""
Verify a folder is safe to publish publicly (GDPR boundary).

This is a *best-effort* guardrail, not a legal guarantee.
It checks for:
- forbidden folders (Sources/, Psychotherapie/, SYSTEM_CONTEXT/, etc.)
- forbidden large/binary artifacts (models, zim)
- forbidden core-data files (OS/00_CORE_DATA/*.json except *.example.json)
- common PII-like strings (names/places) and absolute home paths
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


FORBIDDEN_DIRS = {
    "Sources",
    "Psychotherapie",
    "SYSTEM_CONTEXT",
    "stunspotPrompts",
    "Upwork Outreach",
    "prepper central erweiterung",
}

FORBIDDEN_EXTS = {
    ".zim",
    ".gguf",
    ".safetensors",
    ".bin",
    ".pt",
    ".pth",
    ".onnx",
    ".ckpt",
}

FORBIDDEN_FILENAMES = {
    "paypal_transactions.json",
    "paypal_transactions.csv",
    "metrics_history.json",
    "service_registry.json",
}

SUSPICIOUS_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("home_path", re.compile(r"/Users/[A-Za-z0-9._-]+/", re.IGNORECASE)),
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")),
]


TEXT_EXTS = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".css",
    ".html",
    ".json",
    ".yaml",
    ".yml",
    ".sh",
    ".command",
}


def iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        # skip git internals if someone already initialized a repo
        if ".git" in p.parts:
            continue
        if p.is_file():
            yield p


def rel_to(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except Exception:
        return str(p)


def check_forbidden_dirs(root: Path) -> List[str]:
    found: List[str] = []
    for d in FORBIDDEN_DIRS:
        if (root / d).exists():
            found.append(d)
    return found


def check_forbidden_core_data(root: Path) -> List[str]:
    found: List[str] = []
    core = root / "OS" / "00_CORE_DATA"
    if not core.exists():
        return found
    for p in core.glob("*.json"):
        if p.name.endswith(".example.json"):
            continue
        found.append(rel_to(root, p))
    return found


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTS


def scan_text(path: Path, max_bytes: int) -> str:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""

def load_extra_patterns(path: Path) -> List[Tuple[str, re.Pattern[str]]]:
    """
    Load additional regex patterns (one per line). Lines starting with '#' are ignored.
    The label is derived from the raw regex text (shortened if needed).
    """
    patterns: List[Tuple[str, re.Pattern[str]]] = []
    if not path.exists():
        return patterns
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            label = line[:40]
            try:
                patterns.append((f"extra:{label}", re.compile(line, re.IGNORECASE)))
            except re.error:
                continue
    except Exception:
        return patterns
    return patterns


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="Folder to verify (default: current dir)")
    parser.add_argument("--max-bytes", type=int, default=2_000_000, help="Max bytes to scan per file")
    parser.add_argument("--extra-patterns", default="", help="Optional file with extra regex patterns (one per line)")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        print(f"❌ root not found: {root}")
        return 2

    issues: List[str] = []

    # Forbidden top-level dirs
    forbidden_dirs = check_forbidden_dirs(root)
    if forbidden_dirs:
        issues.append(f"forbidden dirs present: {', '.join(forbidden_dirs)}")

    # Forbidden core data jsons
    forbidden_core = check_forbidden_core_data(root)
    if forbidden_core:
        issues.append("private core data jsons present:\n" + "\n".join(f"- {p}" for p in forbidden_core))

    # File-level checks
    suspicious_hits: List[str] = []
    forbidden_files: List[str] = []
    forbidden_exts: List[str] = []

    extra_patterns: List[Tuple[str, re.Pattern[str]]] = []
    if args.extra_patterns:
        extra_patterns = load_extra_patterns(Path(args.extra_patterns).expanduser())

    for p in iter_files(root):
        rp = rel_to(root, p)
        if p.name in FORBIDDEN_FILENAMES:
            forbidden_files.append(rp)
        if p.suffix.lower() in FORBIDDEN_EXTS:
            forbidden_exts.append(rp)

        if is_text_file(p):
            text = scan_text(p, args.max_bytes)
            for label, pat in SUSPICIOUS_PATTERNS + extra_patterns:
                if pat.search(text):
                    suspicious_hits.append(f"{rp}: {label}")

    if forbidden_files:
        issues.append("forbidden filenames present:\n" + "\n".join(f"- {p}" for p in sorted(set(forbidden_files))))
    if forbidden_exts:
        issues.append("forbidden binary/model/zim files present:\n" + "\n".join(f"- {p}" for p in sorted(set(forbidden_exts))))
    if suspicious_hits:
        issues.append("suspicious strings detected (review manually):\n" + "\n".join(f"- {h}" for h in sorted(set(suspicious_hits))))

    if issues:
        print("❌ PUBLIC EXPORT CHECK: FAIL")
        for i, issue in enumerate(issues, 1):
            print(f"\n[{i}] {issue}")
        return 1

    print("✅ PUBLIC EXPORT CHECK: OK")
    print(f"- root: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
