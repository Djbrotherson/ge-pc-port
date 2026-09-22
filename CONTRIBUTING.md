# Contributing

This branch is developed as two things at once:

1. a native AArch64/GLES GoldenEye port for R36S/PortMaster, and
2. a reusable N64 decomp/recomp porting toolchain.

Changes should improve at least one of those goals without weakening the other.

## Before changing code

Run:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
```

Read:

- `docs/PORTING-TOOLSET.md`
- `docs/porting-notes.md`
- the relevant current status/backlog entry under `docs/dev/`

## Working rules

### Classify before patching

Do not fix an isolated cast, warning, or crash site until its semantic class is
understood.

For 32/64-bit work, classify values as:

- native host pointer,
- N64/ROM/segmented address token,
- fixed-width serialized/layout data,
- ordinary scalar.

Only native pointers widen.

### Batch the whole failure class

When a repeatable pattern is found:

1. search the relevant source tree for the full class,
2. classify every candidate,
3. patch all proven instances together,
4. add a reusable detector/assertion/contract where practical.

A one-line runtime fix without a way to prevent recurrence is usually
incomplete.

### Preserve N64 semantics

The goal is not to make warnings disappear. The goal is to preserve the
original data/ABI meaning on a modern host.

Avoid broad mechanical replacements such as changing every `s32` to
`uintptr_t`.

### Keep project-specific knowledge out of the generic core

Generic rules belong under:

- `tools/n64_port.py`
- `tools/n64_port_audit.py`
- `tools/n64_portlib/`

GoldenEye-specific format knowledge belongs in:

- a port profile,
- an ABI manifest,
- a converter adapter,
- the GoldenEye contract suite.

A second N64 decomp should be able to use the generic scanner without
GoldenEye files being present.

## Validation tiers

Use the cheapest proof capable of rejecting the mistake.

### Tier 0 — required for relevant changes

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
```

### Tier 1 — host verification

Use focused compiler/layout/converter tests and headless verification where
the host environment is available.

### Tier 2 — AArch64 proof

Run the full target cross-build after a coherent batch, not after every edit.

### Tier 3 — R36S

Use the real device for hardware/runtime questions that the earlier tiers
cannot answer.

If a device test merely rediscovers a static ABI mismatch, improve the
toolchain so that class is caught earlier next time.

## Binary format changes

A binary conversion change must account for all of:

- source byte order,
- N64 record size/stride,
- host record size/stride,
- alignment,
- pointer/token relocation,
- runtime walker behavior,
- terminators/sentinels,
- converter validation.

Prefer a machine-readable contract over duplicated constants.

Current project contracts live under `tools/integration_profiles/`.

## Graphics changes

The R36S path is GLES-first.

Do not introduce desktop-only OpenGL calls into a host-active GLES path.
Display-list, Gfx/Vtx, TMEM, texture/palette and segmented-address semantics
must remain explicit.

Reusable widescreen, texture replacement, upscaling and renderer options
should be implemented as port-layer capabilities rather than scattered
GoldenEye-specific patches.

## Documentation

For every meaningful semantic class:

- record the reusable rule in `docs/porting-notes.md`,
- update current status/backlog if runtime behavior changed,
- update `docs/PORTING-TOOLSET.md` if the reusable architecture changed.

Chronological debugging notes belong under `docs/dev/`; they should not
replace concise current documentation.

## Commits

Prefer coherent, reviewable batches.

A useful commit answers one of these questions:

- what failure class was removed?
- what invariant was added?
- what reusable tool capability was created?
- what target behavior was proven?

Avoid commit churn that exists only to trigger CI.

## Legal

Do not commit ROMs, extracted copyrighted game assets, keys, or other
redistributability-sensitive material.

Keep existing copyright and license notices intact for code derived from
upstream projects. See `NOTICE.md`.
