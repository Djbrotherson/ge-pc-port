#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

SOURCE_GLOBS = ("src/game/*.c", "src/*.c", "port/src/*.c")
ROOTS = (
    "lvlStageLoad",
    "proplvreset2",
    "load_bg_file",
    "bgRoomCalcBB",
    "bgOrderPortal",
)
CURRENT_FRONTIER = "proplvreset2"
DEVICE_CONFIRMED = {
    "stanDetermineEOF",
    "stanLoadFile",
    "bgRoomCalcBB",
    "sub_GAME_7F0B993C",
    "bgOrderPortal",
    "sub_GAME_7F09B820",
    "initModelHitEntryFreeList",
    "modelmgrResetSlotCounts",
    "init_load_objpos_table",
    "reinit_between_menus",
    "init_sound_effects_registers",
    "init_guards",
    "bodiesReset",
}

FUNC_RE = re.compile(
    r"(?ms)^\s*(?:[A-Za-z_]\w*[\s\*]+)+(?P<name>[A-Za-z_]\w*)\s*"
    r"\([^;{}]*\)\s*(?:(?://[^\n]*\n\s*)|(?:/\*.*?\*/\s*))?\{"
)
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
KEYWORDS = {
    "if", "for", "while", "switch", "return", "sizeof", "defined",
    "do", "else", "case", "assert",
}

RULES = [
    (
        "P0",
        "pointer-compare-truncation",
        re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[^;\n]+(?:<|>|<=|>=)[^;\n]+\(\s*(?:s32|u32)\s*\)"),
        "Comparison appears to pass addresses through 32-bit integers.",
    ),
    (
        "P0",
        "address-arithmetic-32",
        re.compile(
            r"\(\s*(?:s32|u32)\s*\)\s*"
            r"(?:[A-Za-z_]\w*(?:ptr|Ptr|pointer|Pointer)[A-Za-z0-9_]*|"
            r"[^;\n]*->(?:ptr|p[A-Z])[A-Za-z0-9_]*)\s*[+\-]"
        ),
        "Pointer-like address arithmetic appears to be performed at 32-bit width.",
    ),
    (
        "P1",
        "pointer-cast-review",
        re.compile(
            r"\(\s*(?:s32|u32)\s*\)\s*"
            r"(?:[A-Za-z_]\w*(?:ptr|Ptr|pointer|Pointer)[A-Za-z0-9_]*|"
            r"[^;\n]*->(?:ptr|p[A-Z])[A-Za-z0-9_]*)"
        ),
        "Pointer-like expression cast to 32-bit integer; verify mapping assumptions.",
    ),
    (
        "P1",
        "kseg-hardcoded-address",
        re.compile(r"0x(?:8|A)[0-9A-Fa-f]{7}\b|\|\s*0x80000000"),
        "N64 KSEG/absolute-address idiom reachable from level loading.",
    ),
    (
        "P1",
        "raw-gfx-layout",
        re.compile(r"\(\s*(?:u8|u16|u32)\s*\*\s*\)\s*[A-Za-z_]\w*\s*\)\s*\["),
        "Raw byte/word indexing may assume original N64 structure layout.",
    ),
    (
        "P2",
        "sentinel-loop",
        re.compile(r"(?:while|for)\s*\([^\n]*(?:!=\s*NULL|offset_portal|while\s*\(\s*1\s*\))"),
        "Sentinel/unbounded loop on loader path; verify termination data after fixups.",
    ),
]

WARN_PATTERNS = (
    "pointer-to-int-cast",
    "int-to-pointer-cast",
    "int-conversion",
    "incompatible-pointer-types",
    "array-bounds",
    "stringop-overflow",
    "use-after-free",
    "maybe-uninitialized",
    "uninitialized",
)

@dataclass
class Function:
    name: str
    path: Path
    start_line: int
    end_line: int
    body: str

@dataclass
class Finding:
    priority: str
    kind: str
    function: str
    path: str
    line: int
    detail: str
    excerpt: str
    distance: int

def line_no(text: str, off: int) -> int:
    return text.count("\n", 0, off) + 1

