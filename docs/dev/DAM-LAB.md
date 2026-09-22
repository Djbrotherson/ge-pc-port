# Dam Behavioral Lab

Branch: `dam-only-lab`

This branch is a temporary GoldenEye behavioral-research environment. It is
not the release line and it is not intended to remain GoldenEye-specific
forever.

The purpose is to reduce the remaining gameplay-correctness problem to one
fully understood mission, then convert every reusable finding into Portkit
contracts, detectors, adapters, tests, or runtime invariants before merging the
general fix back to `main`.

## Why Dam

Dam is the first controlled specimen because it exercises the full chain needed
to trust the rest of the port:

- stage/setup loading,
- intro/spawn records,
- pad conversion,
- pad -> STAN linking,
- floor-height calculation,
- room ownership,
- player/camera placement,
- collision/navigation,
- AI and patrol paths,
- doors and props,
- objectives,
- mission progression,
- renderer/runtime behavior on real R36S hardware.

The current symptom that motivated this branch is deterministic and high value:
the latest full port loads Dam, but Bond starts in the wrong world position and
must traverse undefined geometry to reach the authored level.

## Dam oracle

The decompiled NTSC-U setup is the source oracle for the first spawn.

Expected single-player Dam start:

| Field | Expected |
|---|---|
| Stage | Dam |
| Spawn pad | 33 |
| Pad position | `(4719, -18, 3949)` |
| Look vector | approximately `(-1, 0, -0.000643)` |
| Pad plink | `p6g1` |

A runtime value that disagrees with this oracle tells us where the conversion or
runtime semantic chain diverged. The lab must log source truth and runtime truth
side-by-side rather than compensating silently.

## Deterministic branch behavior

The lab branch intentionally:

- forces solo mission selection to Dam,
- forces Agent difficulty for the baseline path,
- records the exact intro spawn selected,
- records the converted pad position/look/STAN,
- continuously samples player position, camera position, room and STAN state,
- records large position jumps and invalid topology,
- exposes FPS, process CPU usage and RAM usage on-screen,
- writes a structured `damlab.log` for a whole-session analysis pass.

These changes are research instrumentation. They should not be merged to
`main` unchanged.

## On-screen HUD

The R36S lab HUD is deliberately independent of the normal game UI. It is drawn
directly in the host video layer so it remains visible even if GoldenEye HUD or
display-list state is part of the failure.

It reports:

- FPS,
- process CPU percentage,
- process RSS,
- player/world position,
- current room,
- whether the player has a valid STAN,
- accumulated anomaly flags.

The HUD is diagnostic, not a release feature.

## Port Control overlay

The Dam branch also carries the redesigned `F10` **ARM-GE // PORT CONTROL**
overlay. It preserves the historical toggle binding and existing keyboard,
mouse and controller navigation, but replaces the old flat settings list with
five capability pages:

- **Video** — fullscreen, resolution, VSync, frame cap, MSAA, texture filter,
  independent mipmap filtering, anisotropy, framebuffer effects, mip/wrap
  fixes, GoldenEye Full/Wide/Cinema screen mode, GoldenEye Normal/16:9 aspect
  ratio, FOV and draw/LOD distance controls.
- **Audio** — mute, master volume, queue limit and device buffer controls plus a
  live queue-depth gauge.
- **Input** — mouse/pad/aim sensitivity, response, smoothing, deadzone,
  inversion, 1:1 menu-pointer mode and menu/hip-fire tuning.
- **Game** — screen-shake intensity, skip-intro, hit-flash and unlock controls
  already owned by the host config layer.
- **System** — independent toggles for the FPS-only counter and the CPU/FPS/RAM
  Dam HUD, plus input logging and read-only runtime telemetry: CPU, FPS,
  process/system memory, audio queue depth, stage, room, STAN state, position
  and anomaly flags. Hiding the Dam HUD does not stop `damlab.log` collection.

The System and Audio diagnostics intentionally read existing runtime state only;
they do not alter GoldenEye gameplay state. This makes the overlay usable as a
real-device debugging surface while the separate always-on Dam HUD continues to
provide crash-frontier visibility.
## Structured trace

The lab writes `damlab.log` in the game working directory.

Records use a single-line machine-readable form beginning with `DAMLAB`.

Important record types:

- `DAMLAB_BEGIN` — records the source oracle and test configuration,
- `kind=SPAWN` — exact setup spawn chosen and its converted values,
- `kind=EVENT` — room/camera/topology transition or newly detected anomaly,
- `kind=TICK` — periodic gameplay snapshot,
- `kind=END` — clean lab shutdown.

Snapshots include:

`stage`, `cammode`, `room`, `spawn`, player position, camera position,
STAN pointer, STAN height, FPS, CPU, RSS, available system memory and anomaly
flags.

The goal is not maximum log volume. The goal is enough state to reconstruct the
entire semantic chain from stage load through gameplay with one device run.

## One-sweep workflow

For each R36S run:

1. start from a fresh, matching binary/converter/sidecar set,
2. launch the Dam lab,
3. move through as much of the level as possible,
4. exercise doors, guards, pickups, objectives and transitions,
5. exit cleanly when possible,
6. preserve `damlab.log` and the normal runtime log,
7. compare runtime values against the decompiled Dam oracle,
8. classify every divergence by semantic class,
9. batch-fix the class rather than one symptom,
10. add a reusable detector/contract/test when the rule is not Dam-specific.

A device test should answer multiple questions at once. If a value can be
proven statically or from a converter contract, add that proof instead of
requiring another hardware run.

## Graduation rule

A Dam finding belongs in `main` only when it has been classified.

Examples:

- pointer/token/layout rule -> Portkit or ABI contract,
- setup/record conversion rule -> converter/runtime cross-check,
- STAN/pad topology rule -> reusable semantic validator,
- host lifecycle rule -> runtime invariant,
- truly GoldenEye-specific gameplay behavior -> narrow title-specific patch.

Dam-only forced-stage logic, HUD code and verbose telemetry remain isolated
unless a generic target-telemetry facility is intentionally extracted.

## Completion criteria

The Dam lab is considered successful when:

- spawn pad 33 matches the source oracle exactly before floor-height adjustment,
- pad 33 resolves to the correct authored STAN without fallback recovery,
- Bond begins inside valid level topology,
- player/camera/room/STAN remain internally consistent during traversal,
- collision and navigation do not require undefined-geometry traversal,
- doors/props/AI/objectives behave correctly enough to complete the mission,
- no unexplained position jumps or invalid rooms appear in the trace,
- the resulting fixes are captured as reusable rules wherever practical.

Once Dam is behaviorally trustworthy, the same telemetry method becomes the
template for representative-level regression across the rest of the game.
