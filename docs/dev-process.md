# Development Process

This project is run as a speedrun with quality constraints.

The objective is not maximum commit count or maximum activity. The objective
is maximum **verified progress per expensive action** while turning GoldenEye
port discoveries into reusable N64 porting infrastructure.

## Core loop

```
observe
→ classify
→ search the whole semantic class
→ batch proven fixes
→ encode the invariant
→ run cheap proof
→ review
→ run one target proof
→ device test only when needed
→ document the reusable rule
→ repeat
```

## Decision rule for every action

Before changing code, ask:

1. Does this remove a whole failure class?
2. Does it strengthen automated proof?
3. Does it move the real R36S runtime frontier?
4. Does it make the next N64 decomp cheaper to port?

If the answer is no to all four, the work is low priority.

## Class before instance

A crash site is evidence, not the task.

Examples:

- one sign-extended pointer → audit every 32-bit token→pointer boundary,
- one `count * 4` pointer array → audit pointer-array allocation/copy/indexing,
- one struct-size mismatch → audit converter/runtime/native ABI agreement,
- one stale renderer object after reload → audit host resource lifetime against
  game lifecycle boundaries.

Fixing one line while leaving the class open is not considered complete.

## ABI classification

Every suspicious value must be classified before modification:

1. native host pointer,
2. N64/ROM/segmented address token,
3. fixed-width serialized/layout field,
4. scalar.

Only category 1 widens automatically on LP64.

This prevents the two common bad strategies:

- blindly widening all `s32/u32`,
- preserving 32-bit storage for values that became native host pointers.

## Validation tiers

### Tier 0 — cheap and continuous

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
```

This tier should reject:

- invalid project profiles,
- broken reusable binary helpers,
- semantic LP64 hazards,
- stale converter/native ABI relationships,
- known GLES incompatibilities,
- missing lifecycle invariants.

### Tier 1 — host

Use focused compilation, layout probes, converter tests, headless rendering,
and deterministic regression tools where available.

### Tier 2 — AArch64

The full cross-build is a batch proof.

It is deliberately not the normal edit/feedback loop.

### Tier 3 — R36S

Use real hardware for:

- driver/GLES behavior,
- timing/performance,
- controller behavior,
- PortMaster packaging/runtime libraries,
- bugs that require actual game interaction.

If Tier 3 catches a static ABI error, add a cheaper invariant afterward.

## Fix + invariant

A runtime fix should usually produce two outputs:

1. the runtime correction,
2. a reusable prevention mechanism.

Prevention can be:

- compile-time `sizeof`/`offsetof` assertion,
- semantic audit rule,
- project ABI manifest entry,
- converter/runtime cross-check,
- ROM-free unit test,
- lifecycle contract,
- generated table.

## Binary format work

Treat each binary format as a formal contract.

For every record family, track:

- N64 byte width,
- host byte width,
- byte order,
- alignment,
- pointer/token interpretation,
- relocation,
- terminator semantics,
- runtime walker stride.

The preferred direction is:

```
machine-readable ABI manifest
→ converter validation
→ C compile-time assertions
→ runtime contract
```

Avoid maintaining the same size constant independently in three places.

## Reusable tool boundary

Generic code belongs under:

- `tools/n64_port.py`,
- `tools/n64_port_audit.py`,
- `tools/n64_portlib/`.

GoldenEye-specific data belongs in:

- project profiles,
- ABI manifests,
- converter adapters,
- the GoldenEye contract suite.

A second decomp should be able to run the generic scanner without GoldenEye
files.

## Commit discipline

Prefer a small number of coherent commits over a long sequence of exploratory
ones.

Good batch boundaries include:

- one semantic failure class,
- one converter/ABI contract family,
- one reusable tool capability,
- one runtime fix plus its invariant.

Do not make no-op commits just to run CI. The branch has an explicit build
trigger for deliberate target proofs.

## Documentation discipline

Three documentation layers are maintained:

### Current public state

- root `README.md`,
- `docs/README.md`,
- `docs/PORTING-TOOLSET.md`.

These must stay concise and current.

### Reusable engineering rules

- `docs/porting-notes.md`.

When a bug reveals a general N64→host rule, distill it here.

### Evidence/history

- `docs/dev/`.

Detailed finding logs and investigation records are retained as evidence, but
they do not define current project status.

## End state

The GoldenEye port is one successful consumer.

The toolchain is successful when a second N64 decomp can be onboarded using a
small project profile and a limited set of format adapters, with the generic
tools automatically identifying ABI hazards, validating layouts, building a
target, and producing actionable failures.
