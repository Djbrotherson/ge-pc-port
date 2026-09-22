# ARM-GE

ARM-GE is the active GoldenEye 007 ARM64/GLES port for R36S/PortMaster and the
reference integration for **N64 Portkit**, the reusable portability toolchain
developed in this repository.

The port proves the runtime. Portkit captures the reusable method.

> No ROM, extracted game assets, or proprietary game data are distributed.
> A legally obtained GoldenEye 007 NTSC-U ROM is required for local use.

## Target

| Component | Current target |
|---|---|
| Device | R36S |
| Runtime | dArkOSRE / PortMaster |
| CPU | AArch64 |
| Graphics | SDL2 + GLES 3 |
| Input | GO-Super Gamepad |
| ROM | GoldenEye 007 NTSC-U |
| ROM path | `data/ge007.ntsc-final.z64` |
| ROM SHA-1 | `abe01e4aeb033b6c0836819f549c791b26cfde83` |

## Current state

The ARM64 target has already reached:

- native AArch64 builds,
- GLES rendering,
- menus and intro rendering,
- in-mission rendering and gameplay,
- controller integration,
- PortMaster launch/package support,
- ROM-derived host sidecars,
- broad LP64/N64 semantic cleanup,
- fixed binary-layout contracts,
- crash/logging instrumentation,
- automated host-port semantic auditing.

Current work is concentrated on runtime regression, renderer correctness,
host-resource lifetime, packaging polish, and extraction of remaining reusable
porting machinery into Portkit.

## Portkit

`portkit/` is the canonical reusable product surface.

Typical analysis flow:

```sh
python3 portkit/portkit.py analyze \
  --repo . \
  --profile portkit/profiles/goldeneye.json \
  --backend portkit/backends/sdl2-gles3-source-port.json \
  --target portkit/targets/linux-aarch64-portmaster-gles3.json \
  --out portkit-out
```

After classification:

```sh
python3 portkit/portkit.py scaffold \
  --analysis portkit-out \
  --out generated-portkit
```

Repository CI also uses a narrower integration wrapper:

```sh
python3 tools/n64_port.py gate
```

The wrapper exists for this repository's GoldenEye-specific contracts and
current CI. New reusable capabilities belong in `portkit/`.

## What Portkit is for

Portkit reduces N64 porting into explicit stages:

```
discover
→ classify
→ validate
→ derive ABI/layout contracts
→ derive host capability contract
→ resolve backend/target
→ generate adapters
→ build
→ verify
```

Reusable checks currently cover classes such as:

- host pointer truncation,
- signed token → native pointer mistakes,
- hard-coded 4-byte pointer-array assumptions,
- pointer-storage type punning,
- serialized struct growth,
- converter/runtime stride mismatch,
- token/native-pointer confusion,
- animation-offset rebasing,
- undefined NULL/member tests,
- architecture-incomplete LP64 fixes,
- desktop-GL calls on GLES paths,
- AI bytecode layout/endian drift,
- model/STAN/setup ABI drift,
- host renderer state surviving game resource resets.

## Development rule

A game fix is not complete when the crash disappears.

Where practical it must also produce one of:

- semantic detector,
- compile-time assertion,
- ABI manifest entry,
- converter/runtime contract,
- unit/selftest,
- lifecycle invariant,
- reusable adapter/helper.

That is how GoldenEye work becomes reusable porting infrastructure.

## Validation

### Tier 0 — every relevant change

```sh
python3 tools/n64_port.py gate
```

### Tier 1 — host

Focused compile, layout, converter and headless regression checks.

### Tier 2 — AArch64

A deliberate cross-build for a reviewed batch.

### Tier 3 — R36S

Real-device testing for hardware/runtime questions that earlier tiers cannot
answer.

The device should not be used to rediscover static ABI mistakes.

## Repository layout

| Path | Role |
|---|---|
| `portkit/` | reusable N64 portability toolkit |
| `src/`, `include/` | game source and narrowly scoped host ABI adaptations |
| `port/` | host runtime, SDL/GLES, audio, input, storage and platform shims |
| `tools/` | repository integration, CI semantic contracts and shared helpers |
| `tools_pc/` | GoldenEye-specific converters and verification utilities |
| `cmake/` | build/toolchain definitions |
| `docs/` | current architecture, rules, target build and active findings |
| `.github/workflows/` | cheap semantic gate and deliberate AArch64 proof |

## GoldenEye converters

The current GoldenEye binary adapters are:

- `tools_pc/d43_emit.py` — model/rodata/display-list conversion,
- `tools_pc/d69_emit.py` — background/STAN conversion,
- `tools_pc/d88_emit.py` — stage setup conversion,
- `tools_pc/d88_propdefs.py` — polymorphic propDef conversion.

Generic binary primitives are being moved into reusable libraries rather than
copied between adapters.

## Build

Use:

- [docs/R36S-BUILD.md](docs/R36S-BUILD.md) for the AArch64/GLES target,
- [portkit/README.md](portkit/README.md) for Portkit,
- [docs/README.md](docs/README.md) for the documentation map.

## Roadmap

1. finish R36S runtime regression,
2. continue moving generic behavior into Portkit,
3. consolidate relocation/record/sidecar primitives,
4. make the R36S target fully declarative,
5. unify remaining GoldenEye-specific converter primitives behind Portkit contracts,
6. add reusable widescreen/FOV hooks,
7. add texture/mod override hooks,
8. validate Portkit against a second N64 project.

## Legal

The working tree contains original work alongside code derived from earlier
open-source sources. Existing copyright and license notices are preserved where
required.

No ROM or extracted copyrighted game assets are distributed.

See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
