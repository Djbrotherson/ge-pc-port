#!/usr/bin/env python3
"""Group GCC/Clang diagnostics into semantic batch candidates.

Consumes a build log and emits machine-readable groups rather than treating
every warning as an independent task. Designed for decomp/source-port bring-up.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DIAG = re.compile(
    r"(?P<path>[^\s:][^:]*):(?P<line>\d+):(?P<col>\d+): "
    r"(?P<level>warning|error): (?P<message>.*?)(?: \[-W(?P<flag>[^\]]+)\])?$"
)
CALLEE = re.compile(
    r"(?:argument \d+ of|passing argument \d+ of) [‘']([^’']+)[’']|"
    r"(?:assignment to|initialization of|returning) [‘']([^’']+)[’']"
)
TYPE_NOTE = re.compile(
    r"note: expected [‘']([^’']+)[’'] but argument is of type [‘']([^’']+)[’']"
)

def clean(line: str) -> str:
    # GitHub Actions prepends timestamps and sometimes ANSI/control prefixes.
    m = re.search(r"/(?:home|workspace|mnt|build|src)/.*", line)
    return m.group(0) if m else line.strip()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--out", type=Path, default=Path("warning-triage.json"))
    ap.add_argument("--markdown", type=Path)
    ap.add_argument("--policy", type=Path, help="optional semantic-scope warning policy")
    args = ap.parse_args()

    policy = {"ignore_scopes": [], "core_options": []}
    if args.policy:
        loaded = json.loads(args.policy.read_text())
        if loaded.get("schema") != 1:
            raise SystemExit("unsupported warning policy schema")
        policy.update(loaded)

    raw = args.log.read_text(errors="replace").splitlines()
    diags = []
    for i, original in enumerate(raw):
        line = clean(original)
        m = DIAG.search(line)
        if not m:
            continue
        d = m.groupdict()
        d["line"] = int(d["line"])
        d["col"] = int(d["col"])
        d["callee"] = None
        cm = CALLEE.search(d["message"])
        if cm:
            d["callee"] = next((x for x in cm.groups() if x), None)

        # GCC prints the expected/actual type note within the following lines.
        d["expected_type"] = None
        d["actual_type"] = None
        norm_path = d["path"].replace("\\", "/")
        d["scope"] = (
            "ignored"
            if any(scope in norm_path for scope in policy.get("ignore_scopes", []))
            else "core"
        )
        for follow in raw[i + 1:i + 10]:
            nm = TYPE_NOTE.search(follow)
            if nm:
                d["expected_type"], d["actual_type"] = nm.groups()
                break
        diags.append(d)

    by_flag = Counter((d["flag"] or d["message"]) for d in diags)
    by_file = Counter(d["path"] for d in diags)
    by_callee = Counter(d["callee"] for d in diags if d["callee"])
    by_pair = Counter(
        f"{d['actual_type']} -> {d['expected_type']}"
        for d in diags if d["actual_type"] and d["expected_type"]
    )

    # High-value first: ABI, pointer-width, ownership, layout and undefined-state
    # classes. Broad decomp noise remains visible but ranks below them.
    risk_flags = {
        "pointer-to-int-cast", "int-to-pointer-cast", "int-conversion",
        "incompatible-pointer-types", "array-bounds=", "array-bounds",
        "discarded-qualifiers", "uninitialized", "maybe-uninitialized",
        "overflow", "format", "return-type", "cast-function-type",
        "strict-aliasing",
    }
    high = [
        d for d in diags
        if d["level"] == "error" or (d["flag"] in risk_flags)
    ]

    core_options = set(policy.get("core_options", []))
    core_contract = [
        d for d in diags
        if d["scope"] == "core"
        and d["level"] == "warning"
        and d["flag"] in core_options
    ]

    result = {
        "schema": 1,
        "diagnostics": len(diags),
        "errors": sum(d["level"] == "error" for d in diags),
        "warnings": sum(d["level"] == "warning" for d in diags),
        "high_signal": len(high),
        "core_diagnostics": sum(d["scope"] == "core" for d in diags),
        "ignored_diagnostics": sum(d["scope"] == "ignored" for d in diags),
        "core_contract_violations": len(core_contract),
        "contract_violations": core_contract,
        "groups": {
            "flag": by_flag.most_common(),
            "file": by_file.most_common(),
            "callee": by_callee.most_common(),
            "type_pair": by_pair.most_common(),
        },
        "high_signal_diagnostics": high,
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")

    if args.markdown:
        md = [
            "# Portkit compiler triage", "",
            f"- Diagnostics: **{result['diagnostics']}**",
            f"- Errors: **{result['errors']}**",
            f"- Warnings: **{result['warnings']}**",
            f"- High-signal: **{result['high_signal']}**",
            f"- Core contract violations: **{result['core_contract_violations']}**", "",
            "## Batch order", "",
            "1. Fix errors and pointer-width/address-token violations.",
            "2. Group incompatible pointer diagnostics by actual → expected type.",
            "3. Correct shared API/prototype or storage-view boundaries before call sites.",
            "4. Fix local declaration errors and owner-slot/pointer-to-pointer conventions.",
            "5. Rebuild once and compare warning-class deltas.",
            "6. Leave broad decomp-noise classes until semantic classes are exhausted.",
            "", "## Top type pairs", "",
        ]
        for name, count in by_pair.most_common(25):
            md.append(f"- **{count}×** `{name}`")
        md += ["", "## Top callees", ""]
        for name, count in by_callee.most_common(25):
            md.append(f"- **{count}×** `{name}`")
        md += ["", "## Top files", ""]
        for name, count in by_file.most_common(25):
            md.append(f"- **{count}×** `{name}`")
        args.markdown.write_text("\n".join(md) + "\n")

    print(json.dumps({
        "errors": result["errors"],
        "warnings": result["warnings"],
        "high_signal": result["high_signal"],
        "core_contract_violations": result["core_contract_violations"],
    }, sort_keys=True))
    return 1 if result["errors"] else (2 if result["core_contract_violations"] else 0)

if __name__ == "__main__":
    raise SystemExit(main())
