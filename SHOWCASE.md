# Current ARM-GE showcase

## Latest public video

[![GoldenEye 007 native ARM64 Linux showcase](https://img.youtube.com/vi/lcN9C9waB6I/hqdefault.jpg)](https://www.youtube.com/shorts/lcN9C9waB6I)

**Watch:** https://www.youtube.com/shorts/lcN9C9waB6I

This Short is the **single current video showcase** for ARM-GE. Older clips are intentionally not used here so viewers, testers, journalists and contributors see one consistent representation of the latest public state.

## What the project is

ARM-GE is an open-source effort to run the reconstructed GoldenEye 007 Nintendo 64 codebase as **native AArch64 Linux software** on low-power ARM64 handhelds.

Reference stack:

- R36S-class ARM64 handheld hardware
- dArkOSRE / PortMaster
- AArch64 Linux
- SDL2
- OpenGL ES 3

This is a **native source-porting effort, not N64 emulation**.

## Verified current project state

The project has demonstrated on real hardware:

- native AArch64 execution;
- SDL2 / GLES rendering;
- boot, menus and intro;
- in-mission rendering and gameplay;
- controller integration;
- PortMaster install and launch;
- first-run generation of required ROM-derived sidecars from the user's own compatible ROM;
- runtime logging and on-device diagnostics.

The alpha remains under active development. Current work is concentrated on gameplay correctness, stage behavior, spawn positions, AI/objectives/props, collision/navigation edge cases, GLES rendering defects, audio/runtime behavior and broader handheld compatibility.

## Why it matters

The hard part is not merely compiling old C for ARM64. Reconstructed N64 software still carries assumptions from the original machine:

- 32-bit segmented and ROM-address tokens;
- pointer-width and signedness behavior inherited from MIPS;
- binary layout and ABI dependencies;
- graphics behavior that desktop OpenGL may provide but GLES does not;
- runtime assumptions that were implicitly guaranteed by the original console.

A recurring rule in the port is therefore:

1. native host pointer;
2. N64 / ROM / segmented-address token;
3. ordinary integer or game state.

Classify the semantic type first, then fix the entire bug class.

## Get involved

**Source:**  
https://github.com/bitflipunix-re/ge-pc-port

**Alpha testers:**  
https://github.com/bitflipunix-re/ge-pc-port/issues/6

**Media / creators:**  
https://github.com/bitflipunix-re/ge-pc-port/issues/7

**Real-device tester thread:**  
https://www.reddit.com/r/R36S/comments/1wos5ea/goldeneye_007_n64_arm64_call_for_alpha_testers/

## Legal

No ROM or generated ROM-derived sidecar binaries are distributed by this project. Users provide their own compatible legally obtained GoldenEye 007 NTSC-U ROM.

GoldenEye 007 and associated names and trademarks belong to their respective rights holders. ARM-GE is a non-commercial fan preservation/porting effort and is not affiliated with or endorsed by Nintendo, Rare, MGM, EON Productions, Danjaq, or other rights holders.
