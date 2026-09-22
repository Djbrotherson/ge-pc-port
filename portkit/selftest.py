#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN = HERE / "scan.py"
CONTRACT = HERE / "contract.py"
GENERATE = HERE / "generate.py"
VALIDATE = HERE / "validate.py"
RESOLVE = HERE / "resolve.py"
CLI = HERE / "portkit.py"
CLASSIFY = HERE / "classify.py"
WARNINGS = HERE / "warnings.py"

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="n64-portkit-selftest-") as td:
        root = Path(td)
        (root / "src").mkdir()
        (root / "rsp").mkdir()
        (root / "ignored").mkdir()

        (root / "src" / "game.c").write_text(
            """
#include <stdint.h>
typedef unsigned int u32;
typedef struct Gfx Gfx;
void demo(void *ptr, Gfx *gdl) {
    osViSwapBuffer(ptr);
    osAiSetNextBuffer(ptr, 256);
    u32 narrowed = (u32)ptr;
    (void)narrowed;
    G_TRI4;
}
"""
        )
        (root / "rsp" / "boot.s").write_text("mfc0 $t0, $12\n")
        (root / "ignored" / "noise.c").write_text("osEepromRead(0, 0, 0);\n")

        profile = {
            "schema": 1,
            "name": "selftest",
            "source_roots": ["src", "rsp", "ignored"],
            "exclude_roots": ["ignored"],
            "layout_contracts": [
                {
                    "type": "FixtureRecord",
                    "size": 16,
                    "scope": "serialized",
                    "why": "fixture serialized size",
                }
            ],
            "offset_contracts": [
                {
                    "type": "FixtureRecord",
                    "member": "field",
                    "offset": 4,
                    "why": "fixture field offset",
                }
            ],
            "fit_contracts": [
                {
                    "payload_type": "FixtureSmall",
                    "container_type": "FixtureRecord",
                    "why": "fixture payload storage",
                }
            ],
            "offset_contracts": [
                {
                    "type": "FixtureRecord",
                    "member": "field",
                    "offset": 4,
                    "why": "fixture field offset",
                }
            ],
            "fit_contracts": [
                {
                    "payload_type": "FixtureSmall",
                    "container_type": "FixtureRecord",
                    "why": "fixture payload storage",
                }
            ],
        }
        profile_path = root / "profile.json"
        profile_path.write_text(json.dumps(profile))

        out = root / "out"
        subprocess.run(
            [sys.executable, str(SCAN), "--repo", str(root),
             "--profile", str(profile_path), "--out", str(out)],
            check=True,
        )

        data = json.loads((out / "inventory.json").read_text())
        assert data["profile"] == "selftest"
        assert data["hardware_surfaces"]["video"]["apis"]["osViSwapBuffer"] == 1
        assert data["hardware_surfaces"]["audio"]["apis"]["osAiSetNextBuffer"] == 1
        assert data["hardware_surfaces"]["save_accessory"]["count"] == 0
        assert data["gbi_tokens"]["G_TRI4"] == 1
        assert data["summary"]["assembly_files"] == 1
        assert any(h["kind"] == "pointer-to-32" for h in data["hazards"])
        assert any(h["kind"] == "cpu-specific-asm" for h in data["hazards"])

        contract_path = root / "host-contract.json"
        subprocess.run(
            [sys.executable, str(CONTRACT), str(out / "inventory.json"),
             "--out", str(contract_path)],
            check=True,
        )
        contract = json.loads(contract_path.read_text())
        caps = {r["capability"] for r in contract["requirements"]}
        assert "video.vi" in caps
        assert "audio.ai" in caps
        assert "graphics.gbi" in caps
        assert "cpu.arch_specific_code" in caps
        assert contract["unresolved"]["P0"] >= 1
        assert contract["ready_for_generation"] is False

        p0 = [h for h in data["hazards"] if h["severity"] == "P0"]
        decisions_path = root / "decisions.json"
        decisions_path.write_text(json.dumps({
            "schema": 1,
            "decisions": [
                {
                    "path": h["path"],
                    "line": h["line"],
                    "kind": h["kind"],
                    "class": "host_pointer" if h["kind"] == "pointer-to-32" else "false_positive",
                    "reason": "selftest fixture: explicitly classified",
                    "source": "selftest",
                }
                for h in p0
            ],
        }))

        classified_path = root / "classified.json"
        subprocess.run(
            [sys.executable, str(CLASSIFY), str(out / "inventory.json"),
             str(decisions_path), "--out", str(classified_path)],
            check=True,
        )
        classified_contract_path = root / "classified-contract.json"
        subprocess.run(
            [sys.executable, str(CONTRACT), str(classified_path),
             "--out", str(classified_contract_path)],
            check=True,
        )
        classified_contract = json.loads(classified_contract_path.read_text())
        assert classified_contract["unresolved"]["P0"] == 0
        assert classified_contract["ready_for_generation"] is True

        generated = root / "generated"
        blocked = subprocess.run(
            [sys.executable, str(GENERATE), str(contract_path), "--out", str(generated)],
            capture_output=True,
            text=True,
        )
        assert blocked.returncode != 0
        assert "generation blocked" in (blocked.stdout + blocked.stderr)

        subprocess.run(
            [sys.executable, str(GENERATE), str(contract_path),
             "--profile", str(profile_path),
             "--out", str(generated), "--force"],
            check=True,
        )
        manifest = json.loads((generated / "manifest.json").read_text())
        generated_caps = {x["capability"] for x in manifest["generated"]}
        assert "video.vi" in generated_caps
        assert "audio.ai" in generated_caps
        assert (generated / "portkit_backend.h").exists()
        assert (generated / "CMakeLists.txt").exists()
        assert manifest["build"]["target"] == "portkit_generated"
        assert (generated / "portkit_layout_contracts.h").exists()
        layout_header = (generated / "portkit_layout_contracts.h").read_text()
        assert 'sizeof(FixtureRecord) == 0x10' in layout_header
        assert '__builtin_offsetof(FixtureRecord, field) == 0x4' in layout_header
        assert 'sizeof(FixtureSmall) <= sizeof(FixtureRecord)' in layout_header
        assert manifest["layout_contracts"][0]["type"] == "FixtureRecord"
        assert manifest["layout_contracts"][0]["size"] == 16
        assert manifest["offset_contracts"][0]["member"] == "field"
        assert manifest["offset_contracts"][0]["offset"] == 4
        assert manifest["fit_contracts"][0]["payload_type"] == "FixtureSmall"
        assert manifest["fit_contracts"][0]["container_type"] == "FixtureRecord"

        validation_path = root / "validation.json"
        validation = subprocess.run(
            [sys.executable, str(VALIDATE), "--repo", str(root),
             "--roots", "src", "--out", str(validation_path)],
            capture_output=True,
            text=True,
        )
        validation_data = json.loads(validation_path.read_text())
        assert validation_data["schema"] == 1

        runtime_desc = HERE / "backends" / "sdl2-gles3-source-port.json"
        target_desc = HERE / "targets" / "linux-aarch64-portmaster-gles3.json"
        resolution_path = root / "resolution.json"
        resolution = subprocess.run(
            [sys.executable, str(RESOLVE), str(contract_path),
             str(runtime_desc), str(target_desc), "--out", str(resolution_path)],
            capture_output=True,
            text=True,
        )
        resolution_data = json.loads(resolution_path.read_text())
        assert "data.n64_serialization" in resolution_data["missing"] or contract["unresolved"]["P0"] > 0
        assert resolution_data["profile"] == "selftest"

        cli_out = root / "cli-out"
        cli = subprocess.run(
            [sys.executable, str(CLI), "analyze",
             "--repo", str(root),
             "--profile", str(profile_path),
             "--decisions", str(decisions_path),
             "--backend", str(runtime_desc),
             "--target", str(target_desc),
             "--out", str(cli_out)],
            capture_output=True,
            text=True,
        )
        assert (cli_out / "summary.json").exists()
        cli_summary = json.loads((cli_out / "summary.json").read_text())
        assert cli_summary["profile"] == "selftest"
        assert cli_summary["classification_checked"] is True
        assert cli_summary["classification_ready"] is True
        assert cli_summary["resolution_checked"] is True

        warning_log = root / "compiler.log"
        warning_log.write_text(
            "/tmp/repo/src/game/core.c:10:2: warning: bad core pointer [-Wincompatible-pointer-types]\n"
            "/tmp/repo/generated/noise.c:4:1: warning: known generated view [-Wincompatible-pointer-types]\n"
        )
        warning_policy = root / "warning-policy.json"
        warning_policy.write_text(json.dumps({
            "schema": 1,
            "ignore_scopes": ["/generated/"],
            "core_options": ["incompatible-pointer-types"],
        }))
        warning_out = root / "warning-audit.json"
        warning_run = subprocess.run(
            [sys.executable, str(WARNINGS), str(warning_log),
             "--policy", str(warning_policy), "--out", str(warning_out)],
            capture_output=True,
            text=True,
        )
        warning_data = json.loads(warning_out.read_text())
        assert warning_run.returncode == 2
        assert warning_data["core_contract_violations"] == 1
        assert warning_data["ignored_diagnostics"] == 1
        assert warning_data["contract_violations"][0]["path"].endswith("/src/game/core.c")

    print("n64-portkit selftest PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
