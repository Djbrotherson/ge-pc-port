#!/usr/bin/env python3
"""Apply explicit semantic decisions to Portkit hazards.

Decisions are intentionally human-authored or tool-assisted facts. Portkit never
guesses an ambiguous pointer/address class merely to make generation proceed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_CLASSES={
    "host_pointer",
    "n64_virtual_address",
    "n64_physical_address",
    "rom_address",
    "segmented_address",
    "serialized_offset",
    "linker_token",
    "scalar",
    "gbi_word",
    "wire_token",
    "false_positive",
}

def key(x:dict)->tuple:
    return (x.get("path"),int(x.get("line",0)),x.get("kind"))

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("inventory",type=Path)
    ap.add_argument("decisions",type=Path)
    ap.add_argument("--out",type=Path,default=Path("classified-inventory.json"))
    args=ap.parse_args()

    inv=json.loads(args.inventory.read_text())
    decisions=json.loads(args.decisions.read_text())
    if inv.get("schema")!=1:
        raise SystemExit("unsupported inventory schema")
    if decisions.get("schema")!=1:
        raise SystemExit("unsupported decisions schema")

    decision_map={}
    for d in decisions.get("decisions",[]):
        cls=d.get("class")
        if cls not in ALLOWED_CLASSES:
            raise SystemExit(f"invalid semantic class {cls!r}")
        k=key(d)
        if k in decision_map:
            raise SystemExit(f"duplicate decision for {k}")
        decision_map[k]=d

    applied=[]
    unresolved=[]
    stale=set(decision_map)
    hazards=[]
    for h in inv.get("hazards",[]):
        k=key(h)
        d=decision_map.get(k)
        item=dict(h)
        if d:
            item["semantic_class"]=d["class"]
            item["decision_reason"]=d.get("reason","")
            item["decision_source"]=d.get("source","manual")
            applied.append(k)
            stale.discard(k)
        else:
            item["semantic_class"]="unknown"
            if h.get("severity")=="P0":
                unresolved.append(k)
        hazards.append(item)

    out=dict(inv)
    out["hazards"]=hazards
    out["classification"]={
        "schema":1,
        "applied":len(applied),
        "unresolved_p0":len(unresolved),
        "stale_decisions":[{"path":p,"line":l,"kind":k} for p,l,k in sorted(stale)],
        "ready_for_contract":len(unresolved)==0 and not stale,
    }
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print(
        f"applied={len(applied)} unresolved_p0={len(unresolved)} "
        f"stale={len(stale)} ready={out['classification']['ready_for_contract']}"
    )
    return 0 if out["classification"]["ready_for_contract"] else 2

if __name__=="__main__":
    raise SystemExit(main())
