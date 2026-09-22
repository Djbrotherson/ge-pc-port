#!/usr/bin/env python3
"""Single-command orchestration for the N64 Portkit pipeline."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def run(args:list[str], allow_fail:bool=False)->subprocess.CompletedProcess:
    p=subprocess.run(args,text=True,capture_output=True)
    if p.returncode and not allow_fail:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit(p.returncode)
    return p

def main()->int:
    ap=argparse.ArgumentParser(prog="portkit")
    sub=ap.add_subparsers(dest="cmd",required=True)

    p=sub.add_parser("analyze",help="scan, validate, build host contract and resolve capabilities")
    p.add_argument("--repo",type=Path,default=Path("."))
    p.add_argument("--profile",type=Path,required=True)
    p.add_argument("--decisions",type=Path,help="optional semantic decision file")
    p.add_argument("--backend",type=Path,action="append",default=[])
    p.add_argument("--target",type=Path,action="append",default=[])
    p.add_argument("--out",type=Path,default=Path("portkit-out"))

    p=sub.add_parser("scaffold",help="generate adapter skeleton from an existing analysis")
    p.add_argument("--analysis",type=Path,default=Path("portkit-out"))
    p.add_argument("--profile",type=Path,help="optional profile for layout contracts")
    p.add_argument("--out",type=Path,default=Path("generated-portkit"))
    p.add_argument("--force",action="store_true")

    args=ap.parse_args()

    if args.cmd=="analyze":
        out=args.out
        out.mkdir(parents=True,exist_ok=True)
        inventory=out/"inventory.json"
        classified=out/"classified-inventory.json"
        validation=out/"validation.json"
        contract=out/"host-contract.json"
        resolution=out/"resolution.json"

        run([sys.executable,str(HERE/"scan.py"),"--repo",str(args.repo),
             "--profile",str(args.profile),"--out",str(out)])
        validation_run=run([sys.executable,str(HERE/"validate.py"),"--repo",str(args.repo),
                            "--out",str(validation)],allow_fail=True)
        contract_input=inventory
        classification_rc=None
        if args.decisions:
            cr=run([sys.executable,str(HERE/"classify.py"),str(inventory),
                    str(args.decisions),"--out",str(classified)],allow_fail=True)
            classification_rc=cr.returncode
            contract_input=classified
        run([sys.executable,str(HERE/"contract.py"),str(contract_input),"--out",str(contract)])

        descriptors=[*args.backend,*args.target]
        resolution_rc=None
        if descriptors:
            rr=run([sys.executable,str(HERE/"resolve.py"),str(contract),
                    *map(str,descriptors),"--out",str(resolution)],allow_fail=True)
            resolution_rc=rr.returncode

        inv=json.loads(inventory.read_text())
        val=json.loads(validation.read_text())
        con=json.loads(contract.read_text())
        summary={
            "schema":1,
            "profile":inv.get("profile"),
            "inventory":inv.get("summary",{}),
            "validation":val.get("summary",{}),
            "classification_checked":bool(args.decisions),
            "classification_ready":classification_rc==0 if args.decisions else None,
            "contract_requirements":len(con.get("requirements",[])),
            "contract_ready":con.get("ready_for_generation",False),
            "resolution_checked":bool(descriptors),
            "resolution_ready":resolution_rc==0 if descriptors else None,
        }
        (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
        print(json.dumps(summary,sort_keys=True))
        return 2 if val.get("summary",{}).get("P0",0) or not con.get("ready_for_generation",False) else 0

    if args.cmd=="scaffold":
        contract=args.analysis/"host-contract.json"
        if not contract.exists():
            raise SystemExit(f"missing {contract}; run 'portkit analyze' first")
        cmd=[sys.executable,str(HERE/"generate.py"),str(contract),"--out",str(args.out)]
        if args.profile:
            cmd += ["--profile",str(args.profile)]
        if args.force:
            cmd.append("--force")
        return run(cmd,allow_fail=True).returncode

    return 2

if __name__=="__main__":
    raise SystemExit(main())
