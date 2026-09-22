# Active Engineering Findings

This file tracks only current, actionable findings for the ARM64/R36S branch.
Historical investigation logs remain available in git history and are not kept
in the working tree as project narrative.

## Current priorities

### R36S runtime regression

Validate the latest AArch64/GLES batch on real hardware:

- mission load,
- death/restart,
- texture stability after reload,
- controller behavior,
- audio initialization and sustained gameplay,
- cutscenes and mission transitions.

### Renderer lifecycle

The level loader now resets host renderer texture/shader state together with
GoldenEye's texture state. Re-test repeated death/restart cycles on previously
affected missions.

### Graphics correctness

Remaining visual issues should be treated as renderer semantics, not patched
per asset unless proven asset-specific.

Focus classes:

- billboard/sprite state,
- particle color state,
- water/tile transitions,
- front-end model/texture state,
- widescreen/FOV policy,
- culling/LOD behavior.

### Portkit extraction

Continue moving reusable behavior from project-specific scripts into
`portkit/` and shared libraries:

- endian primitives,
- alignment,
- relocation,
- variable-length record walking,
- manifest/sidecar assembly,
- target resolution,
- semantic classification,
- ABI contract generation.

### Second-project proof

The reusable toolchain is not considered generic until a second N64 source tree
can run discovery, semantic classification, host-contract generation and
scaffolding with only a profile and project-specific format adapters.

## Reporting rule

New findings must include:

- symptom,
- semantic class,
- affected subsystem,
- root cause evidence,
- complete sibling search,
- fix,
- reusable invariant/tool improvement,
- target verification still required.

Do not append chronological debugging transcripts here.
