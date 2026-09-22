# Documentation

Current documentation only.

## Start here

- [dev/DAM-LAB.md](dev/DAM-LAB.md) — **dam-only-lab branch mission, oracle, telemetry and graduation rules.**

- [../portkit/README.md](../portkit/README.md) — Portkit product surface.
- [../portkit/ARCHITECTURE.md](../portkit/ARCHITECTURE.md) — reusable architecture.
- [R36S-BUILD.md](R36S-BUILD.md) — current AArch64/GLES target build.
- [porting-notes.md](porting-notes.md) — reusable N64→host semantic rules.
- [internals.md](internals.md) — current repository architecture.
- [dev/LEVEL-STATUS.md](dev/LEVEL-STATUS.md) — current level/runtime evidence.
- [dev/GRAPHICS-BACKLOG.md](dev/GRAPHICS-BACKLOG.md) — current graphics/runtime backlog.
- [../tools_pc/README.md](../tools_pc/README.md) — living GoldenEye-specific tools.

## Repository CI

```sh
python3 tools/n64_port.py gate
```

## Documentation policy

Current architecture belongs in `portkit/` and `docs/`.

Detailed runtime evidence belongs under `docs/dev/`.

Closed investigations are preserved by git history and are removed from the
working tree once their reusable rule or permanent test has been captured.
