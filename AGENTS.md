# AGENTS.md — ARM-GE / N64 Portkit

## Mission

This repository has two coupled goals:

1. keep the GoldenEye 007 ARM64/GLES R36S port working and measurable;
2. turn every reusable portability lesson into N64 Portkit infrastructure.

The game port is the reference integration. Portkit is the reusable product.

## Canonical development line

- `main` is the only canonical development branch.
- Work in reviewed batches, not one-crash-one-commit loops.
- Prefer the smallest number of high-information builds and device tests.
- Preserve legal attribution in `NOTICE.md`; do not copy historical project documentation into new front-facing docs.

## Speedrun rule

For every action, ask:

1. What uncertainty does this remove?
2. Can the same evidence eliminate an entire bug class instead of one symptom?
3. Can this be proven statically or on host before spending an AArch64 build or R36S test?
4. Can the result become a reusable detector, contract, adapter, test, or generator?

Do not spend device time rediscovering static ABI, layout, pointer-width, or renderer-capability errors.

## Required validation ladder

Run the cheapest useful tier first.

### Tier 0 — semantic gate

```sh
python3 tools/n64_port.py gate
```

### Tier 1 — host evidence

Use focused compile/layout/converter/headless checks for the subsystem being changed.

### Tier 2 — AArch64 proof

Use the deliberate R36S cross-build only after a coherent reviewed batch. Avoid trigger-only commits.

### Tier 3 — R36S

Use real hardware only for runtime behavior that cannot be settled earlier.

## Porting invariants

Classify every suspicious value before editing it:

1. native host pointer;
2. 32-bit N64/ROM/segmented address token;
3. serialized offset or binary field;
4. fixed-width integer/data value.

Never mechanically widen every `s32`/`u32` to `uintptr_t`.

Keep serialized layouts fixed-width. Convert tokens to host pointers only at explicit boundaries. Keep converter/runtime strides and structure contracts paired and tested.

For graphics, the target capability is SDL2 + GLES 3. Desktop GL behavior must not leak into the GLES path. Prefer capability adapters and renderer-state lifecycle fixes over title-specific call-site patches.

## Where changes belong

| Area | Responsibility |
|---|---|
| `portkit/` | reusable scanners, schemas, backends, targets, classifiers, generators |
| `tools/n64_port.py`, `tools/n64_portlib/` | repository integration and semantic gate |
| `tools_pc/` | GoldenEye-specific converters and verification |
| `port/` | host runtime, SDL/GLES, audio, input, filesystem and platform shims |
| `src/`, `include/` | game source plus narrowly justified host ABI/layout adaptations |
| `cmake/`, `CMakeLists.txt` | target/build contracts |
| `docs/dev/` | current runtime evidence and active findings |
| `docs/` | current architecture and durable operating rules |

If a GoldenEye fix exposes a general N64 portability rule, capture the generic rule in `portkit/` or the semantic gate instead of leaving it as folklore.

## Batch workflow

1. identify a semantic class or runtime frontier;
2. census the whole relevant source path;
3. classify findings;
4. patch the class in one coherent batch;
5. add a detector/assertion/test/contract where practical;
6. run Tier 0;
7. run the minimum higher tier needed;
8. record only durable current documentation;
9. commit once the batch is internally consistent.

Do not accumulate temporary probes, scratch reports, generated binaries, ROM data, extracted assets, or machine-specific setup files in the repository.

## Documentation

Start with:

- `README.md`
- `docs/README.md`
- `portkit/README.md`
- `portkit/ARCHITECTURE.md`
- `docs/R36S-BUILD.md`
- `docs/porting-notes.md`

Detailed live evidence belongs under `docs/dev/`. Closed investigations should disappear from the working tree once their reusable rule or permanent test has been captured; Git history is the archive.

## Legal boundary

Do not commit ROMs, extracted proprietary game assets, credentials, private runner configuration, or generated ROM-derived artifacts.

Keep required third-party copyright/license notices intact. See `LICENSE` and `NOTICE.md`.
