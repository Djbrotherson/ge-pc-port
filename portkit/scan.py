#!/usr/bin/env python3
"""
n64-portkit static discovery pass.

Goal: turn an arbitrary N64 decomp into a machine-readable portability
inventory before any host-port code is written. This is intentionally
conservative: it discovers surfaces and hazards; it does not rewrite code.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_EXTS = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".s", ".S", ".asm"}
DEFAULT_ROOTS = ("src", "include", "assets", "rsp", "lib", "ultra")

API_GROUPS = {
    "threads_messages": (
        "osCreateThread", "osStartThread", "osStopThread", "osYieldThread",
        "osCreateMesgQueue", "osSendMesg", "osRecvMesg", "osSetEventMesg",
    ),
    "timers_time": (
        "osGetTime", "osGetCount", "osSetTimer", "osStopTimer",
    ),
    "video": (
        "osViSetMode", "osViSwapBuffer", "osViBlack", "osViSetSpecialFeatures",
        "osViSetEvent", "osViGetCurrentFramebuffer", "osViGetNextFramebuffer",
    ),
    "rsp_rdp": (
        "osSpTaskLoad", "osSpTaskStartGo", "osSpTaskYield", "osSpTaskYielded",
        "osDpSetNextBuffer", "osDpGetStatus", "osDpSetStatus",
    ),
    "audio": (
        "osAiSetFrequency", "osAiSetNextBuffer", "osAiGetLength",
    ),
    "controllers": (
        "osContInit", "osContStartReadData", "osContGetReadData",
        "osContSetCh", "osContReset",
    ),
    "save_accessory": (
        "osEepromProbe", "osEepromRead", "osEepromWrite", "osEepromLongRead",
        "osEepromLongWrite", "osPfsInit", "osPfsIsPlug", "osMotorInit",
        "osMotorStart", "osMotorStop",
    ),
    "pi_cart": (
        "osPiStartDma", "osPiRawStartDma", "osPiGetStatus", "osPiCreateManager",
    ),
    "cache_tlb_cpu": (
        "osWritebackDCache", "osInvalDCache", "osInvalICache",
        "osMapTLB", "osUnmapTLBAll", "osSetTLBASID", "osSetFpcCsr",
    ),
}

GBI_RX = re.compile(r"\b(?:g[DS]P|gs[DS]P|G_)[A-Za-z0-9_]+\b")
PTR_NARROW_RX = re.compile(
    r"\(\s*(?:u32|s32|unsigned\s+int|int)\s*\)\s*"
    r"(?:&\s*)?(?:[A-Za-z_]\w*(?:\s*->\s*\w+|\s*\[[^\]]+\])?)"
)
INT_TO_PTR_RX = re.compile(
    r"\(\s*(?:void|char|u8|s8|u16|s16|u32|s32|Gfx|Vtx|Mtx|"
    r"[A-Za-z_]\w*)\s*\*\s*\)\s*(?:0x[0-9A-Fa-f]+|[A-Za-z_]\w*)"
)
N64_ADDR_RX = re.compile(r"\b0x(?:[89ABab][0-9A-Fa-f]{7}|[0-7][0-9A-Fa-f]{7})\b")
BE_RX = re.compile(r"\b(?:bswap(?:16|32|64)?|__builtin_bswap(?:16|32|64)|BE(?:16|32|64)|big.?endian)\b", re.I)
ROM_TOKEN_RX = re.compile(r"\b(?:SegmentRom|SegmentStart|SegmentEnd|_rom_start|_rom_end|romptr|IMAGESEG)\w*\b")
ASM_OP_RX = re.compile(r"\b(?:mfc0|mtc0|cache|eret|tlbp|tlbr|tlbwi|tlbwr)\b", re.I)

def load_profile(path: Path | None) -> dict:
    if path is None:
        return {}
    return json.loads(path.read_text())

def iter_files(repo: Path, roots: list[str], excludes: list[str]):
    seen = set()
    for root in roots:
        p = repo / root
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file() or f.suffix not in SOURCE_EXTS:
                continue
            rel = f.relative_to(repo).as_posix()
            if any(rel.startswith(x.rstrip("/") + "/") or rel == x.rstrip("/") for x in excludes):
                continue
            if rel not in seen:
                seen.add(rel)
                yield rel, f

def line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--profile", type=Path)
    ap.add_argument("--out", type=Path, default=Path("portkit-out"))
    args = ap.parse_args()

    repo = args.repo.resolve()
    profile = load_profile(args.profile)
    roots = profile.get("source_roots", list(DEFAULT_ROOTS))
    excludes = profile.get("exclude_roots", [".git", "build", "build-pc"])

    api_hits = defaultdict(list)
    gbi = Counter()
    build = set()
    hazards = []
    asm_files = []
    endian_files = set()
    rom_token_files = set()
    source_count = 0

    for rel, path in iter_files(repo, roots, excludes):
        source_count += 1
        text = path.read_text(errors="replace")

        if path.suffix in {".s", ".S", ".asm"}:
            asm_files.append(rel)
            for m in ASM_OP_RX.finditer(text):
                hazards.append({
                    "severity": "P1",
                    "kind": "cpu-specific-asm",
                    "path": rel,
                    "line": line_no(text, m.start()),
                    "token": m.group(0),
                })

        for group, names in API_GROUPS.items():
            for name in names:
                for m in re.finditer(r"\b" + re.escape(name) + r"\s*\(", text):
                    api_hits[group].append({
                        "api": name, "path": rel, "line": line_no(text, m.start())
                    })

        for m in GBI_RX.finditer(text):
            gbi[m.group(0)] += 1

        for kind, rx, sev in (
            ("pointer-to-32", PTR_NARROW_RX, "P0"),
            ("integer-to-pointer", INT_TO_PTR_RX, "P0"),
            ("n64-address-literal", N64_ADDR_RX, "P1"),
        ):
            for m in rx.finditer(text):
                hazards.append({
                    "severity": sev,
                    "kind": kind,
                    "path": rel,
                    "line": line_no(text, m.start()),
                    "token": m.group(0)[:160],
                })

        if BE_RX.search(text):
            endian_files.add(rel)
        if ROM_TOKEN_RX.search(text):
            rom_token_files.add(rel)

    for name in ("CMakeLists.txt", "Makefile", "meson.build", "build.ninja"):
        if (repo / name).exists():
            build.add(name)
    if (repo / ".github" / "workflows").exists():
        build.add(".github/workflows")

    categories = {}
    for group in API_GROUPS:
        hits = api_hits[group]
        categories[group] = {
            "count": len(hits),
            "apis": dict(sorted(Counter(h["api"] for h in hits).items())),
            "examples": hits[:20],
        }

    p0 = [h for h in hazards if h["severity"] == "P0"]
    p1 = [h for h in hazards if h["severity"] == "P1"]

    report = {
        "schema": 1,
        "profile": profile.get("name"),
        "source_files": source_count,
        "build_systems": sorted(build),
        "hardware_surfaces": categories,
        "gbi_tokens": dict(gbi.most_common()),
        "assembly_files": sorted(asm_files),
        "endian_sensitive_files": sorted(endian_files),
        "rom_or_segment_token_files": sorted(rom_token_files),
        "hazards": hazards,
        "summary": {
            "p0": len(p0),
            "p1": len(p1),
            "gbi_unique": len(gbi),
            "assembly_files": len(asm_files),
            "endian_sensitive_files": len(endian_files),
            "rom_or_segment_token_files": len(rom_token_files),
        },
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inventory.json").write_text(json.dumps(report, indent=2) + "\n")

    md = [
        "# N64 Portkit discovery report",
        "",
        f"- Profile: **{report['profile'] or 'generic'}**",
        f"- Source files scanned: **{source_count}**",
        f"- P0 host-width hazards: **{len(p0)}**",
        f"- P1 architecture/layout findings: **{len(p1)}**",
        f"- Unique GBI tokens: **{len(gbi)}**",
        f"- Assembly files: **{len(asm_files)}**",
        "",
        "## Hardware surfaces",
        "",
    ]
    for group, data in categories.items():
        md.append(f"- **{group}**: {data['count']} call sites, {len(data['apis'])} APIs")
    md += [
        "",
        "## Porting order",
        "",
        "1. Classify P0 values as host pointers versus serialized/N64 address tokens.",
        "2. Replace or shim OS/hardware surfaces by category.",
        "3. Establish ROM/segment mapping and endian conversion boundaries.",
        "4. Bind the display-list path to a renderer backend and validate GBI deltas.",
        "5. Bind audio, input, saves, timing, and filesystem services.",
        "6. Only then add game-specific enhancements such as widescreen, upscaling, mods, or unlocked FPS.",
        "",
        "This scanner intentionally does not auto-rewrite ambiguous pointer/address code.",
        "",
    ]
    (args.out / "report.md").write_text("\n".join(md))
    print(json.dumps(report["summary"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
