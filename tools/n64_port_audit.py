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
    roots = profile.get("source_roots", [])
    excludes = profile.get("exclude_path_parts", [])

    if not roots:
        raise SystemExit(f"{profile_path}: source_roots must not be empty")

    os.environ["N64_PORT_AUDIT_PROFILE"] = str(profile_path)
    os.environ["N64_PORT_AUDIT_PROJECT"] = str(profile.get("project", profile_path.stem))
    os.environ["N64_PORT_AUDIT_ROOTS"] = os.pathsep.join(str(x) for x in roots)
    os.environ["N64_PORT_AUDIT_EXCLUDES"] = os.pathsep.join(str(x) for x in excludes)

    runpy.run_path(str(_IMPL), run_name="__main__")


if __name__ == "__main__":
    main()
