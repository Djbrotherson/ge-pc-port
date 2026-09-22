#!/usr/bin/env python3
"""Resolve a Portkit host contract against one or more backend capability descriptors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("contract",type=Path)
    ap.add_argument("descriptors",nargs="+",type=Path)
    ap.add_argument("--out",type=Path,default=Path("portkit-resolution.json"))
    args=ap.parse_args()

    contract=json.loads(args.contract.read_text())
    required={r["capability"] for r in contract.get("requirements",[])}
    provided=set()
    descriptors=[]
    for path in args.descriptors:
        d=json.loads(path.read_text())
        if d.get("schema")!=1:
            raise SystemExit(f"unsupported descriptor schema in {path}")
        provides=set(d.get("provides",[]))
        provided |= provides
        descriptors.append({
            "name":d.get("name",path.stem),
            "kind":d.get("kind","backend"),
            "provides":sorted(provides),
        })

    missing=sorted(required-provided)
    extra=sorted(provided-required)
    out={
        "schema":1,
        "profile":contract.get("profile"),
        "descriptors":descriptors,
        "required":sorted(required),
        "provided":sorted(provided),
        "missing":missing,
        "extra":extra,
        "resolved":not missing and contract.get("unresolved",{}).get("P0",0)==0,
        "semantic_p0":contract.get("unresolved",{}).get("P0",0),
    }
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print(f"required={len(required)} provided={len(provided)} missing={len(missing)} resolved={out['resolved']}")
    return 0 if out["resolved"] else 2

if __name__=="__main__":
    raise SystemExit(main())
