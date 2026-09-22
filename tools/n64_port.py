#!/usr/bin/env python3
"""Unified CLI for the reusable N64 decomp/recomp porting toolset."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "tools" / "port_profiles" / "goldeneye.json"


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text())
    if profile.get("schema_version") != 1:
        raise ValueError(f"unsupported schema_version {profile.get('schema_version')!r}")
    if not isinstance(profile.get("project"), str) or not profile["project"]:
        raise ValueError("project must be a non-empty string")
    roots = profile.get("source_roots")
    if not isinstance(roots, list) or not roots:
        raise ValueError("source_roots must be a non-empty list")
    return profile


def repo_path(rel: str) -> Path:
    return ROOT / rel


def doctor(profile_path: Path, profile: dict) -> int:
    failures: list[str] = []
    notices: list[str] = []

    for rel in profile.get("source_roots", []):
        if not repo_path(rel).is_dir():
            failures.append(f"missing source root: {rel}")

    abi = profile.get("abi_contract")
    if abi and not repo_path(abi).is_file():
        failures.append(f"missing ABI contract: {abi}")

    for group in ("binary_adapters", "verification"):
        entries = profile.get(group, {}) or {}
        if not isinstance(entries, dict):
            failures.append(f"{group} must be an object")
            continue
        for name, rel in entries.items():
            if not isinstance(rel, str) or not repo_path(rel).exists():
                failures.append(f"missing {group}.{name}: {rel}")

    targets = profile.get("targets", [])
    if not targets:
        notices.append("no targets declared")
    else:
        for target in targets:
            tid = target.get("id", "<unnamed>")
            arch = target.get("arch")
            bits = target.get("pointer_bits")
            gfx = target.get("graphics")
            if not arch or bits not in (32, 64):
                failures.append(f"target {tid}: arch/pointer_bits incomplete")
            notices.append(f"target {tid}: arch={arch} ptr={bits} graphics={gfx}")

    print(f"project: {profile['project']}")
    print(f"profile: {profile_path.relative_to(ROOT) if profile_path.is_relative_to(ROOT) else profile_path}")
    print(f"contract suite: {profile.get('contract_suite') or '<generic-only>'}")
    if abi:
        print(f"ABI contract: {abi}")
    for n in notices:
        print(f"NOTE: {n}")
    for f in failures:
        print(f"ERROR: {f}", file=sys.stderr)

    if failures:
        print(f"doctor: FAIL ({len(failures)} problem(s))", file=sys.stderr)
        return 2
    print("doctor: PASS")
    return 0


def audit(profile_path: Path) -> int:
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "n64_port_audit.py"),
        "--profile",
        str(profile_path),
    ]
    return subprocess.call(cmd, cwd=ROOT)


def show(profile: dict) -> int:
    print(json.dumps(profile, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="n64-port")
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help="port profile JSON",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="validate profile, adapters, contracts and targets")
    sub.add_parser("audit", help="run semantic + project contract audit")
    sub.add_parser("show-profile", help="print the resolved profile")

    args = parser.parse_args()
    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = (Path.cwd() / profile_path).resolve()

    try:
        profile = load_profile(profile_path)
    except Exception as exc:
        print(f"{profile_path}: {exc}", file=sys.stderr)
        return 2

    if args.command == "doctor":
        return doctor(profile_path, profile)
    if args.command == "audit":
        return audit(profile_path)
    if args.command == "show-profile":
        return show(profile)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
