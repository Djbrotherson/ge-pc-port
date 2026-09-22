# Development Process

The project is optimized for maximum verified progress per expensive action.

## Core loop

```
observe
→ classify semantic class
→ search the whole class
→ batch proven fixes
→ encode invariant
→ run cheap proof
→ review
→ run one target proof
→ device test only when required
→ document reusable rule
→ repeat
```

## Action filter

A change should do at least one of:

1. remove a meaningful failure class,
2. strengthen automated proof,
3. move the R36S runtime frontier,
4. make the next N64 project cheaper to port.

Low-signal cleanup that does none of these is deprioritized.

## ABI classification

Before modifying an address-like value, classify it as:

1. native host pointer,
2. N64/ROM/segmented address token,
3. fixed-width serialized/layout field,
4. scalar.

Only native pointers widen automatically on LP64.

## Product boundary

### Reusable

New generic capabilities belong in `portkit/`:

- discovery,
- semantic classification,
- validation,
- ABI/layout contracts,
- host capability contracts,
- backend/target resolution,
- adapter generation,
- reusable binary primitives,
- warning topology.

### Repository integration

`tools/` contains GoldenEye-repository CI glue, integration contracts and
shared helpers that have not yet graduated into Portkit.

### GoldenEye-specific

`tools_pc/`, project adapters and integration manifests may contain
GoldenEye-specific binary knowledge.

## Validation tiers

### Tier 0

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
```

### Tier 1

Focused host compile/layout/converter/headless tests.

### Tier 2

One deliberate AArch64 cross-build for a coherent reviewed batch.

### Tier 3

R36S testing only for questions earlier tiers cannot answer.

If the device rediscovers a static ABI problem, add an earlier invariant.

## Fix + invariant

A compatibility fix should usually produce both:

- runtime correction,
- regression prevention.

Prevention may be:

- compile-time assertion,
- semantic rule,
- profile/ABI contract,
- converter/runtime cross-check,
- selftest,
- lifecycle invariant,
- generated table.

## Binary formats

Treat binary conversion as a formal ABI:

- byte order,
- N64 width,
- host width,
- alignment,
- token/pointer meaning,
- relocation,
- terminators,
- runtime stride.

Prefer one manifest or generated source of truth over duplicated constants.

## Commit discipline

Prefer coherent batches over exploratory commit churn.

Useful batch boundaries:

- one semantic failure class,
- one binary-format contract,
- one reusable Portkit capability,
- one runtime correction plus invariant.

Do not create commits only to trigger CI.

## Documentation

Current public/project state:

- `README.md`,
- `portkit/README.md`,
- `portkit/ARCHITECTURE.md`,
- `docs/README.md`.

Reusable engineering rules:

- `docs/porting-notes.md`.

Current runtime evidence/backlog:

- `docs/dev/LEVEL-STATUS.md`,
- `docs/dev/GRAPHICS-BACKLOG.md`,
- `docs/dev/findings.md`.

Closed investigations belong in git history, not the working tree.


## Dam lab exception

The `dam-only-lab` branch deliberately narrows Tier 3 to one instrumented
mission. It is allowed to carry forced-stage logic and high-signal telemetry
that would be inappropriate on `main`.

The lab still follows the normal development rule:

```
observe Dam
-> identify semantic divergence
-> census the whole class
-> batch fix
-> encode reusable invariant
-> prove cheaply
-> run Dam once
-> graduate generic fix to main/Portkit
```

Do not merge Dam-specific probes merely because they helped diagnose a bug.
Promote the underlying rule, not the temporary instrumentation.
