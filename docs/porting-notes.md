# N64 → Modern Host Porting Rules

This document is the compact rulebook extracted from the current ARM64/GLES
port. It records reusable semantic classes, not historical debugging sessions.

## 1. Classify address-like values before editing

Every suspicious value belongs to one of four categories:

1. native host pointer,
2. N64/ROM/segmented address token,
3. fixed-width serialized/layout field,
4. scalar.

Only native host pointers widen automatically on LP64.

Never replace every `s32/u32` with `uintptr_t`. Doing so destroys token and
serialized-layout semantics.

## 2. Pointer-width hazards

Audit the whole class whenever one instance appears:

- pointer → `s32/u32` narrowing,
- signed 32-bit token → pointer sign extension,
- pointer arrays stepped by 4 bytes,
- pointer arrays allocated/copied with `count * 4`,
- pointer storage type-punned through `s32 *` / `u32 *`,
- hard-coded byte offsets into structs that gained 8-byte pointers,
- callback/function-pointer ABIs that still use 32-bit pointer parameters,
- pointer members used as scalar/tag storage.

Prefer named helpers at token/native boundaries.

## 3. Serialized layouts are contracts

For every ROM/file-side record family, track:

- source byte order,
- N64 byte width,
- host byte width,
- alignment,
- pointer/token fields,
- relocation rules,
- terminators/sentinels,
- runtime walker stride.

Converter width, native `sizeof`, and runtime stride must agree mechanically.

The project ABI manifest lives under `tools/port_profiles/`.

## 4. Endianness

ROM and sidecar source data may remain big-endian even on a little-endian host.

Multibyte fields must either:

- be converted offline, or
- be read through explicit byte-swap helpers at runtime.

Do not mix both approaches for the same field family.

## 5. Pointer-array rule

N64 pointer slots are 4 bytes; LP64 pointer slots are 8 bytes.

Any byte math around `T **` must use `sizeof(T *)`, not a literal 4 or
`<< 2`.

This applies to indexing, allocation, copies, clears, and ad-hoc slot storage.

## 6. Struct overlays and puns

If one type intentionally overlays another:

- assert required `offsetof` relationships,
- assert containing storage is large enough,
- avoid raw byte offsets where a typed field exists.

If the relationship cannot be stated as an invariant, it is too fragile.

## 7. Display-list / graphics ABI

Graphics command and vertex widths are fixed contracts.

Keep command-width assumptions explicit and audited. Do not infer N64 bitfield
layout from host C bitfield layout.

On GLES targets:

- reject desktop-only GL entry points,
- preserve N64 display-list semantics in the renderer bridge,
- keep texture/TLUT/TMEM state explicit,
- treat renderer caches as host resources with their own lifecycle.

## 8. Host resource lifetime

N64-era arenas are frequently recycled.

Any host cache keyed by an address from those arenas must be reset when the
game resets/reloads the corresponding resource domain.

Examples include:

- decoded textures,
- palettes,
- shaders/program state,
- model-side caches.

Game reset and host-cache reset must be paired at the same lifecycle boundary.

## 9. Binary converters

Converters are part of the ABI, not disposable extraction scripts.

A converter change should have:

- machine-readable size/offset contract,
- ROM-free synthetic coverage where possible,
- deterministic manifest output,
- explicit alignment,
- explicit endian helpers,
- validation against runtime expectations.

Shared primitives belong in `tools/n64_portlib/` or `portkit/`, not copied
between adapters.

## 10. Validation order

Use the cheapest proof first:

```
profile validation
→ reusable-library selftest
→ semantic/ABI audit
→ host tests
→ target cross-build
→ real device
```

A device test that rediscovers a static ABI mismatch means the earlier tooling
needs another invariant.

## 11. Fix + invariant

A runtime fix is considered complete when the semantic class is also guarded by
one or more of:

- compile-time assertion,
- semantic-audit rule,
- ABI-manifest entry,
- converter/runtime cross-check,
- ROM-free unit test,
- lifecycle contract.

## 12. Product boundary

Generic logic belongs in `portkit/` and shared tool libraries.

Title-specific knowledge belongs in profiles, ABI manifests and converter
adapters.

The goal is to make each new N64 decomp an exception-list problem rather than
another open-ended port.
