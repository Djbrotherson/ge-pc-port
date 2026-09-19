#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, re
from dataclasses import dataclass
from pathlib import Path

SOURCE_GLOBS = (
    "src/**/*.c", "src/**/*.h",
    "include/**/*.h",
    "port/**/*.c", "port/**/*.h",
    "assets/**/*.h",
)

RULES = [
    ("P0","ptr-to-32-cast", re.compile(r"\(\s*(?:s32|u32|int|unsigned\s+int)\s*\)\s*(?:&\s*)?[A-Za-z_]\w*(?:\s*->\s*\w+|\s*\[[^\]]+\]|\b)"),
     "Pointer/pointer-like value explicitly narrowed to 32 bits."),
    ("P0","32-to-ptr-cast", re.compile(r"\(\s*(?:void|char|u8|s8|u16|s16|u32|s32|Gfx|Mtx|Vtx|Vertex|Model\w*|Prop\w*|Object\w*|Chr\w*|StandTile|AIRecord)\s*\*[^)]*\)\s*(?:\(?\s*)?(?:s32|u32|int|unsigned\s+int)?\s*[A-Za-z_]\w*"),
     "32-bit integer/pointer conversion requires width review."),
    ("P0","32-bit-address-arithmetic", re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[^;\n]+\s*[+\-]\s*[^;\n]+"),
     "Address/offset arithmetic appears to be forced through 32-bit width."),
    ("P0","pointer-int-assignment", re.compile(r"\b(?:s32|u32|int|unsigned\s+int)\s+[A-Za-z_]\w*\s*=\s*(?:\([^;\n]*\*\)|&\s*[A-Za-z_]|[A-Za-z_]\w*\s*->\s*[A-Za-z_]\w*)"),
     "A 32-bit scalar is initialized from a pointer-like expression."),
    ("P1","fixed-n64-allocation", re.compile(r"mempAllocBytesInBank\s*\([^;\n]*(?:0x(?:10|14|18|1c|20|24|28|2c|30|34|38|3c|40|44|48|4c|50)|\*\s*4\b)[^;\n]*\)"),
     "Fixed allocation/stride may encode a 32-bit N64 struct layout."),
    ("P1","raw-word-layout", re.compile(r"\(\s*(?:u32|s32)\s*\*\s*\)\s*[^;\n]+\[[^\]]+\]"),
     "Raw 32-bit word indexing can assume original N64 object layout."),
    ("P1","pointer-compare-via-32", re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[^;\n]+(?:==|!=|<|>|<=|>=)\s*\(\s*(?:s32|u32)\s*\)"),
     "Pointer identity/comparison appears to be narrowed to 32 bits."),
    ("P1","n64-kseg-address", re.compile(r"\b0x(?:8|A)[0-9A-Fa-f]{7}\b|\|\s*0x80000000\b"),
     "Hard-coded N64 virtual-address/KSEG idiom needs host mapping review."),
]

WARN_RX = re.compile(r"^([^:\n]+\.(?:c|h)):(\d+):\d+: warning: (.*)$")
WARN_KEYS = (
    "pointer-to-int-cast", "int-to-pointer-cast", "int-conversion",
    "incompatible-pointer-types", "array-bounds", "stringop-overflow",
)

@dataclass
class Finding:
    priority: str
    kind: str
    path: str
    line: int
    detail: str
    excerpt: str

def files(repo: Path):
    seen=set()
    for g in SOURCE_GLOBS:
        for p in repo.glob(g):
            if p.is_file() and p not in seen:
                seen.add(p); yield p

def scan(repo: Path):
    out=[]
    for p in files(repo):
        text=p.read_text(errors="replace")
        lines=text.splitlines()
        for pri,kind,rx,detail in RULES:
            for m in rx.finditer(text):
                line=text.count("\n",0,m.start())+1
                excerpt=lines[line-1].strip()[:260] if line-1 < len(lines) else m.group(0)[:260]
                out.append(Finding(pri,kind,str(p),line,detail,excerpt))
    return out

def warnings(path: Path|None):
    if not path or not path.exists(): return []
    out=[]
    for raw in path.read_text(errors="replace").splitlines():
        m=WARN_RX.match(raw)
        if not m: continue
        msg=m.group(3)
        if not any(k in msg for k in WARN_KEYS): continue
        pri="P0" if any(k in msg for k in ("pointer-to-int","int-to-pointer","int-conversion","incompatible-pointer-types")) else "P1"
        out.append(Finding(pri,"compiler-warning",m.group(1),int(m.group(2)),msg,raw[:260]))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,default=Path("."))
    ap.add_argument("--warnings",type=Path)
    ap.add_argument("--outdir",type=Path,default=Path("lp64-audit-out"))
    args=ap.parse_args()

    found=scan(args.repo)+warnings(args.warnings)
    uniq={(f.kind,f.path,f.line,f.excerpt):f for f in found}
    rank={"P0":0,"P1":1,"P2":2}
    found=sorted(uniq.values(), key=lambda f:(rank.get(f.priority,9),f.path,f.line,f.kind))

    args.outdir.mkdir(parents=True,exist_ok=True)
    with (args.outdir/"r36s-lp64-findings.tsv").open("w",newline="") as fp:
        w=csv.writer(fp,delimiter="\t")
        w.writerow(["priority","kind","path","line","detail","excerpt"])
        for f in found: w.writerow([f.priority,f.kind,f.path,f.line,f.detail,f.excerpt])

    counts={}
    kinds={}
    for f in found:
        counts[f.priority]=counts.get(f.priority,0)+1
        kinds[f.kind]=kinds.get(f.kind,0)+1

    with (args.outdir/"r36s-lp64-report.md").open("w") as fp:
        fp.write("# R36S whole-codebase 32/64/32 audit\n\n")
        fp.write("Scope: all decompiled C/H sources under src/, include/, port/, plus generated headers used by the build.\n\n")
        fp.write("This report targets host-width hazards, not gameplay correctness. P0 means high-confidence width/prototype/address risk; P1 means layout/address assumptions requiring review.\n\n")
        fp.write("## Summary\n\n")
        fp.write(f"- P0: **{counts.get('P0',0)}**\n")
        fp.write(f"- P1: **{counts.get('P1',0)}**\n")
        fp.write(f"- Total: **{len(found)}**\n\n")
        fp.write("## By class\n\n")
        for k,n in sorted(kinds.items(), key=lambda kv:(-kv[1],kv[0])):
            fp.write(f"- {k}: **{n}**\n")
        fp.write("\n## Findings\n\n")
        for i,f in enumerate(found,1):
            fp.write(f"### {i}. {f.priority} {f.kind}\n\n")
            fp.write(f"- Location: `{f.path}:{f.line}`\n")
            fp.write(f"- Why: {f.detail}\n")
            fp.write(f"- Code: `{f.excerpt.replace(chr(96),chr(39))}`\n\n")

    print(f"findings={len(found)} P0={counts.get('P0',0)} P1={counts.get('P1',0)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
