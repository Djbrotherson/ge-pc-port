# N64 Portkit

Portkit is the reusable portability layer in this repository.

Its job is to turn an existing N64 source/decomp/recomp project into a finite,
auditable modern-host porting problem.

It does not ship game ROMs or copyrighted assets and it does not assume one
specific title.

## Pipeline

```
project source
  -> profile
  -> discovery
  -> semantic classification
  -> ABI/layout contracts
  -> host contract
  -> backend/target resolution
  -> generated adapter skeleton
  -> build
  -> validation
```

## Commands

Analyze a project:

```sh
python3 portkit/portkit.py analyze \
  --repo /path/to/project \
  --profile portkit/profiles/template.json \
  --backend portkit/backends/sdl2-gles3-source-port.json \
  --target portkit/targets/linux-aarch64-portmaster-gles3.json \
  --out portkit-out
```

Generate adapter scaffolding after P0 issues are classified:

```sh
python3 portkit/portkit.py scaffold \
  --analysis portkit-out \
  --out generated-portkit
```

Run Portkit selftests:

```sh
python3 portkit/selftest.py
```

## Product boundary

Reusable logic belongs here:

- source discovery,
- address/token classification,
- semantic portability checks,
- ABI/layout contracts,
- host capability contracts,
- backend/target resolution,
- adapter generation,
- warning topology,
- reusable binary-format primitives,
- enhancement capability declarations.

Title-specific knowledge belongs in profiles and adapters.

## Semantic rule

Every address-like value must be classified before transformation:

- native host pointer,
- N64 virtual/physical/cart address,
- segmented address,
- serialized pointer/offset token,
- linker token,
- scalar/bitfield/graphics word,
- unknown.

Unknown is valid. Automatic rewriting of unknown values is forbidden.

## GoldenEye integration

GoldenEye is the first reference integration and regression corpus in this
repository.

A GoldenEye fix enters Portkit only when its invariant can be stated without a
GoldenEye symbol name.

## Directory layout

- `profiles/` — game/project profiles and reusable templates,
- `backends/` — host runtime capability descriptions,
- `targets/` — deployment/architecture constraints,
- `scan.py` — zero-mutation discovery,
- `classify.py` — semantic decision application,
- `validate.py` — host-safety findings,
- `contract.py` — host capability contract generation,
- `resolve.py` — contract/backend/target resolution,
- `generate.py` — adapter skeleton generation,
- `warnings.py` / `warning_topology.py` — compiler-warning classification,
- `selftest.py` — ROM-free regression tests.

## Success criterion

Portkit is successful when a new N64 project can be reduced to:

1. a profile,
2. a finite unresolved-risk report,
3. a generated host contract,
4. a selected runtime/target,
5. generated adapter stubs,
6. a short explicit list of title-specific exceptions.

The goal is not automatic magic. The goal is to replace open-ended porting
with repeatable classification and contracts.
