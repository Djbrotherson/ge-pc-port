#!/usr/bin/env python3
"""Reduce a Portkit discovery inventory to a runtime-neutral host contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SURFACE_TO_CAPABILITY = {
    "threads_messages": "os.threads_messages",
    "timers_time": "os.timers_time",
    "video": "video.vi",
    "rsp_rdp": "graphics.rsp_rdp",
    "audio": "audio.ai",
    "controllers": "input.controllers",
    "save_accessory": "storage.save_accessory",
    "pi_cart": "rom.pi_cart",
    "cache_tlb_cpu": "cpu.cache_tlb",
}

def require_surface(inv: dict, surface: str) -> bool:
    data = inv.get("hardware_surfaces", {}).get(surface, {})
    return int(data.get("count", 0)) > 0

def build_contract(inv: dict) -> dict:
    requirements = []
    for surface, capability in SURFACE_TO_CAPABILITY.items():
        if require_surface(inv, surface):
            data = inv["hardware_surfaces"][surface]
            requirements.append({
                "capability": capability,
                "source_surface": surface,
                "call_sites": data.get("count", 0),
                "apis": sorted(data.get("apis", {}).keys()),
            })

    if int(inv.get("summary", {}).get("gbi_unique", 0)) > 0:
        requirements.append({
            "capability": "graphics.gbi",
            "source_surface": "gbi_tokens",
            "tokens": sorted(inv.get("gbi_tokens", {}).keys()),
        })

    endian_files = inv.get("endian_sensitive_files", [])
    token_files = inv.get("rom_or_segment_token_files", [])
    if endian_files or token_files:
        requirements.append({
            "capability": "data.n64_serialization",
            "source_surface": "serialized_data",
            "endian_sensitive_files": len(endian_files),
            "rom_or_segment_token_files": len(token_files),
        })

    if int(inv.get("summary", {}).get("assembly_files", 0)) > 0:
        requirements.append({
            "capability": "cpu.arch_specific_code",
            "source_surface": "assembly_files",
            "files": inv.get("assembly_files", []),
        })

    hazards = inv.get("hazards", [])
    classified = "classification" in inv
    unresolved = {
        "P0": sum(
            1 for h in hazards
            if h.get("severity") == "P0"
            and (not classified or h.get("semantic_class", "unknown") == "unknown")
        ),
        "P1": sum(1 for h in hazards if h.get("severity") == "P1"),
    }

    return {
        "schema": 1,
        "profile": inv.get("profile"),
        "requirements": requirements,
        "unresolved": unresolved,
        "ready_for_generation": unresolved["P0"] == 0,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory", type=Path)
    ap.add_argument("--out", type=Path, default=Path("host-contract.json"))
    args = ap.parse_args()

    inv = json.loads(args.inventory.read_text())
    if inv.get("schema") != 1:
        raise SystemExit(f"unsupported inventory schema: {inv.get('schema')!r}")

    contract = build_contract(inv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(contract, indent=2) + "\n")

    print(
        f"requirements={len(contract['requirements'])} "
        f"P0={contract['unresolved']['P0']} "
        f"P1={contract['unresolved']['P1']} "
        f"ready={contract['ready_for_generation']}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
