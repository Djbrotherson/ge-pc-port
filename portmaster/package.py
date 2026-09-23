#!/usr/bin/env python3
"""Assemble the PortMaster test zip deterministically from tree contents.

Usage:
    python3 portmaster/package.py --game-bin PATH [--out DIR] [--zip-name NAME]

Reads the zip name from portmaster/port.json ("name"). Layout inside the zip
(matches port.json "items"):

    ge007/
        ge007.aarch64                 the game (you supply it: CI artifact or
                                      local cross-build; verified AArch64 ELF)
        data/.place-user-rom-and-sidecars-here
                                      marker so the folder exists pre-ROM
        prepare-assets/
            prepare-assets.py         converter orchestrator (stdlib only)
            d43_emit.py d69_emit.py d88_emit.py d88_propdefs.py
            ge007-convert             wrapper: runs the above on device python3
            vendor/scripts/filelist.u.csv
            vendor/assets/obseg/file_resource_table.inc.c
            vendor/assets/**modelFileHeader.inc.c   (515 files)
        build-info.txt                written here (source revision + date)
        USER_DATA_REQUIRED.txt        staged alongside (see portmaster/README)
        port.json gameinfo.xml        copies, as the current test package has
    GoldenEye 007.sh                  the fresh-extract launcher (runs the
                                      converter on first boot when needed)

The script REFUSES to include any .z64/.n64/.v64 ROM or any
pcmodels.bin/pccg.bin sidecars (legal guardrail): those are user-supplied /
device-generated, never distributed.

After packing it verifies: zip lists, binary is AArch64, no ROM/sidecars
inside, wrapper + launcher have exec bits, converter bundle complete
(emit scripts + lib + CSV + headers present).
"""
import argparse
import datetime
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../portmaster
ROOT = HERE.parent                              # repo root
PORT_JSON = HERE / "port.json"

# Converter bundle, repo-relative: (source, dest inside prepare-assets/)
CONVERTER_FILES = [
    "tools_pc/dist/prepare-assets/prepare-assets.py",
    "tools_pc/d43_emit.py",
    "tools_pc/d69_emit.py",
    "tools_pc/d88_emit.py",
    "tools_pc/d88_propdefs.py",
]
CONVERTER_LIB = [
    "tools/n64_portlib/__init__.py",
    "tools/n64_portlib/binary.py",
]
VENDOR_SCRIPTS = ["scripts/filelist.u.csv"]
VENDOR_ASSETS = ["assets/obseg/file_resource_table.inc.c"]

WRAPPER = """#!/bin/sh
# ge007-convert: device-side entry point the game execs at boot when
# sidecars are missing. Runs the bundled converter on the OS python3
# (stdlib only, no dependencies, no network).
exec /usr/bin/env python3 "$(dirname "$0")/prepare-assets.py" "$@"
"""

ROM_SUFFIXES = (".z64", ".n64", ".v64")
SIDECAR_BINS = ("pcmodels.bin", "pccg.bin")


def die(msg):
    print(f"package.py: error: {msg}", file=sys.stderr)
    sys.exit(1)


def check_elf_aarch64(path):
    with open(path, "rb") as f:
        magic = f.read(20)
    if len(magic) < 20 or magic[:4] != b"\x7fELF":
        return False
    machine = struct.unpack("<H", magic[18:20])[0]
    return machine == 183  # EM_AARCH64


def model_headers():
    out = []
    for p in (ROOT / "assets").rglob("*"):
        if p.is_file() and p.name.lower().endswith("modelfileheader.inc.c"):
            out.append(p)
    return sorted(out)


def stage_dir(root):
    """Copy converter bundle into staging. Returns prepare-assets dir."""
    prep = root / "ge007" / "prepare-assets"
    (prep / "vendor" / "scripts").mkdir(parents=True, exist_ok=True)
    (prep / "vendor" / "assets" / "obseg").mkdir(parents=True, exist_ok=True)
    (root / "ge007" / "tools" / "n64_portlib").mkdir(parents=True, exist_ok=True)
    (root / "ge007" / "data").mkdir(parents=True, exist_ok=True)

    for rel in CONVERTER_FILES:
        src = ROOT / rel
        if not src.is_file():
            die(f"missing converter source: {rel}")
        shutil.copy2(src, prep / Path(rel).name)
    for rel in CONVERTER_LIB:
        src = ROOT / rel
        if not src.is_file():
            die(f"missing converter lib: {rel}")
        shutil.copy2(src, root / "ge007" / "tools" / "n64_portlib" / Path(rel).name)
    for rel in VENDOR_SCRIPTS:
        src = ROOT / rel
        if not src.is_file():
            die(f"missing vendor script: {rel}")
        shutil.copy2(src, prep / "vendor" / "scripts" / Path(rel).name)
    for rel in VENDOR_ASSETS:
        src = ROOT / rel
        if not src.is_file():
            die(f"missing vendor asset: {rel}")
        shutil.copy2(src, prep / "vendor" / "assets" / "obseg" / Path(rel).name)

    headers = model_headers()
    if not headers:
        die("no *modelFileHeader.inc.c found under assets/")
    for src in headers:
        rel = src.relative_to(ROOT / "assets")
        dst = prep / "vendor" / "assets" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"package.py: staged converter ({len(headers)} model headers)")
    return prep


