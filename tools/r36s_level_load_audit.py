#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

SOURCE_GLOBS = ("src/game/*.c", "src/*.c", "port/src/*.c")
ROOTS = ("load_bg_file", "bgRoomCalcBB", "bgOrderPortal", "sub_GAME_7F0B95D8", "sub_GAME_7F0B37EC")
CURRENT_FRONTIER = "bgOrderPortal"
FUNC_RE = re.compile(r"(?ms)^\s*(?:[A-Za-z_]\w*[\s\*]+)+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{")
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
KEYWORDS = {"if","for","while","switch","return","sizeof","defined","do","else","case","assert"}
RULES = [
 ("P0","pointer-compare-truncation",re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[^;\n]+(?:<|>|<=|>=)[^;\n]+\(\s*(?:s32|u32)\s*\)"),"Comparison appears to pass addresses through 32-bit integers."),
 ("P0","address-arithmetic-32",re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[A-Za-z_]\w*\s*[+\-]"),"Address-like arithmetic appears to be performed at 32-bit width."),
 ("P0","pointer-truncation",re.compile(r"\(\s*(?:s32|u32|int)\s*\)\s*(?:[A-Za-z_]\w*|\([^\n;]+\))"),"32-bit cast in reachable level-load code; verify this is not a pointer/address."),
 ("P1","integer-to-pointer",re.compile(r"\(\s*(?:u8|s8|u16|s16|u32|s32|Gfx|Vtx|Vertex|void|char)\s*\*\s*\)\s*(?:[A-Za-z_]\w*|0x[0-9A-Fa-f]+)"),"Integer/expression converted to pointer; inspect provenance and width."),
 ("P1","kseg-hardcoded-address",re.compile(r"0x(?:8|A)[0-9A-Fa-f]{7}\b|\|\s*0x80000000"),"N64 KSEG/absolute-address idiom reachable from level loading."),
 ("P1","raw-gfx-layout",re.compile(r"\(\s*(?:u8|u16|u32)\s*\*\s*\)\s*[A-Za-z_]\w*\s*\)\s*\["),"Raw byte/word indexing may assume the original N64 structure layout."),
 ("P2","sentinel-loop",re.compile(r"(?:while|for)\s*\([^\n]*(?:!=\s*NULL|offset_portal|while\s*\(\s*1\s*\))"),"Sentinel/unbounded loop on loader path; verify termination data after fixups."),
]
WARN_PATTERNS=("pointer-to-int-cast","int-to-pointer-cast","int-conversion","incompatible-pointer-types","array-bounds","stringop-overflow","use-after-free","maybe-uninitialized","uninitialized")

@dataclass
class Function:
    name:str; path:Path; start_line:int; end_line:int; body:str
@dataclass
class Finding:
    priority:str; kind:str; function:str; path:str; line:int; detail:str; excerpt:str; distance:int

def line_no(text, off): return text.count("\n",0,off)+1

def extract_functions(path):
    text=path.read_text(errors="replace"); out=[]
    for m in FUNC_RE.finditer(text):
        depth=0; end=None; i=m.end()-1
        while i<len(text):
            if text[i]=="{": depth+=1
            elif text[i]=="}":
                depth-=1
                if depth==0: end=i+1; break
            i+=1
        if end:
            out.append(Function(m.group("name"),path,line_no(text,m.start()),line_no(text,end),text[m.start():end]))
    return out

def collect(repo):
    funcs={}; seen=set()
    for pat in SOURCE_GLOBS:
        for p in repo.glob(pat):
            if p in seen: continue
            seen.add(p)
            for fn in extract_functions(p): funcs.setdefault(fn.name,fn)
    return funcs

def graph_for(funcs):
    names=set(funcs); g=defaultdict(set)
    for name,fn in funcs.items():
        for callee in CALL_RE.findall(fn.body):
            if callee in names and callee not in KEYWORDS and callee!=name: g[name].add(callee)
    return g

def walk(g,roots):
    dist={}; parent={}; q=deque()
    for r in roots: dist[r]=0; q.append(r)
    while q:
        cur=q.popleft()
        for nxt in sorted(g.get(cur,())):
            if nxt not in dist: dist[nxt]=dist[cur]+1; parent[nxt]=cur; q.append(nxt)
    return dist,parent

def scan(funcs,dist):
    out=[]
    for name,d in dist.items():
        fn=funcs.get(name)
        if not fn: continue
        lines=fn.body.splitlines()
        for prio,kind,rx,detail in RULES:
            for m in rx.finditer(fn.body):
                rel=line_no(fn.body,m.start()); src=fn.start_line+rel-1
                ex=lines[rel-1].strip()[:220] if rel-1<len(lines) else m.group(0)[:220]
                out.append(Finding(prio,kind,name,str(fn.path),src,detail,ex,d))
    return out

def warning_findings(path,dist):
    if not path or not path.exists(): return []
    out=[]; current=""
    f_re=re.compile(r"In function [‘'\x60]([^’'\x60]+)")
    w_re=re.compile(r"^([^:\n]+\.c):(\d+):\d+: warning: (.*)$")
    for raw in path.read_text(errors="replace").splitlines():
        fm=f_re.search(raw)
        if fm: current=fm.group(1); continue
        wm=w_re.match(raw)
        if not wm: continue
        msg=wm.group(3)
        if not any(x in msg for x in WARN_PATTERNS): continue
        if current and current not in dist: continue
        out.append(Finding("P0" if ("pointer" in msg or "int-conversion" in msg) else "P1","compiler-warning",current or "?",wm.group(1),int(wm.group(2)),msg,raw[:220],dist.get(current,999)))
    return out

def chain(name,parent):
    xs=[name]
    while xs[-1] in parent: xs.append(parent[xs[-1]])
    return " -> ".join(reversed(xs))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",type=Path,default=Path("."))
    ap.add_argument("--warnings",type=Path)
    ap.add_argument("--outdir",type=Path,default=Path("audit-out"))
    a=ap.parse_args()
    funcs=collect(a.repo); graph=graph_for(funcs)
    roots=tuple(r for r in ROOTS if r in funcs)
    if not roots: raise SystemExit("No level-loading roots found")
    dist,parent=walk(graph,roots)
    findings=scan(funcs,dist)+warning_findings(a.warnings,dist)
    uniq={(f.kind,f.path,f.line,f.function,f.excerpt):f for f in findings}
    rank={"P0":0,"P1":1,"P2":2}
    findings=sorted(uniq.values(),key=lambda f:(rank.get(f.priority,9),f.distance,f.path,f.line))
    a.outdir.mkdir(parents=True,exist_ok=True)
    with (a.outdir/"r36s-level-load-findings.tsv").open("w",newline="") as fp:
        w=csv.writer(fp,delimiter="\t"); w.writerow(["priority","kind","distance","function","path","line","detail","excerpt"])
        for f in findings: w.writerow([f.priority,f.kind,f.distance,f.function,f.path,f.line,f.detail,f.excerpt])
    counts=defaultdict(int)
    for f in findings: counts[f.priority]+=1
    with (a.outdir/"r36s-level-load-report.md").open("w") as fp:
        fp.write("# R36S level-loading frontier audit\n\n")
        fp.write(f"Current physical-device frontier: **after \`{CURRENT_FRONTIER}()\`**.\n\n")
        fp.write("Static candidates reachable from known level-loading roots; a hit is a review target, not proof of failure.\n\n")
        fp.write("## Summary\n\n")
        fp.write(f"- Reachable functions: **{len(dist)}** / {len(funcs)} parsed\n- P0: **{counts['P0']}**\n- P1: **{counts['P1']}**\n- P2: **{counts['P2']}**\n- Total: **{len(findings)}**\n\n")
        fp.write("## Roots\n\n")
        for r in ROOTS: fp.write(f"- \`{r}()\`: {'found' if r in funcs else 'missing'}\n")
        fp.write("\n## Current frontier neighborhood\n\n")
        callers=sorted(k for k,v in graph.items() if CURRENT_FRONTIER in v and k in dist)
        callees=sorted(graph.get(CURRENT_FRONTIER,()))
        fp.write(f"- Callers of \`{CURRENT_FRONTIER}()\`: {', '.join(callers) or 'none'}\n")
        fp.write(f"- Direct callees: {', '.join(callees) or 'none'}\n\n")
        fp.write("## Ranked findings\n\n")
        for i,f in enumerate(findings,1):
            fp.write(f"### {i}. {f.priority} {f.kind} — \`{f.function}()\`\n\n")
            fp.write(f"- Location: \`{f.path}:{f.line}\`\n- Root distance: {f.distance}\n- Call path: \`{chain(f.function,parent)}\`\n- Why: {f.detail}\n- Code: \`{f.excerpt.replace(chr(96),chr(39))}\`\n\n")
        fp.write("## Reachable call graph\n\n")
        for name in sorted(dist,key=lambda n:(dist[n],n)):
            if name not in funcs: continue
            kids=sorted(x for x in graph.get(name,()) if x in dist)
            fp.write(f"- d={dist[name]} \`{name}()\`" + (" -> "+", ".join(f"\`{x}()\`" for x in kids) if kids else "") + "\n")
    print(f"parsed={len(funcs)} reachable={len(dist)} findings={len(findings)}")
    print(a.outdir/"r36s-level-load-report.md")

if __name__=="__main__": main()
