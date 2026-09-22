# Portkit Architecture

## Purpose

Portkit sits between an N64 codebase and a modern host target.

It converts reverse-engineering knowledge into explicit contracts so that
portability work becomes measurable and repeatable.

## Layers

### 1. Discovery

Inventory:

- source/build roots,
- OS/libultra surfaces,
- graphics command usage,
- assembly/CPU-specific code,
- pointer-width hazards,
- endian-sensitive data,
- ROM/segment/address-token idioms.

Output: versioned machine-readable inventory.

### 2. Classification

Address-like values are classified before any rewrite.

Classes include native pointers, virtual/physical/cart addresses, segmented
addresses, serialized offsets, linker tokens, scalars and unknowns.

### 3. Project profile

A profile contains only project-specific facts:

- source roots/exclusions,
- target ROM revisions/hashes where relevant,
- memory/segment rules,
- custom graphics commands,
- serialized formats,
- explicit semantic exceptions,
- layout/offset/fit contracts.

Profiles are data, not forks of the scanner.

### 4. ABI/layout contract

Machine-readable contracts describe fixed sizes, offsets, alignment and
containment assumptions.

The validation layer should prove those contracts against source assertions
and converter/runtime behavior.

### 5. Host capability contract

The classified inventory reduces into required capabilities:

- threads/messages/timers,
- video/frame timing,
- graphics task/display-list services,
- audio,
- input,
- storage/save,
- ROM/cart access,
- filesystem/configuration,
- platform lifecycle.

### 6. Runtime backends

Backends advertise capabilities and implementation constraints.

A project profile should not need to know backend internals.

### 7. Target descriptors

Targets describe deployment constraints:

- OS,
- architecture,
- pointer width,
- graphics API,
- packaging,
- device-specific requirements.

### 8. Serialized-data conversion

Binary conversion is independent of CPU recompilation.

Reusable primitives cover:

- endian reads/writes,
- alignment,
- relocation,
- fixed/variable record walking,
- segmented token handling,
- manifest assembly,
- deterministic validation.

Project adapters supply exact record knowledge when it cannot be inferred.

### 9. Generation

Once the host contract is resolved, Portkit generates only required adapter
skeletons and compile-time contracts.

Unresolved P0 semantics block a validated scaffold unless explicitly forced for
bring-up.

### 10. Validation

Every promoted fix should become one of:

- semantic rule,
- unit/selftest,
- source assertion,
- ABI-manifest rule,
- converter/runtime contract,
- target smoke test,
- documented profile exception.

Knowledge should be monotonic: solved classes should not reappear.

### 11. Enhancements

Enhancements sit above compatibility:

- widescreen/FOV,
- resolution/upscaling,
- texture replacement,
- high-frame-rate policy,
- controller remapping,
- mod/asset override hooks.

Compatibility must remain testable with enhancements disabled.

## Repository integration

The GoldenEye ARM64/R36S port is reference integration #1.

Repository-specific CI glue may remain under `tools/` and `.github/`, but
new reusable capabilities belong in `portkit/`.

## End state

Given a sufficiently complete N64 project, Portkit should produce:

1. portability inventory,
2. semantic risk report,
3. ABI/layout contracts,
4. host capability contract,
5. runtime/target resolution,
6. generated adapter skeleton,
7. deterministic validation plan,
8. explicit project-specific exception list.
