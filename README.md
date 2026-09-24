# ARM-GE — GoldenEye 007, Native on ARM64 Linux

> **GoldenEye 007's reconstructed Nintendo 64 codebase running natively on ARM64 Linux handheld hardware — AArch64 + SDL2 + OpenGL ES, not N64 emulation.**

ARM-GE is an open-source engineering effort to make the reconstructed GoldenEye 007 Nintendo 64 codebase run as native software on low-power ARM64 Linux handhelds.

The current reference target is **R36S / dArkOSRE / PortMaster** using **AArch64 + SDL2 + OpenGL ES 3**.

## See it running

- **Alpha testing / real-device reports:**  
  https://www.reddit.com/r/R36S/comments/1wos5ea/goldeneye_007_n64_arm64_call_for_alpha_testers/
- **Current alpha release links:**  
  https://www.reddit.com/r/u_Appropriate_Comb1486/comments/1woso74/goldeneye_007_n64_arm64_port_alpha_release_links/

The interesting part is not simply that GoldenEye runs on another device. The engineering problem is moving reconstructed software that still carries a 1990s console's ABI, address model, graphics assumptions and runtime invariants onto a modern 64-bit ARM Linux host.

## Current alpha

The latest verified R36S PortMaster build was produced on 24 September 2026 from:

- source revision: `c762a153a75ac6eadbef6fa4e4547bf465597ecd`
- installer: `ge007.zip`
- installer SHA-256: `738c0c754ffab04911651db14095604aa0cbc5e3f1f2478b3ddf917681381eb9`
- architecture: AArch64
- graphics: SDL2 + GLES
- ROM target: GoldenEye 007 NTSC-U, big-endian

The CI build verifies the executable as AArch64, builds the PortMaster package, runs `unzip -t`, validates package metadata, and rejects ROM files or generated sidecar binaries from the release archive.

## What works on real hardware

The port has demonstrated:

- native AArch64 execution on R36S-class hardware;
- SDL2/GLES rendering;
- boot, menus and intro;
- in-mission rendering and gameplay;
- controller integration;
- PortMaster install and launch;
- first-run generation of required ROM-derived sidecars from the user's own ROM;
- runtime logging and on-device diagnostics.

Active work is focused on correctness and polish: stage behavior, spawn positions, AI/objectives/props, collision/navigation edge cases, GLES rendering defects, audio/runtime behavior and broader handheld compatibility.

## The portability work

Porting reconstructed N64 software to a modern host is not a mechanical 32-bit-to-64-bit conversion.

A recurring rule in this project is to classify values before changing them:

1. **native host pointer**
2. **N64 / ROM / segmented-address token**
3. **ordinary integer or game state**

That distinction drives whole-class fixes for LP64 correctness rather than one-crash-at-a-time patches.

Other recurring problem areas include:

- MIPS-era signedness and pointer-width assumptions;
- binary structure layout and ABI dependencies;
- segmented and ROM address translation;
- desktop OpenGL behavior that is unavailable in OpenGL ES;
- gameplay/runtime behavior that depended on N64-era invariants;
- generated sidecar and asset formats crossing host architectures.

The longer-term goal is to turn those lessons into reusable N64-to-modern-host portability tooling and documentation.

## Install model

This repository and its release package do **not** include a GoldenEye ROM or generated ROM-derived sidecars.

After installing the PortMaster package, provide your own legally obtained US NTSC big-endian ROM at:

`ge007/data/ge007.ntsc-final.z64`

Expected SHA-1:

`abe01e4aeb033b6c0836819f549c791b26cfde83`

The first launch generates the required host-format data locally and then starts the game.

## Repository layout

- `work/goldeneye-pc-port/` — source-port tree used for the ARM64 build
- `port/` — PortMaster launcher and package metadata
- `bundle/prepare-assets/` — local ROM-to-sidecar conversion tooling
- `package.py` — builds and validates the distributable PortMaster ZIP
- `watch/` — PortMaster exit-hotkey helper
- `.github/workflows/build-r36s.yml` — reference AArch64/GLES build and packaging proof
- `PRESS.md` — concise media / creator briefing and verified public links

## Building

The reference build is the GitHub Actions workflow in `.github/workflows/build-r36s.yml`.

For local package assembly after producing `ge007.aarch64`:

```sh
python3 package.py --game-bin path/to/ge007.aarch64 --out dist
```

The packager refuses to include `.z64`, `.n64`, `.v64`, `pcmodels.bin` or `pccg.bin` files.

## Contributing

Help is welcome, particularly with real-device testing, GLES rendering, ARM64/LP64 semantics, gameplay correctness, PortMaster compatibility and documentation.

See [CONTRIBUTING.md](CONTRIBUTING.md).

For journalists, video creators and technical writers, see [PRESS.md](PRESS.md).

## Lineage and attribution

This project builds on the work of:

- [n64decomp/007](https://github.com/n64decomp/007) — GoldenEye 007 reconstruction/decompilation;
- [jkdansereau/goldeneye-pc-port](https://github.com/jkdansereau/goldeneye-pc-port) — PC/source-port foundation;
- [fgsfdsfgs/perfect_dark](https://github.com/fgsfdsfgs/perfect_dark) and related Fast3D lineage used by the renderer.

ARM64/R36S work and PortMaster packaging are maintained by **bitflipunix** and **Tomobobo710**, with contributions welcomed from the wider community.

Existing copyright and license notices in inherited and third-party code are preserved. See [NOTICE.md](NOTICE.md) and the license files within the source tree.

## Legal

No ROM is distributed by this project. No generated ROM-derived sidecar binaries are included in the PortMaster package.

GoldenEye 007 and associated names and trademarks belong to their respective rights holders. This is a **non-commercial fan preservation/porting effort** and is not affiliated with or endorsed by Nintendo, Rare, MGM, EON Productions, Danjaq, or other rights holders.

Any future commercial activity around this work is intended to concern original tooling, engineering services, educational material or creator content—not distribution or sale of GoldenEye game data.
