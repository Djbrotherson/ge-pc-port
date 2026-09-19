#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

SOURCE_GLOBS = (
    "src/**/*.c", "src/**/*.h",
    "port/src/**/*.c", "port/src/**/*.h",
    "port/fast3d/**/*.c", "port/fast3d/**/*.h",
)

POINTER_NAME = r"(?:ptr|pointer|addr|address|base|end|start|buf|buffer|data|node|model|prop|gdl|vtx|tile|room|portal)"
RULES = [
    ("P0", "ptr-to-32", re.compile(rf"\(\s*(?:s32|u32|int)\s*\)\s*(?:[A-Za-z_]\w*{POINTER_NAME}\w*|[^;\n]*->\w*(?:ptr|addr|data|node|model|prop|gdl|vtx)\w*)", re.I),
     "Pointer-like value is explicitly narrowed to 32 bits."),
    ("P0", "32-to-ptr-arithmetic", re.compile(r"\(\s*[A-Za-z_]\w*\s*\*\s*\)\s*\(?(?:\(\s*(?:s32|u32)\s*\)[^;\n]*[+\-&|]|[^;\n]*\(\s*(?:s32|u32)\s*\)[^;\n]*[+\-&|])"),
     "Pointer is reconstructed from arithmetic performed at 32-bit width."),
    ("P0", "ptr-compare-32", re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[^;\n]+(?:<|>|<=|>=|==|!=)[^;\n]+\(\s*(?:s32|u32)\s*\)"),
     "Comparison narrows both operands through 32-bit integers."),
    ("P0", "ptr-align-32", re.compile(r"\(\s*(?:s32|u32)\s*\)\s*[^;\n]+[+&]\s*(?:0x[0-9a-fA-F]+|~\s*\d+)"),
     "Address alignment/math appears to occur after 32-bit narrowing."),
    ("P1", "hardcoded-n64-address", re.compile(r"\b0x(?:7|8|9|A|B)[0-9A-Fa-f]{7}\b"),
     "Hard-coded N64-style virtual/physical address; verify whether it is serialized data or a host pointer."),
    ("P1", "pointer-stride-magic", re.compile(r"(?:<<\s*[23]|\*\s*(?:4|8|12|16|24|32))[^;\n]*(?:ptr|portal|room|model|node|prop)", re.I),
     "Magic stride near pointer/structure access; verify host structure layout."),
    ("P2", "neighbor-global-sentinel", re.compile(r"(?:end|limit)\s*=\s*\([^;\n]*\)&[A-Za-z_]\w*"),
     "End pointer is derived from another global/object; verify the objects are guaranteed contiguous."),
]

COMPILER_PATTERNS = (
    "pointer-to-int-cast",
    "int-to-pointer-cast",
    "int-conversion",
    "incompatible-pointer-types",
    "array-bounds",
    "stringop-overflow",
    "use-after-free",
)

@dataclass(frozen=True)
class Finding:
    priority: str
    kind: str
    path: str
    line: int
    text: str
    reason: str
    source: str

def source_findings(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[Path] = set()
    for glob in SOURCE_GLOBS:
        for path in repo.glob(glob):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            text = path.read_text(errors="replace")
            lines = text.splitlines()
            for priority, kind, rx, reason in RULES:
                for m in rx.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    excerpt = lines[line - 1].strip()[:240] if line <= len(lines) else m.group(0)[:240]
                    if excerpt.lstrip().startswith(("//", "/*", "*")):
                        continue
                    findings.append(Finding(priority, kind, str(path), line, excerpt, reason, "static"))
    return findings

def compiler_findings(path: Path | None) -> list[Finding]:
    if not path or not path.exists():
        return []
    out: list[Finding] = []
    rx = re.compile(r"^([^:\n]+\.(?:c|h)):(\d+):\d+: warning: (.*)$")
    for raw in path.read_text(errors="replace").splitlines():
        m = rx.match(raw)
        if not m:
            continue
        msg = m.group(3)
        if not any(p in msg for p in COMPILER_PATTERNS):
            continue
        priority = "P0" if any(p in msg for p in (
            "pointer-to-int-cast", "int-to-pointer-cast", "int-conversion"
        )) else "P1"
        out.append(Finding(priority, "compiler-warning", m.group(1), int(m.group(2)), raw[:240], msg, "compiler"))
    return out

def main() -> int:
    ap = argparse.ArgumentParser(description="Whole-port host compatibility audit")
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--warnings", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("compat-out"))
    ap.add_argument("--fail-on-new-p0", action="store_true")
    ap.add_argument("--baseline", type=Path)
    args = ap.parse_args()

    findings = source_findings(args.repo) + compiler_findings(args.warnings)
    unique = {(f.kind, f.path, f.line, f.text): f for f in findings}
    rank = {"P0": 0, "P1": 1, "P2": 2}
    findings = sorted(unique.values(), key=lambda f: (rank.get(f.priority, 9), f.path, f.line, f.kind))

    args.outdir.mkdir(parents=True, exist_ok=True)
    tsv = args.outdir / "compat-findings.tsv"
    with tsv.open("w", newline="") as fp:
        w = csv.writer(fp, delimiter="\t")
        w.writerow(["priority", "kind", "source", "path", "line", "reason", "text"])
        for f in findings:
            w.writerow([f.priority, f.kind, f.source, f.path, f.line, f.reason, f.text])

    counts = {p: sum(f.priority == p for f in findings) for p in ("P0", "P1", "P2")}
    report = args.outdir / "compat-report.md"
    with report.open("w") as fp:
        fp.write("# GoldenEye host-compatibility audit\n\n")
        fp.write("This is a review queue, not an automatic proof that every hit is a bug. ")
        fp.write("P0 is intentionally restricted to pointer-width/compiler evidence; serialized 32-bit N64 offsets still require semantic review.\n\n")
        fp.write("## Summary\n\n")
        fp.write(f"- P0: **{counts['P0']}**\n- P1: **{counts['P1']}**\n- P2: **{counts['P2']}**\n- Total: **{len(findings)}**\n\n")
        fp.write("## P0 queue\n\n")
        for i, f in enumerate((x for x in findings if x.priority == "P0"), 1):
            fp.write(f"{i}. `{f.path}:{f.line}` — **{f.kind}** ({f.source})\n")
            fp.write(f"   - {f.reason}\n   - `{f.text.replace(chr(96), chr(39))}`\n")
        fp.write("\n## P1/P2 queue\n\n")
        for f in (x for x in findings if x.priority != "P0"):
            fp.write(f"- {f.priority} `{f.path}:{f.line}` — {f.kind}: `{f.text.replace(chr(96), chr(39))}`\n")

    if args.baseline and args.baseline.exists():
        old = {
            tuple(line.rstrip("\n").split("\t")[:5])
            for line in args.baseline.read_text(errors="replace").splitlines()[1:]
            if line.strip()
        }
        new_p0 = [
            f for f in findings
            if f.priority == "P0" and (f.priority, f.kind, f.source, f.path, str(f.line)) not in old
        ]
        (args.outdir / "new-p0.tsv").write_text(
            "\n".join(f"{f.kind}\t{f.path}\t{f.line}\t{f.text}" for f in new_p0) + ("\n" if new_p0 else "")
        )
        if args.fail_on_new_p0 and new_p0:
            print(f"FAIL: {len(new_p0)} new P0 finding(s)")
            return 2

    print(f"P0={counts['P0']} P1={counts['P1']} P2={counts['P2']} total={len(findings)}")
    print(report)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