def extract_functions(path: Path) -> list[Function]:
    text = path.read_text(errors="replace")
    out: list[Function] = []
    for m in FUNC_RE.finditer(text):
        depth = 0
        end = None
        i = m.end() - 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
            i += 1
        if end is not None:
            out.append(Function(
                m.group("name"),
                path,
                line_no(text, m.start()),
                line_no(text, end),
                text[m.start():end],
            ))
    return out

def collect(repo: Path) -> dict[str, Function]:
    funcs: dict[str, Function] = {}
    seen: set[Path] = set()
    for pattern in SOURCE_GLOBS:
        for path in repo.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            for fn in extract_functions(path):
                funcs.setdefault(fn.name, fn)
    return funcs

def graph_for(funcs: dict[str, Function]) -> dict[str, set[str]]:
    names = set(funcs)
    graph: dict[str, set[str]] = defaultdict(set)
    for name, fn in funcs.items():
        for callee in CALL_RE.findall(fn.body):
            if callee in names and callee not in KEYWORDS and callee != name:
                graph[name].add(callee)
    return graph

def walk(graph: dict[str, set[str]], roots: tuple[str, ...]):
    dist: dict[str, int] = {}
    parent: dict[str, str] = {}
    q = deque()
    for root in roots:
        dist[root] = 0
        q.append(root)
    while q:
        cur = q.popleft()
        for nxt in sorted(graph.get(cur, ())):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                parent[nxt] = cur
                q.append(nxt)
    return dist, parent

def scan(funcs: dict[str, Function], dist: dict[str, int]) -> list[Finding]:
    out: list[Finding] = []
    for name, distance in dist.items():
        fn = funcs.get(name)
        if not fn:
            continue
        lines = fn.body.splitlines()
        for priority, kind, rx, detail in RULES:
            for m in rx.finditer(fn.body):
                rel = line_no(fn.body, m.start())
                src_line = fn.start_line + rel - 1
                excerpt = lines[rel - 1].strip()[:220] if rel - 1 < len(lines) else m.group(0)[:220]
                out.append(Finding(
                    priority, kind, name, str(fn.path), src_line,
                    detail, excerpt, distance,
                ))
    return out

def warning_findings(path: Path | None, dist: dict[str, int]) -> list[Finding]:
    if not path or not path.exists():
        return []
    out: list[Finding] = []
    current = ""
    func_re = re.compile(r"In function [‘'\x60]([^’'\x60]+)")
    warn_re = re.compile(r"^([^:\n]+\.c):(\d+):\d+: warning: (.*)$")
    for raw in path.read_text(errors="replace").splitlines():
        fm = func_re.search(raw)
        if fm:
            current = fm.group(1)
            continue
        wm = warn_re.match(raw)
        if not wm:
            continue
        msg = wm.group(3)
        if not any(p in msg for p in WARN_PATTERNS):
            continue
        if current and current not in dist:
            continue
        priority = "P0" if (
            "pointer-to-int" in msg
            or "int-to-pointer" in msg
            or "incompatible-pointer-types" in msg
            or "int-conversion" in msg
        ) else "P1"
        out.append(Finding(
            priority,
            "compiler-warning",
            current or "?",
            wm.group(1),
            int(wm.group(2)),
            msg,
            raw[:220],
            dist.get(current, 999),
        ))
    return out

