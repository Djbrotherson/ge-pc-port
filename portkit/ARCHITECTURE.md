# N64 Portkit architecture

## Position in the ecosystem

Portkit is not another N64 decompiler, static recompiler, renderer, or monolithic
runtime. Its job is to make an N64 codebase portable by turning reverse-
engineering knowledge into a repeatable host contract.

Two input paths are first-class:

1. **Source/decomp path**
   - input: an existing N64 decompilation;
   - compile game code natively;
   - adapt its N64 ABI, serialized data, libultra surfaces and display-list
     path to host services.

2. **Static-recomp path**
   - input: N64 binary plus symbols/metadata;
   - use an external recompilation engine for MIPS/RSP translation;
   - use Portkit for discovery, target/profile generation, runtime adapters,
     validation and enhancements.

Portkit should interoperate with existing runtime/recomp projects where their
contracts fit. Reimplement a subsystem only when portability requirements or a
target platform require a smaller/different backend.

## Stable layers

### 1. Discovery

Zero-mutation analysis of a project:

- source/build layout;
- libultra and hardware API usage;
- GBI/custom microcode surface;
- assembly and CPU-specific code;
- pointer-width hazards;
- endian-sensitive serialized structures;
- ROM, segment, overlay and address-token idioms.

Output is a versioned inventory.

### 2. Classification

Every address-like value is assigned a semantic class before transformation:

- host pointer;
- N64 virtual address;
- N64 physical address;
- cart/ROM address;
- segmented address;
- serialized 32-bit pointer/offset;
- linker symbol used as a token;
- scalar/bitfield/GBI word.

Unknown is a valid class. Automatic rewriting is forbidden for unknown values.

### 3. Game profile

A profile records facts specific to one title/decomp:

- ROM revisions/hashes;
- source roots and exclusions;
- memory map;
- overlays/segments;
- custom GBI/microcode;
- serialized asset layouts;
- scheduler/audio quirks;
- known generated symbols;
- explicit exceptions to generic audit rules.

Profiles are data, not forks of the generic scanner.

### 4. Host contract

The classified inventory is reduced to capabilities the selected runtime must
provide:

- threads/message queues/timers;
- VI and frame timing;
- RSP task dispatch;
- audio DMA/queue semantics;
- controller/accessory/save services;
- PI/cart/ROM reads;
- cache/TLB no-ops or mappings;
- filesystem and persistent storage;
- renderer/window/input callbacks.

This is the boundary between game analysis and implementation.

### 5. Runtime/backend adapters

Backends satisfy the host contract. Initial targets:

- direct source-port runtime;
- N64ModernRuntime adapter where compatible;
- SDL2 platform services;
- desktop OpenGL;
- OpenGL ES 3;
- Linux x86-64;
- Linux AArch64 / PortMaster.

Future backends can add Vulkan/RT64, Android, macOS or other handheld targets
without changing game profiles.

### 6. Serialized-data conversion

This is separate from CPU recompilation.

N64 ROM structures often combine:

- big-endian scalar fields;
- 32-bit pointers/offsets;
- N64 struct alignment;
- packed display-list data;
- game-specific compressed assets.

Portkit provides conversion primitives and generated walkers, while a game
profile supplies exact record descriptions when they cannot be inferred
safely.

### 7. Validation

Every promoted fix must become one of:

- a static audit rule;
- a unit/self-test;
- a build-time assertion;
- a runtime invariant check;
- a game-profile exception with justification.

The objective is monotonic knowledge: solved bug classes should not reappear
on the next title.

### 8. Enhancements

Enhancements sit above the compatibility layer:

- widescreen/ultrawide;
- FOV correction;
- resolution/upscale control;
- texture replacement;
- high-framerate support;
- input remapping/gyro;
- mod hooks;
- asset override filesystem.

Compatibility must remain testable with all enhancement modules disabled.

## GoldenEye's role

GoldenEye is reference integration #1. Its fixes are evidence used to improve
the generic layers. A GoldenEye change graduates into Portkit only when its
invariant can be stated without using a GoldenEye symbol name.

## Success criterion

Given a new, sufficiently complete N64 decomp, Portkit should eventually be
able to produce:

1. a machine-readable portability inventory;
2. a classified unresolved-risk report;
3. a generated host-contract manifest;
4. a build skeleton for the selected runtime/target;
5. generated shim stubs for unresolved hardware services;
6. a renderer/microcode compatibility report;
7. a target package skeleton;
8. a small explicit list of title-specific work still requiring human review.

The product is the reduction of an open-ended port into a finite, auditable
exception list.