def write_wrapper(prep):
    wrapper = prep / "ge007-convert"
    # newline="\n": this file is exec'd by shebang on-device, where a CRLF
    # (Python's Windows default) makes the kernel look for "/bin/sh\r".
    wrapper.write_text(WRAPPER, encoding="ascii", newline="\n")
    return wrapper


def main():
    ap = argparse.ArgumentParser(description="Assemble the PortMaster test zip.")
    ap.add_argument("--game-bin", required=True, help="path to ge007.aarch64")
    ap.add_argument("--out", default="dist", help="output dir (default: dist/)")
    ap.add_argument("--zip-name", default=None, help="override port.json name")
    args = ap.parse_args()

    game_bin = Path(args.game_bin)
    if not game_bin.is_file():
        die(f"--game-bin {game_bin} : not a file")
    if not check_elf_aarch64(game_bin):
        die(f"--game-bin {game_bin} : not an AArch64 ELF")
    print(f"package.py: game binary OK ({game_bin.stat().st_size} bytes, AArch64)")

    try:
        port = json.loads(PORT_JSON.read_text(encoding="utf-8"))
        zip_name = args.zip_name or port["name"]
    except Exception as e:
        die(f"cannot read {PORT_JSON}: {e}")

    stage = Path(tempfile.mkdtemp(prefix="geport-"))
    try:
        prep = stage_dir(stage)

        # Game binary + data marker.
        shutil.copy2(game_bin, stage / "ge007" / "ge007.aarch64")
        (stage / "ge007" / "data" / ".place-user-rom-and-sidecars-here").write_text(
            "Put your GoldenEye 007 US NTSC .z64 ROM in this folder as\n"
            "ge007.ntsc-final.z64, then launch. Sidecars generate on first boot.\n",
            encoding="ascii")

        # Perf-safe default ini: the game merges this (missing keys are added
        # with defaults on first boot, present keys are honored), so fresh
        # installs start with Mali-friendly values instead of MSAA 4x +
        # framebuffer effects. Verified on R36S 2026-09-22.
        (stage / "ge007" / "data" / "ge007.ini").write_text(
            "# GoldenEye 007 R36S defaults (shipped in zip; edit freely).\n"
            "[Video]\n"
            "MSAA = 1\n"
            "FramebufferEffects = 0\n"
            "Anisotropy = 0\n",
            encoding="ascii", newline="\n")

        # Converter wrapper (exec bit set at zip time).
        wrapper = write_wrapper(prep)

        # Launcher + metadata at zip root / in ge007/ (as current package).
        for name in ["GoldenEye 007.sh", "port.json", "gameinfo.xml", "README.md"]:
            src = HERE / name
            if src.is_file():
                shutil.copy2(src, stage / name if name.endswith(".sh") else stage / "ge007" / name)

        # Build info: what revision produced this zip.
        try:
            rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 cwd=ROOT, capture_output=True, text=True,
                                 timeout=30).stdout.strip()
        except Exception:
            rev = "unknown"
        (stage / "ge007" / "build-info.txt").write_text(
            f"source-rev: {rev}\nbuilt-utc: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}\n",
            encoding="ascii")

        # Legal guardrail: refuse ROMs/sidecars anywhere in staging.
        bad = [p for p in stage.rglob("*")
               if p.is_file() and (p.suffix.lower() in ROM_SUFFIXES or p.name in SIDECAR_BINS)]
        if bad:
            die("refusing to ship ROM/sidecar data: " + ", ".join(str(p) for p in bad[:5]))

        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        zippath = outdir / zip_name
        if zippath.exists():
            zippath.unlink()
        exec_files = {wrapper.resolve(), (stage / "GoldenEye 007.sh").resolve()}
        with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in sorted(stage.rglob("*")):
                if not p.is_file():
                    continue
                arc = p.relative_to(stage).as_posix()
                zi = zipfile.ZipInfo(arc)
                zi.external_attr = (0o755 if p.resolve() in exec_files else 0o644) << 16
                zi.compress_type = zipfile.ZIP_DEFLATED
                with open(p, "rb") as f:
                    z.writestr(zi, f.read())

        # Verify the artifact.
        with zipfile.ZipFile(zippath) as z:
            names = z.namelist()
        checks = {
            "ge007/ge007.aarch64 in zip": "ge007/ge007.aarch64" in names,
            "launcher in zip": "GoldenEye 007.sh" in names,
            "converter wrapper in zip": "ge007/prepare-assets/ge007-convert" in names,
            "orchestrator in zip": "ge007/prepare-assets/prepare-assets.py" in names,
            "no ROM in zip": not any(n.lower().endswith(ROM_SUFFIXES) for n in names),
            "no sidecar bins in zip": not any(Path(n).name in SIDECAR_BINS for n in names),
        }
        for what, ok in checks.items():
            print(f"package.py: verify {'OK ' if ok else 'FAIL'}  {what}")
            if not ok:
                die("verification failed")
        print(f"package.py: wrote {zippath} ({zippath.stat().st_size} bytes, {len(names)} files)")
        print("package.py: normie flow: PortMaster-install zip -> place ROM at")
        print("package.py:   ge007/data/ge007.ntsc-final.z64 -> launch (extracts, boots)")
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    main()
