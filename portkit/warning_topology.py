#!/usr/bin/env python3
"""Summarize compiler diagnostics by semantic-risk class and source hotspot.

This is intentionally a triage tool, not a warning suppressor. It helps choose
the next *batch* to audit so one proof build validates a whole semantic class.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DIAG_RE = re.compile(
    r"(?P<path>[^:\n]+\.(?:c|cc|cpp|cxx|h|hpp)):"
    r"(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<level>warning|error):\s+(?P<message>.*?)"
    r"(?:\s+\[-W(?P<wclass>[^\]]+)\])?$"
)

HIGH_SIGNAL = {
    "pointer-to-int-cast": "P0",
    "int-to-pointer-cast": "P0",
    "int-conversion": "P0",
    "array-bounds": "P0",
    "array-bounds=": "P0",
    "stringop-overflow": "P0",
    "stringop-overread": "P0",
    "use-after-free": "P0",
    "uninitialized": "P0",
    "maybe-uninitialized": "P0",
    "incompatible-pointer-types": "P1",
    "discarded-qualifiers": "P1",
    "cast-align": "P1",
    "packed-not-aligned": "P1",
    "address-of-packed-member": "P1",
    "format": "P1",
    "overflow": "P1",
}

LOW_VALUE = {
    "comment",
    "switch",
    "parentheses",
    "unused-function",
    "unused-variable",
    "unused-parameter",
}

def classify(wclass: str | None, level: str) -> str:
    if level == "error":
        return "P0"
    if wclass in HIGH_SIGNAL:
        return HIGH_SIGNAL[wclass]
    if wclass in LOW_VALUE:
        return "noise"
    return "review"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--out", type=Path, default=Path("warning-topology.json"))
    ap.add_argument("--top", type=int, default=30)
    args = ap.parse_args()

    by_class = Counter()
    by_file = Counter()
    by_risk = Counter()
    matrix = defaultdict(Counter)
    diagnostics = []

    for raw in args.log.read_text(errors="replace").splitlines():
        # CI timestamps/prefixes are allowed; search from the last plausible path.
        match = None
        for m in DIAG_RE.finditer(raw):
            match = m
        if not match:
            continue

        d = match.groupdict()
        wclass = d["wclass"] or "unclassified"
        risk = classify(d["wclass"], d["level"])
        path = d["path"].strip()
        # GitHub Actions commonly prefixes absolute checkout paths. Keep a compact
        # repo-relative suffix when possible without assuming one repository name.
        marker = "/src/"
        if marker in path:
            path = "src/" + path.rsplit(marker, 1)[1]
        elif "/port/" in path:
            path = "port/" + path.rsplit("/port/", 1)[1]
        elif "/assets/" in path:
            path = "assets/" + path.rsplit("/assets/", 1)[1]

        item = {
            "path": path,
            "line": int(d["line"]),
            "column": int(d["col"]),
            "level": d["level"],
            "warning_class": wclass,
            "risk": risk,
            "message": d["message"],
        }
        diagnostics.append(item)
        by_class[wclass] += 1
        by_file[path] += 1
        by_risk[risk] += 1
        matrix[path][wclass] += 1

    ranked_files = []
    for path, count in by_file.most_common(args.top):
        ranked_files.append({
            "path": path,
            "total": count,
            "classes": dict(matrix[path].most_common()),
            "high_signal": sum(
                n for cls, n in matrix[path].items()
                if classify(None if cls == "unclassified" else cls, "warning") in {"P0", "P1"}
            ),
        })

    out = {
        "schema": 1,
        "summary": {
            "diagnostics": len(diagnostics),
            "risk": dict(by_risk),
            "classes": dict(by_class.most_common()),
        },
        "ranked_files": ranked_files,
        "diagnostics": diagnostics,
        "workflow": [
            "Start from a green baseline.",
            "Rank P0/P1 classes and files; ignore bulk low-value noise initially.",
            "Prove one semantic invariant that explains many diagnostics.",
            "Transform only compiler-proven sites or the shared source-of-truth definition.",
            "Commit the batch atomically and run exactly one target proof build.",
            "Measure the actual diagnostic delta and promote the invariant into a regression rule.",
        ],
    }
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["summary"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
