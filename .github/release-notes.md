## GoldenEye 007 PC Port <version>

<p align="center">
  <img src="https://github.com/jkdansereau/goldeneye-pc-port/raw/v0.2.0/docs/media/goldeneye-gh-preview.gif" width="480"
       alt="~32 s gameplay montage from live play sessions (no audio track)">
</p>

> The full single-player campaign runs at a steady 60 fps with audio (music +
> SFX) playing throughout, on Windows and Linux including Steam Deck, and it
> is completable end to end: the whole campaign has been playtested through
> all 21 missions (Agent difficulty). It's an early public cut: all 21 solo
> missions load and run crash-free, but the known issues below are real;
> feedback is very welcome.

### What's new since v0.2.0

Small hotfix batch from user playtest feedback on v0.2.0:

- **Fixed: `All unlocked` + a fresh save produced silent music/SFX** (D259).
  A brand-new save now seeds max volume the same way the N64 does, whether
  or not `All unlocked` is on.
- **Mouse wheel weapon cycling now matches the on-screen wheel-menu order**:
  scroll up = previous weapon, scroll down = next (D260).
- **Watch menu: holding a direction now auto-repeats** instead of crawling
  one item per key press/notch (D261).
- **Fixed: the watch menu's item-preview 3D model wasn't rendering** —
  weapons now show their model when selected on the watch inventory page
  (D264).
- Investigated the Facility report of Ourumov never executing Trevelyan:
  confirmed it's proximity/line-of-sight-triggered exactly as on the N64
  (walk toward the room), not a port bug — the full scripted beat, including
  the execution shot, fires correctly (D263).

### What's new since v0.1.0

- **Drop-in ROM, no tooling**: unpack the bundle, drop your NTSC-U (US) ROM
  in `data/`, launch; the first run generates the derived assets
  automatically. No Python, no installer, nothing to set up.
- **Steady 60 fps** in normal play (the software RSP runs off the presentation
  critical path); `Video.DisplayFPS` in the F10 overlay shows it.
- **Audio**: in-level music and sound effects throughout (the alpha was
  silent). A handful of tracks have wrong-sounding instruments (below).
- **Mouse**: click-to-lock capture (click to grab, ESC to release) with a
  proportional GEPD-style aim mode; sensitivity / Y-inversion / aim-turn split
  tunable in `ge007.ini` or the F10 overlay. The legacy always-grab mode is
  gone.
- **Rendering**: outdoor skies render correctly; water no longer renders
  green/pulsing; reflective surfaces (glass, chrome weapon skins) work.
- **Crash fixes**: the two v0.1.0-era crashing levels (Bunker ii, Statue) and
  the AI-pacing bug that broke Cradle are fixed and playtest-verified: all 21
  solo missions load and run crash-free. Also fixed: the Steam Deck / Linux
  Facility crash triggered by walking into the crouch-forcing spot at the
  level's opening (D253); this also revives the auto-crouch and ladder
  signals, which were dead on PC before.
- **QoL**: F10 in-game options overlay (fullscreen, resolution, frame cap,
  MSAA, texture filtering, FOV/draw distance, sensitivity), F12 screenshot.
