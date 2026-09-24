# Contributing

Contributions are welcome.

The highest-value work right now is real-device regression testing, spawn/player-position and gameplay correctness, GLES rendering, AArch64/LP64 semantics, controller/audio/runtime compatibility, PortMaster clean-install behavior and documentation.

## Bug reports

Please include:

- device model and firmware/CFW;
- build/source revision;
- mission and difficulty;
- exact reproduction steps;
- `ge007/log.txt` when available;
- whether the issue reproduces after a clean install / regenerated sidecars.

Current verified reference revision:

`c762a153a75ac6eadbef6fa4e4547bf465597ecd`

Reference installer SHA-256:

`738c0c754ffab04911651db14095604aa0cbc5e3f1f2478b3ddf917681381eb9`

## Do not upload game data

Do not attach or commit ROM files (`.z64`, `.n64`, `.v64`), extracted copyrighted game assets, generated `pcmodels.bin`/`pccg.bin` sidecars, or private information.

Code, patches, build logs and minimal diagnostic output are preferred.

## Development rule

Fix bug classes rather than individual symptoms where practical. Strong fixes should leave behind a regression test, assertion, converter/runtime contract, validation step or clear documentation when possible.
