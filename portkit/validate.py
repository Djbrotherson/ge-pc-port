#!/usr/bin/env python3
"""Portkit validation rules that are safe to apply across decomp/source ports."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE_EXTS={".c",".h",".cc",".cpp",".cxx",".hpp"}

RULES=(

    (
        "P1",
        "raw-32bit-pointer-token-boundary",
        re.compile(r"\((?:s32|u32|int|unsigned\\s+int)\)\\s*(?:\(\\s*u32\\s*\)\\s*)?\(\\s*(?:u?intptr_t)\\s*\)"),
        "Raw host-pointer-to-32-bit conversion must be classified. Proven N64 cart, segmented, message, wire or serialized tokens should use a named token helper; native pointers must remain pointer-width."
    ),
    (
        "P1",
        "unchecked-persistent-read",
        re.compile(r"\bfread\s*\([^;]+;"),
        "Persistent/file reads should verify the returned byte/item count and define the unread remainder deterministically."
    ),
    (
        "P1",
        "empty-if-side-effect",
        re.compile(r"\bif\s*\([^;{}]+\)\s*;"),
        "Empty conditional statements in decomps may exist only for matching/side effects; review for host compiler UB/warning behavior and isolate with a host-only equivalent when needed."
    ),
    (
        "P0",
        "array-address-passed",
        re.compile(r"\b(?:sprintf|strcat|strcpy|strlen)\s*\(\s*&\s*[A-Za-z_]\w*\b"),
        "Array expressions decay to pointers; passing &array changes the pointer type and can hide ABI/prototype mistakes."
    ),
    (
        "P1",
        "pointer-slot-struct-pun",
        re.compile(r"return\s*\(\s*[A-Za-z_]\w*\s*\*\s*\)\s*&\s*[A-Za-z_]\w*\s*\[[^\]]+\]"),
        "Address of an array element is returned as an unrelated struct pointer. This often encodes an N64 first-field/word alias that must be re-expressed with the real slot type on LP64."
    ),
    (
        "P1",
        "bitmask-comparison-precedence",
        re.compile(r"\b(?:if|while)\s*\([^\n;]*(?:&|\|)[^\n;]*(?:==|!=|>|<)"),
        "Bitwise masks mixed with comparisons are easy to parse differently than intended. Parenthesize the mask expression explicitly, e.g. (flags & MASK) != 0."
    ),
    (
        "P1",
        "logical-not-bitmask",
        re.compile(r"!\s*\([^\n;]+\)\s*&"),
        "Logical-not followed by bitwise AND collapses the left operand to 0/1 before masking. Review for the common intended form !(flags & MASK)."
    ),
    (
        "P1",
        "owner-slot-struct-cast",
        re.compile(r"\(\s*(?:struct\s+)?[A-Za-z_]\w*\s*\*\s*\)\s*&\s*[A-Za-z_]\w*(?:\s*->\s*\w+|\s*\[[^\]]+\])?"),
        "Address of a storage slot is cast to a struct pointer. This can encode an N64 first-field owner-slot convention; expose the slot as T** at a host adapter boundary instead of dereferencing a fake struct."
    ),
)

def iter_files(repo:Path, roots:list[str]):
    for root in roots:
        p=repo/root
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in SOURCE_EXTS:
                yield f.relative_to(repo).as_posix(),f

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,default=Path("."))
    ap.add_argument("--roots",nargs="*",default=["src","include","port"])
    ap.add_argument("--out",type=Path,default=Path("portkit-validation.json"))
    args=ap.parse_args()

    findings=[]
    for rel,path in iter_files(args.repo,args.roots):
        text=path.read_text(errors="replace")
        for sev,kind,rx,why in RULES:
            for m in rx.finditer(text):
                findings.append({
                    "severity":sev,
                    "kind":kind,
                    "path":rel,
                    "line":text.count("\n",0,m.start())+1,
                    "why":why,
                    "excerpt":m.group(0)[:180],
                })

    findings.sort(key=lambda x:(x["severity"],x["path"],x["line"],x["kind"]))
    out={"schema":1,"findings":findings,"summary":{
        "P0":sum(f["severity"]=="P0" for f in findings),
        "P1":sum(f["severity"]=="P1" for f in findings),
    }}
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out["summary"],sort_keys=True))
    return 2 if out["summary"]["P0"] else 0

if __name__=="__main__":
    raise SystemExit(main())