- **Sharper defaults out of the box**: draw distance and LOD swap distance now
  default to 150% of the authored N64 values, so props no longer fade in just
  before they become visible (Dam's alarms and wall switches being the tell);
  F10 → *Draw distance* / *LOD distance* set back to 100 restores the
  console-authentic look. MSAA now defaults to 4× instead of off.
- **All-unlocked toggle**: F10 → *All unlocked* makes all 21 solo levels
  selectable at every difficulty from the first launch, adds 007 mode, and
  fully populates the cheat menu. It is off by default (faithful N64
  progression). No *active* cheats are enabled either way (weapons remain
  per-mission pickups, as on N64).
- **Steam Deck first-run preset**: on SteamOS the first launch seeds
  Deck-friendly defaults (native 1280×800 fullscreen, VSync, MSAA 4, 150%
  draw/LOD distance); an existing `ge007.ini` always wins. Two more F10 rows:
  *No hit flash* (suppresses the damage-flash overlay) and *Skip intro*.
- **Modern dual-stick controller layout** (the scheme used by the console
  re-releases): left stick move/strafe, right stick look, right trigger fire,
  left trigger aim, A/X use, B/Y crouch/cancel, **RB/LB cycle weapons**.
- **Linux / Steam Deck**: the Linux bundle now ships its own SDL2, so it runs
  as-is on any distro, and sideloads onto a Steam Deck with nothing
  installed. Saves and F10 settings now persist no matter which directory you
  launch from (previously Linux wrote them relative to the launch directory
  only, so they silently failed elsewhere; D256); the options overlay is
  fully gamepad-driven on the Deck.

### Known issues

- **Cutscenes still glitch, mostly with James Bond**: in scripted sequences
  Bond is the one who gets misplaced, hovers, or spins; the other actors are
  fine for the most part now. The Dam level-end cutscene is racy (D243).
  Still the most visible gap in this release.
- **Particle colours cycle through a rainbow palette**: bullet-impact sparks
  and lingering smoke/explosion residue drift through the hues over time
  instead of holding their intended grey/orange palette (D252).
- Water on `IsWater` levels shows a moving seam between two patterns (D245);
  thin pixel strips at the left/right screen edges at non-integer window
  scales (D246).
- The front-end **Nintendo logo renders as two white blobs**, and the
  Rareware logo is close but its texture filtering looks off (D75).
- The F10 overlay's **bottom row duplicates whatever item is currently
  selected** (e.g. the MSAA value appears both on its own row and again at
  the panel bottom); earlier builds showed it as an intermittent 4K-
  fullscreen ghost of the top row.
- **Surface 1: the 2D billboard trees near the start render as a solid wall
  of tree texture** instead of discrete sprites (D236). Under active
  investigation; no fix in this release.
- **Steam Deck: one intermittent crash remains**: the v0.1.0-era Facility
  crash is confirmed fixed on Deck hardware, but a SIGSEGV can occasionally
  occur during heavy firefights (D255; seen on Bunker and Frigate). The
  faulting-register capture in `ge007.crash.log` has pinned it: an object
  record whose model reference is NULL while the record is still active;
  i.e. something in a mid-firefight destruction leaves the record live one
  tick too long. We're tracking down the exact destruction path; more Deck
  playtime across levels is welcome; please report any Deck-specific faults.

### Downloads

| File | Platform |
|---|---|
| `goldeneye-pc-port-<version>-win64.zip` | Windows x86-64 |
| `goldeneye-pc-port-<version>-linux-x86_64.tar.gz` | Linux x86-64 (incl. Steam Deck) |

Each contains the engine executable, a README, license texts, and the
`prepare-assets` tool. **No ROM, no game assets.** The Windows bundle carries
its runtime DLLs; the Linux bundle carries SDL2, so on both platforms nothing
needs to be installed first.

### Running it

You supply your own **GoldenEye 007 N64 ROM** (`.z64`, big-endian) that you
legally own: the **NTSC-U (US)** release is what this build supports (PAL / JP
are on the roadmap). No Python, no toolchain, nothing to install.

1. Unpack the archive.
2. Make a `data/` folder next to the executable and put the ROM in it, named
   `ge007.ntsc-final.z64`.
3. Run the executable **from that folder**. The first run takes a few extra
   seconds: it detects your ROM, generates the two derived asset folders
   (`data/pcmodels-ntsc-final/`, `data/pccg-ntsc-final/`) once, and saves them
   for every future run. (The generator is `prepare-assets/ge007-convert`
   inside the bundle; you can also run it manually; it prints what it's doing.)

**Steam Deck:** sideload the unpacked folder (USB or a file manager), do steps
2–3, then add the executable to Games → *Add Game* as a non-Steam game.

**In-game settings on the Deck:** the options overlay is fully gamepad-driven:
it opens with **Select**, the D-pad or left stick (up/down) moves between
options, **A** steps the selected option forward, **B** steps it back, and
**Start** (or Select again) closes. No keyboard needed.

Full steps are in the bundled `README.md`.

### Verify the download

```
sha256sum -c goldeneye-pc-port-<version>-win64.zip.sha256
sha256sum -c goldeneye-pc-port-<version>-linux-x86_64.tar.gz.sha256
```

### Source & docs

<https://github.com/jkdansereau/goldeneye-pc-port>, built on the
[GoldenEye 007 decompilation](https://github.com/n64decomp/007), architecture
after the [Perfect Dark PC port](https://github.com/fgsfdsfgs/perfect_dark).
Non-commercial fan preservation/research project; not affiliated with any
rights holder.
