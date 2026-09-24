# mouse-injector (removed from public repo)

The GEPD-Edition Mouse Injector source (GPLv2, ~1.5 MB including a prebuilt
`discord-rpc.lib`) was vendored here as a read-only reference for the PC
port's mouse-aim model, and **removed from the public repo on 2026-09-19**
during the v0.3.0 release review: it is GPL-licensed code (plus a binary)
inside an MIT-licensed project, and it is not compiled or linked by anything
in this tree — it was consulted by developers only.

## Provenance (if you need to re-vendor it locally)

- Project: "GEPD-Edition Mouse Injector" (GoldenEye 007 / Perfect Dark N64
  mouse-aim injection for emulators), GPLv2.
- The file that mattered was `games/goldeneye.c` (~380 lines — the whole GE
  aim/hipfire/menu model), plus `device.c` (raw mouse polling) and
  `maindll.h` (tickrate units).

## What replaced it in this repo

- The ported, calibrated result lives in `port/src/input.c` (the D194
  lineage; see `docs/dev/GEPD-INPUT-PLAN.md` for the design record, which
  quotes the model inline).
- Historical findings that cite `reference/mouse-injector/...` paths
  (`docs/dev/findings.md`, D194/D214/etc.) remain accurate as written; the
  cited file content is preserved in those write-ups.

If you want the original source again for reference work, clone it locally
into `reference/mouse-injector/` (it is gitignored now) — do not commit it.