def chain(name: str, parent: dict[str, str]) -> str:
    nodes = [name]
    while nodes[-1] in parent:
        nodes.append(parent[nodes[-1]])
    return " -> ".join(reversed(nodes))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--warnings", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("audit-out"))
    args = ap.parse_args()

    funcs = collect(args.repo)
    graph = graph_for(funcs)
    roots = tuple(r for r in ROOTS if r in funcs)
    if not roots:
        raise SystemExit("No level-loading roots found")

    dist, parent = walk(graph, roots)
    findings = scan(funcs, dist)
    findings.extend(warning_findings(args.warnings, dist))

    unique = {
        (f.kind, f.path, f.line, f.function, f.excerpt): f
        for f in findings
    }
    rank = {"P0": 0, "P1": 1, "P2": 2}
    findings = sorted(
        unique.values(),
        key=lambda f: (
            rank.get(f.priority, 9),
            f.function in DEVICE_CONFIRMED,
            f.distance,
            f.path,
            f.line,
        ),
    )

    args.outdir.mkdir(parents=True, exist_ok=True)

    with (args.outdir / "r36s-level-load-findings.tsv").open("w", newline="") as fp:
        w = csv.writer(fp, delimiter="\t")
        w.writerow([
            "priority", "kind", "distance", "device_confirmed",
            "function", "path", "line", "detail", "excerpt",
        ])
        for f in findings:
            w.writerow([
                f.priority,
                f.kind,
                f.distance,
                "yes" if f.function in DEVICE_CONFIRMED else "no",
                f.function,
                f.path,
                f.line,
                f.detail,
                f.excerpt,
            ])

    counts = defaultdict(int)
    for f in findings:
        counts[f.priority] += 1

    with (args.outdir / "r36s-level-load-report.md").open("w") as fp:
        fp.write("# R36S level-loading frontier audit\n\n")
        fp.write(
            f"Current physical-device frontier: **entering `{CURRENT_FRONTIER}()` "
            "after `bgOrderPortal()` returned**.\n\n"
        )
        fp.write(
            "Static candidates reachable from known level-loading roots; "
            "a hit is a review target, not proof of failure.\n\n"
        )
        fp.write(
            "Functions already confirmed to return on the physical R36S are "
            "deprioritized unless new evidence regresses them.\n\n"
        )

        fp.write("## Summary\n\n")
        fp.write(f"- Reachable functions: **{len(dist)}** / {len(funcs)} parsed\n")
        fp.write(f"- P0: **{counts['P0']}**\n")
        fp.write(f"- P1: **{counts['P1']}**\n")
        fp.write(f"- P2: **{counts['P2']}**\n")
        fp.write(f"- Total: **{len(findings)}**\n\n")

        fp.write("## Roots\n\n")
        for root in ROOTS:
            fp.write(f"- `{root}()`: {'found' if root in funcs else 'missing'}\n")

        fp.write("\n## Device-confirmed phases\n\n")
        for name in sorted(DEVICE_CONFIRMED):
            fp.write(
                f"- `{name}()`: returned successfully on latest physical-device log\n"
            )

        fp.write("\n## Current frontier neighborhood\n\n")
        callers = sorted(
            name for name, children in graph.items()
            if CURRENT_FRONTIER in children and name in dist
        )
        callees = sorted(graph.get(CURRENT_FRONTIER, ()))
        fp.write(
            f"- Callers of `{CURRENT_FRONTIER}()`: "
            f"{', '.join(callers) or 'none'}\n"
        )
        fp.write(
            f"- Direct callees: {', '.join(callees) or 'none'}\n\n"
        )

        fp.write("## Ranked findings\n\n")
        for i, f in enumerate(findings, 1):
            confirmed = " (device-confirmed earlier phase)" if f.function in DEVICE_CONFIRMED else ""
            fp.write(
                f"### {i}. {f.priority} {f.kind} — `{f.function}()`{confirmed}\n\n"
            )
            fp.write(f"- Location: `{f.path}:{f.line}`\n")
            fp.write(f"- Root distance: {f.distance}\n")
            fp.write(f"- Call path: `{chain(f.function, parent)}`\n")
            fp.write(f"- Why: {f.detail}\n")
            fp.write(
                f"- Code: `{f.excerpt.replace(chr(96), chr(39))}`\n\n"
            )

        fp.write("## Reachable call graph\n\n")
        for name in sorted(dist, key=lambda n: (dist[n], n)):
            if name not in funcs:
                continue
            kids = sorted(x for x in graph.get(name, ()) if x in dist)
            fp.write(f"- d={dist[name]} `{name}()`")
            if kids:
                fp.write(" -> " + ", ".join(f"`{x}()`" for x in kids))
            fp.write("\n")

    print(
        f"parsed={len(funcs)} reachable={len(dist)} "
        f"findings={len(findings)}"
    )
    print(args.outdir / "r36s-level-load-report.md")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
