# ARM-GE press / creator brief

## One-line story

**GoldenEye 007's reconstructed Nintendo 64 codebase is now running natively on low-cost ARM64 Linux handheld hardware as an AArch64 + SDL2 + OpenGL ES application — not through N64 emulation.**

## Why this is technically interesting

The reconstructed source still carries assumptions from the original Nintendo 64 environment. Moving it to a modern 64-bit ARM Linux host exposes problems that normal desktop ports can hide:

- 32-bit N64 / ROM / segmented-address tokens that can be confused with native pointers;
- MIPS-era signedness and integer-width behavior;
- ABI and binary structure-layout assumptions;
- renderer behavior that exists in desktop OpenGL but not OpenGL ES;
- gameplay/runtime invariants that only held because the original console environment made them true.

A central project rule is to classify values before changing them:

1. native host pointer;
2. N64 / ROM / segmented-address token;
3. ordinary integer or game state.

That enables class-wide fixes rather than chasing individual crashes.

## Current state

Verified on R36S-class ARM64 Linux hardware through PortMaster:

- native AArch64 execution;
- SDL2 + GLES rendering;
- boot / menus / intro;
- in-mission rendering and gameplay;
- controller integration;
- install / launch flow;
- first-run local generation of required ROM-derived sidecars;
- runtime logging and device diagnostics.

The project remains an alpha. Current work focuses on gameplay correctness, stage behavior, spawn positions, AI/objectives/props, collision/navigation edge cases, GLES defects, audio/runtime behavior and wider handheld compatibility.

## Public links

**Source**
https://github.com/bitflipunix-re/ge-pc-port

**Alpha testing / real-device reports**
https://www.reddit.com/r/R36S/comments/1wos5ea/goldeneye_007_n64_arm64_call_for_alpha_testers/

**Current alpha release links**
https://www.reddit.com/r/u_Appropriate_Comb1486/comments/1woso74/goldeneye_007_n64_arm64_port_alpha_release_links/

## Accuracy notes

- This is a **native source-porting effort**, not N64 emulation.
- It is **not** a claim to be the first ARM64 GoldenEye implementation.
- The repository does **not** distribute a GoldenEye ROM.
- Release packages do **not** include generated ROM-derived sidecar binaries.
- Users provide their own compatible legally obtained NTSC-U ROM.

## Broader project direction

GoldenEye is the current proving ground. The broader engineering objective is to extract reusable patterns, validation methods and tooling for moving reconstructed/decompiled N64-era software onto modern ARM64/GLES/Linux targets.

That includes work around:

- LP64 semantic auditing;
- N64-address-token handling;
- binary-layout validation;
- graphics translation and capability detection;
- host-format conversion;
- PortMaster packaging;
- repeatable real-device diagnostics.

## Suggested story angles

- **Software archaeology:** what survives from the N64 hardware contract inside reconstructed C?
- **ARM64 correctness:** why “just compile it for 64-bit” fails.
- **Graphics portability:** moving desktop GL assumptions onto OpenGL ES handhelds.
- **Game preservation:** reconstructed historical software becoming native on modern machines.
- **Low-cost hardware:** using inexpensive Linux handhelds as real native targets rather than emulation boxes.
- **Tooling:** turning one difficult port into reusable N64 portability methods.

## Credits

The project builds on:

- n64decomp/007;
- jkdansereau/goldeneye-pc-port;
- fgsfdsfgs/perfect_dark and related Fast3D renderer lineage.

ARM64/R36S work and PortMaster packaging are maintained by **bitflipunix** and **Tomobobo710**.

## Legal

GoldenEye 007 and associated names and trademarks belong to their respective rights holders. ARM-GE is a non-commercial fan preservation/porting effort and is not affiliated with or endorsed by Nintendo, Rare, MGM, EON Productions, Danjaq, or other rights holders.

Commercial activity, if developed separately, should concern original tooling, engineering services, educational material or creator content—not sale or distribution of GoldenEye game data.
