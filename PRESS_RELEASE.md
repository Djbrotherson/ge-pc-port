# Press Release — ARM-GE GoldenEye 007 Native ARM64 Linux Alpha

**For immediate release — 25 September 2026**

## Reconstructed GoldenEye 007 codebase now running natively on ARM64 Linux handheld hardware

The ARM-GE project has reached a public alpha milestone: GoldenEye 007's reconstructed Nintendo 64 codebase is running as native AArch64 Linux software on low-cost ARM handheld hardware using SDL2 and OpenGL ES.

This is a native source-porting effort, not N64 emulation.

### Current showcase

https://www.youtube.com/shorts/lcN9C9waB6I

This is the current canonical showcase clip for the project.

### Current real-device state

On R36S-class hardware through the PortMaster stack, the project has demonstrated:

- native AArch64 execution;
- SDL2 / OpenGL ES rendering;
- boot, menus and intro;
- in-mission rendering and gameplay;
- controller integration;
- PortMaster install and launch;
- first-run generation of required ROM-derived sidecars from the user's own compatible ROM;
- runtime logging and on-device diagnostics.

### Why the port is technically difficult

The reconstructed source still carries assumptions inherited from the original Nintendo 64 environment. The ARM64 porting work has exposed recurring classes of incompatibility around:

- 32-bit segmented and ROM-address tokens;
- MIPS-era signedness and pointer-width assumptions;
- ABI and binary layout dependencies;
- desktop OpenGL functionality that is unavailable in OpenGL ES;
- runtime behavior that relied on invariants guaranteed by the original console.

A central project rule is to classify values before changing them:

1. native host pointer;
2. N64 / ROM / segmented-address token;
3. ordinary integer or game state.

That has allowed the project to fix semantic bug classes rather than individual crashes one by one.

### Broader goal

GoldenEye is the proving ground.

The longer-term objective is to extract reusable methods, validation rules and tooling for moving reconstructed/decompiled N64-era software onto modern ARM64 / GLES / Linux targets.

### Public links

**Source:**  
https://github.com/bitflipunix-re/ge-pc-port

**Showcase:**  
https://github.com/bitflipunix-re/ge-pc-port/blob/main/SHOWCASE.md

**Alpha testers:**  
https://github.com/bitflipunix-re/ge-pc-port/issues/6

**Media / creators:**  
https://github.com/bitflipunix-re/ge-pc-port/issues/7

**Real-device tester thread:**  
https://www.reddit.com/r/R36S/comments/1wos5ea/goldeneye_007_n64_arm64_call_for_alpha_testers/

### Legal

No GoldenEye ROM or generated ROM-derived sidecar binaries are distributed by the project. Users provide their own compatible legally obtained NTSC-U ROM.

GoldenEye 007 and associated names and trademarks belong to their respective rights holders. ARM-GE is a non-commercial fan preservation/porting effort and is not affiliated with or endorsed by Nintendo, Rare, MGM, EON Productions, Danjaq, or other rights holders.

Support options for the project may be added in the future.
