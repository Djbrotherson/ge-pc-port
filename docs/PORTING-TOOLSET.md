# N64 Porting Toolset — architecture and speedrun rules

This repository is no longer treated as only a GoldenEye port. GoldenEye is the reference implementation and stress test for a reusable layer between N64 decompilation projects and modern host hardware.

The product is the **porting layer + verification toolchain**. Game-specific patches are acceptable only when the underlying semantic class is genuinely game-specific. Otherwise, every fix should become a reusable invariant, converter contract, runtime adapter, or diagnostic.

## 1. Objective

Given an N64 decomp/recomp project, reduce the work needed to produce a native modern-host build by supplying reusable machinery for:

- ILP32/N64 ABI → LP64 host adaptation.
- N64 address/token semantics → native pointer semantics.
- Big-endian serialized data → host-native layouts.
- N64 display-list / graphics semantics → GLES/OpenGL-compatible rendering.
- Fixed-width binary records and polymorphic stream conversion.
- Asset extraction and sidecar conversion.
- Input, audio, save, timing and platform shims.
- Widescreen, resolution, controller, mod and texture extension points.
- Automated semantic audits and target-hardware verification.

GoldenEye remains the proving ground. The long-term design target is a set of **plug-in adapters and generated contracts**, not a pile of game-specific fixes.

## 2. Speedrun rules

These rules are mandatory for agent work on this branch.

1. **Class before instance.** When a bug appears, identify the semantic class and audit the whole class before pushing a one-off patch.
2. **Fix + invariant.** A runtime fix is incomplete until the class is represented by a compile-time assertion, semantic-audit rule, converter/runtime cross-check, or regression harness where practical.
3. **Batch expensive validation.** Push-level work should use the cheap semantic gate. AArch64 cross-builds are deliberate batch proofs, not feedback for each edit.
4. **No blind widening.** Every suspicious 32-bit value is classified as one of:
   - native host pointer,
   - N64/ROM/segmented address token,
   - fixed-width serialized/layout data,
   - scalar value.
   Only native pointers widen.
5. **Binary formats are contracts.** Converter output size, host struct layout, runtime stride, byte order and pointer fixups must agree mechanically.
6. **Document the discovered rule, not the debugging diary.** The chronological findings log stays as evidence, but reusable knowledge belongs in concise architecture/tool docs and automated checks.
7. **Prefer generation over duplicated constants.** If a table exists in converter and runtime, either generate one from the other or add a gate that proves equality.
8. **Host lifecycle matters.** Caches and platform state that outlive N64-era arenas must be explicitly reset at game lifecycle boundaries.
9. **Target-neutral first.** A fix guarded only by x86_64 is suspect unless it is genuinely x86-specific. LP64 fixes should cover AArch64 too.
10. **One frontier at a time, whole class at once.** Do not bounce between unrelated cosmetic bugs while a high-impact semantic class remains open.
11. **Evidence hierarchy.** Compile-time proof > semantic gate > host test > target build > real-device test. Each layer should eliminate failures before the next.
12. **Every retained tool has an owner and purpose.** Investigation scripts graduate into living verification/conversion tools or are archived.

## 2.1 Implemented tool interface

