# GoldenEye-Specific Tools

This directory contains project-specific converters and verification utilities
for the GoldenEye ARM64/R36S integration.

Reusable tooling belongs in `portkit/` or shared libraries under `tools/`.

## Binary converters

| Tool | Purpose |
|---|---|
| `d43_emit.py` | model/rodata/display-list host sidecars |
| `d43_convert.py` | focused model conversion/validation |
| `d69_emit.py` | background and STAN host sidecars |
| `d88_emit.py` | stage setup host sidecars |
| `d88_propdefs.py` | polymorphic propDef stream conversion |

These converters are treated as ABI components. Size, endian, relocation and
runtime-walk assumptions are guarded by the semantic/ABI gate where possible.

## Verification

| Tool | Purpose |
|---|---|
| `verify.sh` | host verification entry point |
| `level_sweep.sh` | multi-level smoke sweep |
| `playtest.sh` | interactive playtest helper |
| `crash_brief.py` | reduce crash logs into actionable summaries |
| `framediff.py` | frame regression comparison |
| `pixcount.py` | simple rendered-pixel sanity check |
| `repro_gdb.sh` | reproducible debugger launch |
| `romverify.c` | ROM integrity check |
| `dump_objectives.py` | objective extraction for validation |
| `ppm2bmp.py` | dependency-free frame conversion |
| `gen_findings_index.py` | findings index generation/check |
| `gen_env_probes.py` | environment-probe drift check |

## Layout probes

| Tool | Purpose |
|---|---|
| `d43_layoutprobe.c` | compiler-verified model-sidecar layout |
| `d88_layoutprobe.c` | compiler-verified stage/propDef layout |
| `mtxtest.c` | matrix-pipeline numerical checks |

## Policy

One-off investigation scripts do not stay in this directory after their
finding is resolved.

A useful investigation graduates into one of:

- reusable Portkit capability,
- semantic-audit rule,
- ABI-manifest entry,
- converter validation,
- permanent regression test.

Git history preserves closed investigations; the working tree stays focused on
living tools.
