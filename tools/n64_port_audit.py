#!/usr/bin/env python3
"""Target-neutral entry point for N64 decomp/recomp host-port semantic checks.

The detector implementation still lives in r36s_semantic_audit.py for
backward compatibility. This wrapper supplies project configuration and is the
stable entry point for CI and future decomp profiles.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE / "port_profiles" / "goldeneye.json"
_IMPL = HERE / "r36s_semantic_audit.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help="JSON port profile (default: GoldenEye reference profile)",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
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

    missing = [p for p in roots if not Path(p).exists()]
    if missing:
        raise SystemExit(f"{profile_path}: missing source roots: {', '.join(missing)}")

    for group in ("binary_adapters", "verification"):
        entries = profile.get(group, {})
        if entries is not None and not isinstance(entries, dict):
            raise SystemExit(f"{profile_path}: {group} must be an object")
        for name, rel in (entries or {}).items():
            if not isinstance(rel, str) or not rel:
                raise SystemExit(f"{profile_path}: {group}.{name} must be a path string")
            if not Path(rel).exists():
                raise SystemExit(f"{profile_path}: {group}.{name} path not found: {rel}")

    os.environ["N64_PORT_AUDIT_PROFILE"] = str(profile_path)
    os.environ["N64_PORT_AUDIT_PROJECT"] = str(profile.get("project", profile_path.stem))
    os.environ["N64_PORT_AUDIT_CONTRACT_SUITE"] = str(profile.get("contract_suite", ""))
    os.environ["N64_PORT_AUDIT_ROOTS"] = os.pathsep.join(str(x) for x in roots)
    os.environ["N64_PORT_AUDIT_EXCLUDES"] = os.pathsep.join(str(x) for x in excludes)

    runpy.run_path(str(_IMPL), run_name="__main__")


if __name__ == "__main__":
    main()
