# ARM-GE — GoldenEye R36S Port + N64 Porting Toolchain

This repository is our working ARM64/GLES port of **GoldenEye 007** for the
R36S/PortMaster environment, and the reference implementation for a reusable
toolchain that turns N64 decompilation projects into modern native ports.

The game is the proving ground. The long-term product is the layer around it:
ABI auditing, binary-layout conversion, target profiles, graphics adaptation,
runtime shims, verification, packaging, widescreen/mod hooks, and repeatable
port workflows.

> **No ROM, game assets, or Nintendo-owned game data are included.**
> You must provide a legally obtained GoldenEye 007 NTSC-U ROM.

## Current target

- **Device:** R36S
- **Environment:** dArkOSRE / PortMaster
- **Architecture:** AArch64 Linux
- **Graphics:** SDL2 + GLES 3.0
- **Input:** GO-Super Gamepad
- **ROM:** GoldenEye 007 NTSC-U
- **Expected ROM path:** `data/ge007.ntsc-final.z64`
- **Expected SHA-1:** `abe01e4aeb033b6c0836819f549c791b26cfde83`

## Status

The ARM64 port is in active development.

Already established on the R36S path:

- native AArch64 build,
- GLES rendering path,
- menus and intro rendering,
- in-mission rendering/gameplay,
- controller integration,
- PortMaster launch/package work,
- ROM-derived sidecar conversion,
- extensive LP64/N64 pointer-semantic cleanup,
- fixed-width binary-layout contracts,
- target-specific diagnostics and crash logging,
- automated semantic checks for recurring N64→LP64 failure classes.

The current work is focused on eliminating remaining host-state and edge-case
failures while extracting every general rule into reusable tooling.

A desktop port's historical status is **not** used as evidence that the R36S
target is complete. Target validation is based on our own AArch64 builds and
real-device tests.

## The toolchain

The reusable entry point is:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
python3 tools/n64_port.py show-profile
```

The GoldenEye reference profile lives at:

```
tools/port_profiles/goldeneye.json
```

The machine-readable ABI contract lives at:

```
tools/port_profiles/goldeneye_abi.json
```

A starter profile for another N64 project is provided at:

```
tools/port_profiles/template.json
```

### What the audit catches

The semantic/ABI gate currently checks classes including:

- host pointer truncation,
- signed 32-bit token → 64-bit pointer mistakes,
- 4-byte pointer-array stride assumptions,
- pointer storage type-punned through `s32*` / `u32*`,
- serialized struct growth,
- converter/runtime stride disagreement,
- N64 token vs native pointer confusion,
- animation-table offset rebasing,
- unsafe address-of-member NULL checks,
- x86-only LP64 fixes that omit AArch64,
- desktop OpenGL calls on GLES paths,
- AI bytecode layout/endian drift,
- model/STAN/setup sidecar ABI drift,
- renderer cache lifetime crossing level reload boundaries.

The rule is simple: if we discover a repeatable porting bug, fixing the
GoldenEye instance is only half the job. The other half is teaching the
toolchain to detect or prevent the class.

## Porting workflow

Our development loop is:

```
observe
→ classify semantic failure
→ search the whole class
→ batch-fix proven instances
→ encode the invariant
→ run cheap tests/audit
→ review
→ run one target build for the batch
→ test on device
→ repeat
```

Expensive AArch64 CI is deliberately not used as an editor. Cheap static and
ROM-free proofs are expected to catch mistakes first.

See [docs/PORTING-TOOLSET.md](docs/PORTING-TOOLSET.md) for the architecture,
validation tiers, and extraction roadmap.

## Repository layout

| Path | Purpose |
|---|---|
| `src/`, `include/` | reconstructed game code and host-safe ABI adaptations |
| `port/` | host runtime, SDL/GLES, audio, input, ROM/save/platform shims |
| `tools/` | reusable N64 port CLI, semantic scanner, profiles, shared library |
| `tools_pc/` | GoldenEye binary converters, verification tools, investigation utilities |
| `cmake/` | host/target toolchains |
| `.github/workflows/` | cheap semantic gate and deliberate AArch64 proof build |
| `docs/` | current architecture, porting rules, status, and engineering record |

## Converter pipeline

GoldenEye currently uses three primary offline format adapters:

- `tools_pc/d43_emit.py` — model/rodata/display-list sidecars,
- `tools_pc/d69_emit.py` — background + STAN data,
- `tools_pc/d88_emit.py` — stage setup data,
- `tools_pc/d88_propdefs.py` — polymorphic propDef stream conversion.

Shared endian/alignment primitives are being extracted into
`tools/n64_portlib/` so these adapters become examples of a generic binary
conversion framework rather than standalone one-off scripts.

## Build verification

The branch uses two validation tiers in CI:

### Cheap semantic gate

Runs on relevant source/tool/profile changes and performs:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
```

### AArch64 proof build

The full cross-build is deliberately triggered only for reviewed batches. It:

- cross-compiles for AArch64,
- builds the GLES path,
- verifies the output ELF is AArch64,
- emits symbols/disassembly/maps,
- uploads the target binary artifact.

This keeps GitHub Actions usage focused on proving meaningful batches instead
of discovering trivial source mistakes.

## PortMaster / R36S

The target runtime expects a PortMaster-style installation with the game
binary, required runtime libraries, derived sidecars, and a user-supplied ROM.

The R36S itself is treated as the final hardware oracle, not the first
debugger. If a failure can be detected statically, by a layout contract, or by
cross-compilation, it should be caught before the SD card is touched.

## Roadmap

Near-term priorities:

1. finish R36S gameplay/runtime regression work,
2. keep converting discovered GoldenEye failures into reusable audit rules,
3. finish extracting shared converter/relocation primitives,
4. consolidate verification behind `tools/n64_port.py`,
5. define R36S as a reusable target profile rather than GoldenEye-specific glue,
6. add true widescreen/FOV support through the reusable graphics layer,
7. add texture/mod replacement hooks,
8. onboard a second N64 decomp to prove the toolchain is genuinely generic.

## Documentation

Start here:

- [docs/README.md](docs/README.md) — documentation map,
- [docs/PORTING-TOOLSET.md](docs/PORTING-TOOLSET.md) — reusable toolchain architecture,
- [docs/porting-notes.md](docs/porting-notes.md) — N64→host failure classes,
- [docs/dev/LEVEL-STATUS.md](docs/dev/LEVEL-STATUS.md) — detailed runtime evidence,
- [tools_pc/README.md](tools_pc/README.md) — converter and verification-tool index.

The large files under `docs/dev/` are engineering records. They are useful
evidence, but they are not the public project narrative.

## Legal and attribution

This repository does not distribute GoldenEye 007 ROM data or extracted game
assets.

Our ARM64/R36S work builds on earlier open-source work, including the
GoldenEye 007 decompilation and the GoldenEye PC-port codebase from which this
repository was derived. Their copyrights and license notices remain with the
code they authored. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

GoldenEye 007, Nintendo 64, Nintendo, Rare, and related marks belong to their
respective owners. This project is not affiliated with or endorsed by them.
