#!/usr/bin/env python3
"""Summarize compiler diagnostics into batch-fix classes.

Consumes plain build logs. The goal is not to silence warnings; it identifies
high-leverage repeated boundaries so a porter can prove and fix a semantic
class once instead of chasing translation units.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

DIAG_RE=re.compile(
    r"(?P<path>[^\s:]+\.(?:c|cc|cpp|cxx|h|hpp)):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<level>warning|error): (?P<message>.*?)(?: \[-W(?P<flag>[^\]]+)\])?$"
)
BOUNDARY_RE=re.compile(
    r"(?:argument \d+ of|assignment to|initialization of|returning) [‘']([^’']+)[’']"
)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("log",type=Path)
    ap.add_argument("--out",type=Path,default=Path("compiler-triage.json"))
    args=ap.parse_args()

    diagnostics=[]
    for raw in args.log.read_text(errors="replace").splitlines():
        # GitHub logs prepend timestamps; search instead of match.
        m=DIAG_RE.search(raw)
        if not m:
            continue
        d=m.groupdict()
        boundary=BOUNDARY_RE.search(d["message"])
        diagnostics.append({
            "path":d["path"],
            "line":int(d["line"]),
            "level":d["level"],
            "flag":d["flag"] or "unclassified",
            "message":d["message"],
            "boundary":boundary.group(1) if boundary else None,
        })

    by_flag=collections.Counter(d["flag"] for d in diagnostics)
    by_file=collections.Counter(d["path"] for d in diagnostics)
    by_boundary=collections.Counter(
        d["boundary"] for d in diagnostics if d["boundary"]
    )

    # Runtime-risk ordering: fatal first, then known ABI/layout classes, then
    # frequency. Cosmetic classes stay visible but sort below semantic ones.
    risk_flags={
        "pointer-to-int-cast":0,
        "int-to-pointer-cast":0,
        "int-conversion":0,
        "array-bounds":0,
        "uninitialized":0,
        "maybe-uninitialized":0,
        "incompatible-pointer-types":1,
        "discarded-qualifiers":2,
        "format":2,
        "return-type":2,
        "switch":8,
        "comment":9,
        "parentheses":9,
    }
    batches=[]
    for boundary,count in by_boundary.items():
        rows=[d for d in diagnostics if d["boundary"]==boundary]
        flags=collections.Counter(d["flag"] for d in rows)
        score=min(risk_flags.get(f,5) for f in flags)
        batches.append({
            "boundary":boundary,
            "count":count,
            "risk_rank":score,
            "flags":dict(flags),
            "files":dict(collections.Counter(d["path"] for d in rows).most_common()),
            "sites":[{"path":d["path"],"line":d["line"],"message":d["message"]} for d in rows],
        })
    batches.sort(key=lambda b:(b["risk_rank"],-b["count"],b["boundary"]))

    out={
        "schema":1,
        "summary":{
            "diagnostics":len(diagnostics),
            "errors":sum(d["level"]=="error" for d in diagnostics),
            "warnings":sum(d["level"]=="warning" for d in diagnostics),
        },
        "by_flag":dict(by_flag.most_common()),
        "top_files":dict(by_file.most_common(30)),
        "batch_candidates":batches,
    }
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out["summary"],sort_keys=True))
    return 1 if out["summary"]["errors"] else 0

if __name__=="__main__":
    raise SystemExit(main())
