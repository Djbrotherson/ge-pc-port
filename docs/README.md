# Documentation

This directory contains the current architecture and the engineering record for
our R36S/AArch64 port and reusable N64 porting toolchain.

## Start here

- [R36S-BUILD.md](R36S-BUILD.md) — current AArch64/GLES target build and verification path.
- [PORTING-TOOLSET.md](PORTING-TOOLSET.md) — reusable toolchain architecture,
  profiles, ABI contracts, validation tiers and roadmap.
- [porting-notes.md](porting-notes.md) — recurring N64→host semantic failure
  classes distilled from real port work.
- [dev/LEVEL-STATUS.md](dev/LEVEL-STATUS.md) — detailed runtime evidence and
  level-specific status.
- [dev/GRAPHICS-BACKLOG.md](dev/GRAPHICS-BACKLOG.md) — graphics/runtime issues
  that still need validation or work.
- [../tools_pc/README.md](../tools_pc/README.md) — converter, verification and
  investigation-tool index.

## Tool documentation

The stable command surface is:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
python3 tools/n64_port.py show-profile
```

Profiles and ABI contracts live in `tools/port_profiles/`.

## Engineering records

Files under `docs/dev/` are evidence and historical debugging records. They
are intentionally not treated as the public project narrative. When a
historical finding becomes a reusable rule, the distilled version belongs in
`porting-notes.md` or `PORTING-TOOLSET.md`.

## Legacy reference material

Some older documents remain because they contain useful implementation detail
about the inherited desktop codebase or earlier investigations. They should
not be read as current release claims, ownership claims, project goals, or
validation of the R36S target.

Current project status is defined by the repository root README, the active
branch, current CI, and our own target/device evidence.
