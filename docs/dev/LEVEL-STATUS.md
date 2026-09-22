# R36S Runtime Status

This file tracks the current `main` branch only.

Historical desktop sweeps and closed crash investigations are preserved in git
history and intentionally removed from the working tree.

## Target

- Device: R36S
- Runtime: dArkOSRE / PortMaster
- Architecture: AArch64
- Graphics: SDL2 + GLES 3
- Input: GO-Super Gamepad
- ROM: GoldenEye 007 NTSC-U

## Proven on the R36S path

The current port lineage has demonstrated:

- PortMaster launch,
- ROM detection and clean missing-ROM handling,
- native AArch64 execution,
- GLES context/rendering,
- menus,
- intro sequences,
- mission rendering and gameplay,
- controller input,
- ROM-derived sidecar loading,
- broad LP64/N64 ABI stabilization.

These are milestone proofs, not a claim that every mission and feature has been
fully regression-tested on the current `main` commit.

## Current validation gate

Before calling the R36S port release-ready, run the following on the exact
current `main` artifact.

| Area | Required current-main proof |
|---|---|
| Boot | Fresh PortMaster launch reaches front end |
| ROM | Correct NTSC-U ROM accepted; bad/missing ROM fails cleanly |
| Menus | File/menu navigation stable |
| Mission load | Representative early/mid/late missions load |
| Gameplay | Movement, shooting, AI, objectives, doors and pickups |
| Death/restart | Repeated restart does not corrupt textures/state |
| Mission transition | Completion → report → next briefing/mission |
| Cutscenes | Intro/outro cameras and actors behave consistently |
| Audio | Music/SFX initialize and survive extended play |
| Input | Analog, buttons, pause and exit behavior |
| Rendering | No systemic missing geometry, palette corruption or stale textures |
| Performance | Sustained interactive frame pacing on device |
| Save | Save/load path survives restart and relaunch |
| Packaging | Fresh install contains only required runtime files |

## Campaign matrix

A complete current-main campaign replay has not yet been re-certified on R36S.

Use this table for the next device sweep and update it with the tested commit.

| Mission group | Status |
|---|---|
| Early campaign | Needs current-main device pass |
| Mid campaign | Needs current-main device pass |
| Late campaign | Needs current-main device pass |
| Bonus missions | Needs current-main device pass |
| Multiplayer | Not yet release-gated |

Do not import old desktop PASS/FAIL state into this table.

## High-value regression scenarios

Prioritize scenarios that exercise host-port failure classes:

1. die/restart the same mission repeatedly,
2. transition between missions without restarting the process,
3. enter/exit menus repeatedly,
4. trigger dense AI/animation scenes,
5. exercise large/open levels and distant geometry,
6. trigger particles, transparency and CI/palette-heavy textures,
7. run long enough to expose cache/lifetime leaks,
8. save, relaunch and resume.

## Reporting format

For each real-device result record:

- commit SHA,
- package/build artifact,
- mission/scenario,
- reproduction steps,
- observed result,
- crash/log filename if applicable,
- whether the failure reproduces after a clean boot.

Only current-main R36S evidence belongs in this file.
