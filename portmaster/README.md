# GoldenEye 007 ARM64 — R36S fresh-install extraction test

This test package is built from the current `main` revision.
It does **not** contain a GoldenEye ROM or ROM-derived runtime sidecars.

## Test

1. Install the zip with PortMaster.
2. Put your own US NTSC big-endian GoldenEye 007 ROM at:
   `ge007/data/ge007.ntsc-final.z64`
3. Launch **GoldenEye 007 ARM64 - Fresh Extract Test**.

The package intentionally ships `.force-first-run-extract`. On the first launch
the launcher removes any old `pcmodels-ntsc-final` / `pccg-ntsc-final` trees,
runs the bundled ARM64 `ge007-convert`, verifies both generated `.bin` files,
then verifies that the sidecars were produced by the matching converter schema and starts `ge007.aarch64`.

Everything is recorded in `ge007/log.txt`, including ROM SHA-1, converter
output, generated sidecar sizes, and the game exit code.

Accepted US ROM SHA-1:
`abe01e4aeb033b6c0836819f549c791b26cfde83`
