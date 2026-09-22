#!/usr/bin/env python3
"""Target-neutral entry point for N64 decomp/recomp host-port semantic checks.

The detector engine lives in port_audit_engine.py. This wrapper supplies
repository/project configuration for the current integration CI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_PROFILE = HERE / "integration_profiles" / "goldeneye.json"
_IMPL = HERE / "port_audit_engine.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help="JSON port profile (default: GoldenEye reference profile)",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = (ROOT / profile_path).resolve()
    profile = json.loads(profile_path.read_text())
    if profile.get("schema_version") != 1:
        raise SystemExit(f"{profile_path}: unsupported schema_version {profile.get('schema_version')!r}")
    if not isinstance(profile.get("project"), str) or not profile["project"].strip():
        raise SystemExit(f"{profile_path}: project must be a non-empty string")

    roots = profile.get("source_roots", [])
    excludes = profile.get("exclude_path_parts", [])
    if not isinstance(roots, list) or not roots or not all(isinstance(x, str) and x for x in roots):
        raise SystemExit(f"{profile_path}: source_roots must be a non-empty string list")
    if not isinstance(excludes, list) or not all(isinstance(x, str) and x for x in excludes):
        raise SystemExit(f"{profile_path}: exclude_path_parts must be a string list")

    missing = [p for p in roots if not (ROOT / p).exists()]
    if missing:
        raise SystemExit(f"{profile_path}: missing source roots: {', '.join(missing)}")

    abi_contract = profile.get("abi_contract", "")
    if abi_contract:
        if not isinstance(abi_contract, str):
            raise SystemExit(f"{profile_path}: abi_contract must be a path string")
        if not (ROOT / abi_contract).exists():
            raise SystemExit(f"{profile_path}: abi_contract path not found: {abi_contract}")

    for group in ("binary_adapters", "verification"):
        entries = profile.get(group, {})
        if entries is not None and not isinstance(entries, dict):
            raise SystemExit(f"{profile_path}: {group} must be an object")
        for name, rel in (entries or {}).items():
            if not isinstance(rel, str) or not rel:
                raise SystemExit(f"{profile_path}: {group}.{name} must be a path string")
            if not (ROOT / rel).exists():
                raise SystemExit(f"{profile_path}: {group}.{name} path not found: {rel}")

    os.environ["N64_PORT_AUDIT_PROFILE"] = str(profile_path)
    os.environ["N64_PORT_AUDIT_PROJECT"] = str(profile.get("project", profile_path.stem))
    os.environ["N64_PORT_AUDIT_CONTRACT_SUITE"] = str(profile.get("contract_suite", ""))
    os.environ["N64_PORT_AUDIT_ABI_CONTRACT"] = str((ROOT / abi_contract).resolve()) if abi_contract else ""
    os.environ["N64_PORT_AUDIT_ROOTS"] = os.pathsep.join(str(x) for x in roots)
    os.environ["N64_PORT_AUDIT_EXCLUDES"] = os.pathsep.join(str(x) for x in excludes)

    old_cwd = Path.cwd()
    try:
        os.chdir(ROOT)
        runpy.run_path(str(_IMPL), run_name="__main__")
    finally:
        os.chdir(old_cwd)


if __name__ == "__main__":
    main()
