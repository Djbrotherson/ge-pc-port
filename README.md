# ARM-GE — Dam Behavioral Lab

> **Branch: `dam-only-lab`**
>
> This is a temporary, instrumented Dam-only research branch. The release and
> canonical integration line remains `main`. This branch intentionally forces
> Dam, adds runtime telemetry, and may contain diagnostic code that must not be
> treated as release behavior.

ARM-GE is the active GoldenEye 007 ARM64/GLES port for R36S/PortMaster and the
reference integration for **N64 Portkit**, the reusable portability toolchain
developed in this repository.

The purpose of this branch is to understand one mission deeply enough to expose
the remaining gameplay-semantic failures, then turn each generalizable result
into reusable Portkit machinery.

See **[docs/dev/DAM-LAB.md](docs/dev/DAM-LAB.md)** before testing this branch.

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

## Dam lab state

The infrastructure inherited from `main` is treated as the certified baseline:

- Core AArch64 / LP64 host semantics: **100%**
- GLES / render / input / runtime integration: **100%**
- Stage / setup / model semantic conversion: **100%**

This branch does **not** assume that those structural closures imply correct
game behavior. Dam currently loads but the player spawn/world state is wrong.
The active task is therefore behavioral validation of the complete
setup -> pad -> STAN -> room -> collision -> player/camera chain.

The lab adds:

- forced Dam / Agent baseline,
- a decompiled-source spawn oracle,
- a persistent hardware HUD,
- structured `damlab.log` telemetry,
- event logging for room/camera/STAN/position anomalies,
- a one-run evidence workflow intended to support batch fixes.

## Current state

The current `main` line has closed the major host-port conversion layers for
the GoldenEye/R36S target.

| Area | Status | Evidence |
|---|---:|---|
| Core AArch64 / LP64 host semantics | **100%** | pointer/token boundaries, ABI/layout contracts and semantic gate |
| GLES / render / input / runtime integration | **100%** | native GLES3 path, menus, intro, missions and controller integration |
| Stage / setup / model semantic conversion | **100%** | setup tables, propDefs, model sidecars and runtime relocation contracts |
| Gameplay / stage behavioral correctness | **active frontier** | full-level regression, AI/objective/prop behavior, transitions and edge cases |

Latest closure proof:

- exact proof commit: `fb618e64bd6060e2b31ca64722207aed3ef379db`,
- Portkit semantic audit: **P0=0, P1=0, total=0**,
- 64-bit pointer regression: **PASS**,
- AArch64 GLES configure/build/link: **PASS**,
- output verified as a 64-bit AArch64 ELF,
- `ge007.aarch64` artifact produced successfully.

The stage/setup/model sweep also closed a previously missing model opcode-17
conversion path. The record now has an LP64 sidecar layout, a typed runtime
representation, correct `othernode` promotion, compile-time layout assertions,
an ABI-manifest entry and semantic-gate coverage. The gate now checks complete
model record coverage and converter/runtime pointer-promotion parity so this
class cannot silently regress.

The port has already demonstrated native AArch64 execution, GLES rendering,
menus and intro, in-mission rendering/gameplay, controller integration,
PortMaster launch/package support and ROM-derived host sidecars.

Current work is now concentrated on **behavioral correctness rather than basic
conversion plumbing**: spawn behavior, objectives and AI, prop interactions,
mission transitions, collision/navigation edge cases, full-level regression,
runtime polish and extraction of the remaining reusable machinery into Portkit.

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

1. complete full-stage behavioral regression on R36S,
2. close remaining spawn, objective, AI, prop, mission-transition and navigation edge cases,
3. continue moving proven generic behavior into Portkit,
4. consolidate relocation/record/sidecar primitives behind reusable Portkit contracts,
5. make the R36S target fully declarative,
6. add reusable widescreen/FOV hooks,
7. add texture/mod override hooks,
8. validate Portkit against a second N64 project.

## Legal

The working tree contains original work alongside code derived from earlier
open-source sources. Existing copyright and license notices are preserved where
required.

No ROM or extracted copyrighted game assets are distributed.

See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
