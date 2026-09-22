# Graphics / Runtime Backlog

This backlog contains only issues worth re-validating on the current AArch64
R36S build.

Historical desktop-only findings and resolved investigations are preserved in
git history.

## Priority 0 — release blockers

### Texture/state corruption after death or level reload

A host renderer cache reset has been paired with the game's texture reset at
level-load/reload boundaries.

Status: **fix candidate landed; current-main R36S re-test required**.

Test:

1. boot a mission cleanly,
2. observe representative textures,
3. die/restart repeatedly,
4. revisit the same surfaces/models,
5. confirm texture/palette/shader state does not leak across reloads.

### Mission-transition / cutscene reliability

Historical testing exposed cutscene/camera/actor-state inconsistencies.

Status: **requires current-main R36S reproduction before further changes**.

Do not patch an individual cutscene until the failing semantic class is known.

## Priority 1 — rendering correctness

### Surface/tree billboard rendering

Reported symptom: tree/billboard assets can render as sheets/walls instead of
discrete sprites.

Likely subsystem: texture/tile state, alpha/fog, LOD selection or billboard
draw semantics.

Action: reproduce on current-main R36S first.

### Distant geometry / large-level culling

Reported on large open scenes.

Likely subsystem: portal visibility, far-plane/depth handling, LOD or culling.

Action: capture one deterministic sightline and classify whether geometry is
removed by game LOD or renderer visibility.

### Transparency / alpha-blended surfaces

Potential symptoms include opaque glass, missing translucent geometry or wrong
draw ordering.

Action: reproduce a specific surface on current main, then inspect render mode,
alpha compare and depth-write semantics as one class.

### Particle color / texture progression

Particle effects have previously shown palette/texture-color drift.

Action: current-main R36S reproduction, then distinguish source texture decode
from tile/palette/cache state.

### Sky / backdrop paths

Some sky/backdrop rendering paths use unusual N64 raster/display-list behavior.

Action: current-main device screenshot and deterministic level/camera repro
before modifying renderer code.

## Priority 2 — enhancements

These are not compatibility fixes and should remain independently toggleable:

- widescreen/aspect correction,
- FOV controls,
- higher internal resolution,
- LOD/detail controls,
- texture replacement,
- mod/asset override path,
- frame-pacing options.

Enhancements must not become prerequisites for accurate baseline rendering.

## Triage rule

For every graphics issue:

1. reproduce on current `main`,
2. capture exact level/camera/action,
3. identify whether the game emitted wrong data or the renderer interpreted
   correct data incorrectly,
4. search the whole semantic class,
5. batch-fix proven siblings,
6. add a reusable renderer/audit invariant where possible.

Do not keep closed visual investigations in this file.
