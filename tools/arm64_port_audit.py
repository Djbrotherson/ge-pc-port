#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOTS = ("src", "include", "port")
EXTS = {".c", ".h", ".cc", ".cpp", ".cxx", ".inc"}
SKIP = {"build-pc", "third_party", "vendor"}

RULES = [
    ("PTR_TO_32_CAST", "HIGH", "pointer-looking expression cast to 32-bit integer",
     re.compile(r"\((?:s32|u32|int|unsigned\s+int)\)\s*(?:\([^\n;]+\)|&?[A-Za-z_]\w*(?:->|\.)?\w*)")),
    ("PTR_ARITH_32", "HIGH", "pointer arithmetic/alignment performed through s32/u32",
     re.compile(r"\((?:s32|u32)\)\s*[A-Za-z_]\w*\s*[+\-^|&]")),
    ("PTR_XOR_32", "HIGH", "pointer XOR/toggle through u32/s32",
     re.compile(r"\((?:s32|u32)\)[^;\n]*\^[^;\n]*\((?:s32|u32)\)")),
    ("X86_64_ONLY_GUARD", "HIGH", "64-bit fix guarded for x86_64 but not aarch64",
     re.compile(r"^\s*#\s*(?:if|elif).*__x86_64__(?![^\n]*__aarch64__)")),
    ("OSMESG_32_CAST", "HIGH", "message pointer crosses a 32-bit cast",
     re.compile(r"(?:OSMesg|osSendMesg|osRecvMesg|msg|message)[^;\n]{0,100}\((?:s32|u32)\)|\((?:s32|u32)\)[^;\n]{0,100}(?:OSMesg|msg|message)", re.I)),
    ("POINTER_STORED_S32", "HIGH", "address assigned to s32/u32 storage",
     re.compile(r"\b(?:s32|u32)\s+[A-Za-z_]\w*\s*=\s*(?:\([^;\n]*\*\)|&[A-Za-z_])")),
    ("INT_TO_PTR_CAST", "MEDIUM", "32-bit-looking value converted directly to pointer",
     re.compile(r"\([A-Za-z_][\w\s]*\*\)\s*\(?\s*(?:\(s32\)|\(u32\)|[A-Za-z_]\w*(?:32|addr|address|offset|pos|ptrval)\w*)")),
    ("HARDCODED_PTR_STRIDE", "MEDIUM", "possible hard-coded pointer/struct stride",
     re.compile(r"\(\s*(?:u8|char)\s*\*\s*\)[^;\n]*[+\-]\s*(?:4|8)\b|\(\s*(?:s32|u32)\s*\*\s*\)[^;\n]*[+\-]\s*\d+")),
]

def source_files():
    for root in ROOTS:
        p = Path(root)
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if f.is_file() and f.suffix in EXTS and not any(x in SKIP for x in f.parts):
                yield f

def context(line):
    if "romptr_t" in line or "SegmentRom" in line or "CART_BASE" in line:
        return "may be intentional mapped N64/cart address"
    if "uintptr_t" in line or "intptr_t" in line:
        return "already uses pointer-width integer; inspect context"
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="arm64-port-audit.json")
    ap.add_argument("--markdown", default="arm64-port-audit.md")
    a = ap.parse_args()

    found = {}
    for path in source_files():
        try:
            lines = path.read_text(errors="replace").splitlines()
        except Exception:
            continue
        for n, line in enumerate(lines, 1):
            for rid, sev, desc, rx in RULES:
                if rx.search(line):
                    found[(rid, path.as_posix(), n)] = {
                        "rule": rid, "severity": sev, "description": desc,
                        "path": path.as_posix(), "line": n,
                        "code": line.strip()[:500], "context": context(line),
                    }

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings = sorted(found.values(), key=lambda x: (order.get(x["severity"], 9), x["path"], x["line"], x["rule"]))
    counts, by_rule = {}, {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        by_rule[f["rule"]] = by_rule.get(f["rule"], 0) + 1

    Path(a.json).write_text(json.dumps({
        "schema": 1, "scope": list(ROOTS), "counts": counts,
        "by_rule": by_rule, "findings": findings
    }, indent=2) + "\n")

    md = ["# ARM64 / 64-bit port audit", "",
          "Static scan for N64-era 32-bit assumptions. Findings are candidates, not automatic proof.", "",
          "## Summary", "",
          "- High: **%d**" % counts.get("HIGH", 0),
          "- Medium: **%d**" % counts.get("MEDIUM", 0),
          "- Total: **%d**" % len(findings), "",
          "## By rule", ""]
    for rid, num in sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0])):
        md.append("- %s: %d" % (rid, num))
    md += ["", "## High-confidence candidates", ""]
    highs = [f for f in findings if f["severity"] == "HIGH"]
    for f in highs[:300]:
        extra = (" — " + f["context"]) if f["context"] else ""
        md.append("- **%s** %s:%d%s" % (f["rule"], f["path"], f["line"], extra))
        md.append("  - " + f["code"])
    if len(highs) > 300:
        md.append("- %d more HIGH findings are in the JSON artifact." % (len(highs) - 300))
    md += ["", "## Review order", "",
           "1. HIGH findings manipulating real host pointers.",
           "2. x86_64-only guards missing AArch64.",
           "3. Message/callback/function arguments stored through s32/u32.",
           "4. MEDIUM findings after excluding intentional N64/cart addresses.", ""]
    Path(a.markdown).write_text("\n".join(md))
    print("ARM64 audit: HIGH=%d MEDIUM=%d TOTAL=%d" %
          (counts.get("HIGH", 0), counts.get("MEDIUM", 0), len(findings)))

if __name__ == "__main__":
    main()