The reusable layer now has a stable top-level command:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py audit
python3 tools/n64_port.py show-profile
```

Current configuration is split into:

- `tools/port_profiles/goldeneye.json` — project roots, target(s), adapters and verification entry points.
- `tools/port_profiles/goldeneye_abi.json` — machine-readable ABI/layout contract; it also declares required C `sizeof` guards.
- `tools/port_profiles/template.json` — generic starting point for another decomp/recomp.
- `tools/n64_port_audit.py` — profile-aware semantic runner.
- `tools/r36s_semantic_audit.py` — detector engine plus the selected GoldenEye contract suite.
- `tools/n64_portlib/binary.py` — shared endian/alignment primitives now used by d43/d69/d88 instead of three independent copies.
- `tools/n64_portlib/test_binary.py` — ROM-free unit tests for the reusable binary core.

CI calls the unified CLI, validates the profile, runs `selftest`, then runs the semantic/ABI gate. GoldenEye-specific binary checks are selected by `contract_suite`; a profile with an empty suite receives only generic semantic scanning.

## 3. Current reusable layers

### Semantic audit

`tools/r36s_semantic_audit.py` is the current host-port invariant engine. Despite its historical name, it is becoming target-neutral. It now guards classes including:

- direct pointer narrowing and host-address truncation,
- N64 token/native pointer boundary misuse,
- x86-only LP64 fixes that omit AArch64,
- animation offset rebasing,
- member-address NULL-test UB,
- pointer-array 4-byte stride assumptions,
- pointer storage aliased as 32-bit scalar storage,
- desktop-GL use on GLES paths,
- bitmask precedence bugs,
- propDef converter/runtime stride agreement,
- stage-setup converter/native ABI agreement,
- model-sidecar converter/native ABI agreement,
- STAN converter/runtime tile strides,
- AI command packed-record size and interpreter-dispatch agreement,
- AI bytecode big-endian multibyte access,
- renderer cache reset alignment with game texture resets.

Long-term action: rename/generalize this into a target-neutral `tools/n64_port_audit.py` entry point with target profiles.

### Binary-layout adapters

The important current converter families are:

- `tools_pc/d43_emit.py` — model files / ModelNode / rodata / GDL relocation.
- `tools_pc/d69_emit.py` — BG + STAN conversion.
- `tools_pc/d88_emit.py` — stage setup tables and relocation.
- `tools_pc/d88_propdefs.py` — polymorphic propDef stream conversion.

Their constants are not merely implementation details. They are ABI declarations and must stay mechanically tied to native structs and runtime walkers.

### Runtime host adapters

The reusable runtime layer currently lives mainly under `port/`:

- libultra/OS shims,
- ROM/cart mapping,
- graphics/fast3d host renderer,
- SDL/video/input,
- audio,
- platform helpers,
- save/EEPROM emulation,
- options/configuration,
- host crash/logging support.

New target support should extend this layer rather than infecting reconstructed game logic with platform conditionals.

## 4. Toolset decomposition

The intended generic toolkit is divided into six modules.

### A. Source semantic scanner

Input: decompiled C/C++ tree.

Output: classified findings for:
- pointer truncation,
- sign extension of 32-bit address tokens,
- fixed-width serialized records widened by host pointers,
- hardcoded 4-byte pointer strides,
- pointer/int unions,
- address arithmetic through signed 32-bit types,
- N64 endian assumptions,
- architecture-specific branches,
- desktop-only graphics calls.

Target: make the current semantic audit configurable per project.

### B. Layout contract generator

Input:
- selected C structs,
- optional N64 reference sizes/offsets,
- compiler target profile.

Output:
- `sizeof` / `offsetof` assertions,
- JSON/CSV ABI manifests,
- converter constants,
- mismatch reports.

Goal: eliminate hand-maintained converter/native size tables.

### C. Binary sidecar converter framework

Provide a generic API for:
- endian transforms,
- pointer-width expansion,
- relocation maps,
- variable-length record walkers,
- polymorphic record streams,
- segmented-address rewriting,
- validation and round-trip checks,
- manifest emission.

GoldenEye's d43/d69/d88 scripts become reference adapters on this framework.

### D. Runtime compatibility layer

Reusable host abstractions:
- N64 token ↔ host pointer boundaries,
- ROM/cart address mapping,
- libultra compatibility,
- threading/timing,
- input,
- save media,
- renderer bridge,
- audio bridge,
- target platform profile.

R36S should become one target profile, not a special-case fork.

### E. Graphics adaptation layer

Required capabilities:
- desktop GL → GLES-safe path,
- display-list command width invariants,
- texture/TLUT conversion,
- N64 tile and TMEM semantics,
- aspect/FOV/widescreen policy,
- draw-distance/LOD controls,
- texture replacement/mod hooks.

This is the eventual home for reusable widescreen/upscale/mod support.

### F. Verification harness

One command should eventually perform:
1. semantic audit,
2. layout-contract validation,
3. converter synthetic tests,
4. native host compile,
5. target cross-build,
6. artifact inspection,
7. optional emulator/device smoke test,
8. report generation.

The existing `verify.sh`, layout probes, semantic gate and AArch64 workflow are the pieces to consolidate.

## 5. Generic project profile

The future tool should consume a small project profile instead of hardcoding GoldenEye paths. A profile should describe:

- source roots,
- host-port include roots,
- target architectures,
- pointer/token helper names,
- ROM regions and hashes,
- serialized record families,
- converter plugins,
- build command,
- expected artifact architecture,
- graphics backend,
- test entry points,
- package target.

Conceptual shape:

```yaml
project: goldeneye
source_roots: [src, include, port]
targets:
  - id: r36s-aarch64-gles
    arch: aarch64
    graphics: gles3
binary_formats:
  - adapter: model
  - adapter: bg_stan
  - adapter: stage_setup
checks:
  semantic: true
  layout: true
  converter_contracts: true
```

The profile is declarative. Game-specific Python should only implement binary-format knowledge that cannot be inferred.

## 6. Validation tiers

### Tier 0 — static, near-free
Run on every relevant push:
- semantic scanner,
- layout assertions that can be evaluated without cross-building,
- converter/runtime table cross-checks,
- synthetic converter tests.

### Tier 1 — native host
Run when host code changes materially:
- compile/link,
- focused unit/layout probes,
- headless rendering and deterministic tests.

### Tier 2 — target cross-build
Run only after a coherent batch:
- AArch64 compile/link,
- ELF architecture verification,
- symbol/map artifact generation.

### Tier 3 — real device
Use only to answer questions static/native/cross-build proofs cannot:
- renderer/device-driver behavior,
- input mapping,
- timing/performance,
- packaging/runtime library behavior.

A device test that merely rediscovers a static ABI mismatch is a workflow failure.

## 7. Immediate roadmap

Priority order:

1. **Implemented:** unified `n64_port.py` CLI plus profile-driven generic semantic scanning.
2. **Implemented (first pass):** machine-readable ABI manifest drives model/STAN/setup converter stride checks.
3. **Next:** extract shared relocation/endian/record-walk helpers from d43/d69/d88.
4. **Next:** expand converter synthetic fixtures that do not require copyrighted ROM data.
5. **Active:** consolidate `verify.sh` + semantic gate + layout probes behind the unified CLI.
6. Define `targets/r36s-aarch64-gles` as a target profile.
7. Split GoldenEye-specific adapters from generic core.
8. Add widescreen/FOV and texture replacement as generic renderer extension points.
9. Build a minimal second-project adapter to prove the architecture is not GoldenEye-specific.
10. Only after the second project works should the generic layer be treated as a standalone product/API.

## 8. Definition of done for a fix

A port fix is complete when:

- the root semantic class is stated,
- the whole relevant class was searched,
- all known concrete instances are addressed,
- the reusable invariant/tool is added where practical,
- the relevant documentation is updated,
- the cheap gate is green,
- and an expensive target build is run only if the change can affect target compilation/runtime.

## 9. Definition of done for the toolset

The toolset is credible when a second N64 decomp can be onboarded by supplying a profile plus a small number of format adapters, with the generic tooling automatically finding ABI hazards, proving binary layouts, building the target layer, and producing an actionable report without GoldenEye-specific assumptions in the core.
