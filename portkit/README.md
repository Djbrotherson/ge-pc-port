# N64 Portkit

This branch is the extraction lane for the reusable tooling discovered while
porting GoldenEye. GoldenEye remains the reference integration target, but the
tooling here must not depend on GoldenEye symbols to be considered reusable.

## Product boundary

Portkit is intended to sit between an existing N64 decompilation and modern
hardware. It does not replace a decompiler and it does not ship game ROMs or
copyrighted assets.

The pipeline is:

```
existing decomp
    |
    v
discover -> classify -> generate host contract -> build -> validate
    |                                            |
    +---- game profile / exceptions -------------+
```

The reusable layers are:

- decomp discovery and semantic auditing;
- host/N64 address-token separation;
- endian and serialized-layout conversion;
- libultra/OS service shims;
- RSP/GBI-to-renderer bridge;
- audio, input, timing, save and filesystem adapters;
- target toolchains and packaging;
- optional enhancement hooks: widescreen/FOV, resolution scaling, texture
  replacement, frame pacing and mod loading.

The non-reusable layer is game-specific knowledge: custom microcode commands,
asset record layouts, engine globals, unusual scheduler behavior, and any
source patches required by one decomp.

## First tool: discovery scanner

`scan.py` performs a zero-mutation inventory of a decomp before port work
begins. It records libultra hardware surfaces, GBI usage, CPU assembly,
endianness-sensitive files, ROM/segment-token usage and high-risk LP64
conversions.

Example:

```sh
python3 portkit/scan.py --repo . \
  --profile portkit/profiles/goldeneye.json \
  --out portkit-out
```

Outputs:

- `inventory.json` for automation;
- `report.md` for human triage.

The scanner is intentionally conservative. It may over-report, but it must not
silently rewrite a host pointer or an N64 token merely because the syntax looks
similar.

## Development rule

A GoldenEye fix graduates into Portkit only when we can state the invariant it
implements independently of GoldenEye. Examples:

- "host pointers must not be narrowed to N64 word width" is reusable;
- "this GoldenEye animation symbol represents a segment-relative token" is a
  GoldenEye profile rule;
- "a serialized N64 pointer field needs promotion to host pointer width" is
  reusable;
- the exact GoldenEye model-node record map is not.

This keeps the SDK small, testable and commercially useful instead of turning
it into a collection of one-off patches.


## Current command-line workflow

Start from the minimal profile template:

```sh
cp portkit/profiles/template.json my-game.json
```

Point it at the decomp and selected runtime/target descriptors:

```sh
python3 portkit/portkit.py analyze \
  --repo /path/to/decomp \
  --profile my-game.json \
  --backend portkit/backends/sdl2-gles3-source-port.json \
  --target portkit/targets/linux-aarch64-portmaster-gles3.json \
  --out portkit-out
```

The analysis directory contains:

- `inventory.json` — discovered APIs, GBI surface, address hazards and source facts;
- `validation.json` — high-signal host-safety findings;
- `host-contract.json` — runtime-neutral capabilities the title requires;
- `resolution.json` — required capabilities compared with selected backends;
- `summary.json` — compact machine-readable result for automation.

When all P0 semantic hazards are classified or fixed:

```sh
python3 portkit/portkit.py scaffold \
  --analysis portkit-out \
  --out generated-portkit
```

This emits only the adapter translation units required by the title's host
contract. Unrequired subsystems are not scaffolded.

During bring-up, `--force` may generate an intentionally incomplete skeleton,
but the manifest retains the unresolved state and this is not considered a
validated port.

## Design target

The intended end state is deliberately finite:

```
decomp
  -> profile
  -> inventory
  -> semantic classification
  -> host contract
  -> backend/target resolution
  -> generated adapters
  -> native build
  -> runtime validation
  -> optional enhancements
```

A new title should become an exception-list problem rather than an open-ended
manual port.


## ABI contract generation

Profiles can promote proven N64/host invariants into generated compile-time
checks instead of leaving them as comments:

- `layout_contracts` — exact `sizeof(type)` for serialized/fixed-stride data;
- `offset_contracts` — exact member offsets, useful for first-field aliasing;
- `fit_contracts` — require a private payload/event type to fit inside the
  generic container that copies or stores it.

GoldenEye examples that motivated these contracts include fixed GBI command
sizes, owner-slot audio aliasing through a field at offset zero, and private
sound events copied through generic `ALEvent` queue storage.

This is also the preferred CI pattern: run static/semantic gates on every
development push, accumulate reviewed fixes, then run expensive cross-target
builds deliberately as batch proofs.
