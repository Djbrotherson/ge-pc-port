# Current Architecture

This document describes the current repository architecture only.

## Project split

The repository has two products:

1. the GoldenEye ARM64/GLES R36S port,
2. Portkit, the reusable N64 decomp/recomp portability layer.

GoldenEye is the first integration target and regression corpus.

## Runtime layers

### Game/source layer

`src/` and `include/` contain reconstructed game code plus narrowly scoped
host-safe ABI adaptations.

Changes here should preserve original game semantics.

### Host runtime

`port/` owns modern platform services:

- SDL window/input,
- GLES renderer integration,
- audio,
- timing/thread/message services,
- ROM/cart mapping,
- save storage,
- configuration,
- logging/crash support.

Target-specific behavior belongs here rather than being scattered through game
logic.

### Binary conversion

`tools_pc/` contains GoldenEye-specific sidecar converters and verification
utilities.

Primary adapters:

- `d43_emit.py` — model/rodata/display-list conversion,
- `d69_emit.py` — background/STAN conversion,
- `d88_emit.py` — stage setup conversion,
- `d88_propdefs.py` — polymorphic propDef stream conversion.

Shared converter primitives are being extracted into reusable libraries.

### Portkit

`portkit/` is the canonical reusable toolkit.

Its pipeline is:

```
discover
→ classify
→ validate
→ derive host contract
→ resolve runtime/target capabilities
→ generate adapter skeleton
→ build
→ verify
```

Project-specific data lives in profiles and contract manifests.

## Target

Current reference target:

- Linux AArch64,
- SDL2,
- GLES 3,
- PortMaster packaging,
- R36S-class handheld.

## Validation

The repository uses tiered validation:

1. profile/contract doctor,
2. ROM-free tool selftests,
3. semantic/ABI audit,
4. host checks,
5. deliberate AArch64 cross-build,
6. R36S device validation.

## Architectural rule

Every compatibility fix should move knowledge toward one of:

- reusable detector,
- reusable runtime adapter,
- generated/manifested ABI contract,
- reusable converter primitive,
- target profile.

Game-specific exceptions should remain explicit and small.
