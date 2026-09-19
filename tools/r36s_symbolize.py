#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import re
from pathlib import Path

NM_RE = re.compile(r"^([0-9A-Fa-f]+)\s+([A-Za-z?])\s+(.+)$")

def load_symbols(path: Path):
    addrs=[]; rows=[]
    for raw in path.read_text(errors="replace").splitlines():
        m=NM_RE.match(raw.strip())
        if not m:
            continue
        addr=int(m.group(1),16)
        addrs.append(addr)
        rows.append((addr,m.group(2),m.group(3)))
    pairs=sorted(zip(addrs,rows), key=lambda x:x[0])
    return [p[0] for p in pairs],[p[1] for p in pairs]

def resolve(addrs,rows,value):
    i=bisect.bisect_right(addrs,value)-1
    if i<0:
        return None
    addr,typ,name=rows[i]
    return addr,typ,name,value-addr

def main():
    ap=argparse.ArgumentParser(description="Resolve R36S crash PC/LR addresses using nm output")
    ap.add_argument("symbols",type=Path)
    ap.add_argument("addresses",nargs="+")
    args=ap.parse_args()
    addrs,rows=load_symbols(args.symbols)
    if not rows:
        raise SystemExit("No symbols parsed")
    for raw in args.addresses:
        value=int(raw,0)
        hit=resolve(addrs,rows,value)
        if hit is None:
            print(f"{raw}: no lower symbol")
            continue
        addr,typ,name,off=hit
        print(f"{raw} -> {name}+0x{off:x} [0x{addr:x}, type={typ}]")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
