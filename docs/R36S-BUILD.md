# R36S / AArch64 Build

This page documents the current target build path for our branch.

The source of truth is `.github/workflows/build-r36s.yml`. The workflow is
deliberately expensive and should be used to prove a reviewed batch, not as an
edit/compile loop.

## Preflight

Run the cheap checks first:

```sh
python3 tools/n64_port.py gate
```

Do not spend an AArch64 build on a batch that fails Tier 0.

## Target

- Architecture: AArch64
- Graphics: GLES
- ROMID: `ntsc-final`
- Output: `build-pc/ge007.aarch64`
- Toolchain file: `cmake/toolchains/aarch64-linux.cmake`

## Configure

The CI proof uses the equivalent of:

```sh
mkdir -p build-pc

cmake -S . -B build-pc \
  -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux.cmake \
  -DROMID=ntsc-final \
  -DSDL2_INCLUDE_DIR=/usr/include/SDL2 \
  -DSDL2_LIBRARY=/usr/lib/aarch64-linux-gnu/libSDL2.so \
  -DZLIB_INCLUDE_DIR=/usr/include \
  -DZLIB_LIBRARY=/usr/lib/aarch64-linux-gnu/libz.so \
  -DGL_LIBRARY=/usr/lib/aarch64-linux-gnu/libGLESv2.so \
  -DCMAKE_C_FLAGS="-DUSE_GLES=1" \
  -DCMAKE_CXX_FLAGS="-DUSE_GLES=1" \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,-Map=ge007.link.map -Wl,--cref"
```

Hosted CI adds the ARM64 SDL architecture-specific include directory because
Ubuntu's cross-development package layout differs from a native AArch64
machine.

The configure log must contain:

```
Target arch: aarch64 (64bit=TRUE)
Output binary: ge007.aarch64
```

## Build

```sh
cmake --build build-pc -j$(nproc)
```

## Verify the artifact

```sh
file build-pc/ge007.aarch64
aarch64-linux-gnu-readelf -h build-pc/ge007.aarch64
```

The ELF header must report:

```
Machine: AArch64
```

For debugging, CI also emits:

- `ge007.link.map`
- `ge007.symbols.txt`
- `ge007.disasm.txt`
- `ge007.elf-header.txt`

## GitHub Actions policy

Ordinary source/tool pushes use the cheap semantic gate.

The full target build is triggered deliberately after a coherent batch through
the explicit R36S build trigger or workflow dispatch.

This is intentional: GitHub minutes are reserved for proving substantial
progress.

## ROM and assets

The repository does not provide the ROM or copyrighted extracted assets.

The current reference target expects a legally obtained GoldenEye 007
NTSC-U ROM named:

```
data/ge007.ntsc-final.z64
```

Expected SHA-1:

```
abe01e4aeb033b6c0836819f549c791b26cfde83
```

GoldenEye-specific offline converters under `tools_pc/` produce the host
sidecar layouts used by the port.

## R36S validation

A successful cross-build proves target compilation and linkage. It does not
replace real-device verification.

Use the R36S only after Tier 0/1/2 are clean to verify:

- PortMaster launch behavior,
- device GLES/driver behavior,
- gamepad mapping,
- runtime libraries,
- performance/timing,
- interactive gameplay regressions.


## Binary / converter lock

The R36S game binary and ROM-derived sidecars are one ABI unit. The PortMaster
launcher requires converter schema `arm-ge-sidecar-v1` in both generated
sidecar directories. A package must therefore bundle `ge007.aarch64` and a
`ge007-convert` frozen from the same source revision. Stale sidecars are
deleted automatically; a stale converter is rejected instead of launching the
game with incompatible setup/model layouts.

## Local native build (contributor loop)

CI cross-builds; contributors can build natively in a container instead --
same sources, no cross toolchain. From a Windows host with Docker Desktop:

```sh
bash build-arm.sh   # configure + build build/arm64/ge007.aarch64, print sha256
```

The builder image (`ge-builder:noble`: Ubuntu 24.04, GCC 13) is reproducible
from `docker/Dockerfile.noble` and built on demand by the script when absent,
so a fresh machine needs nothing but Docker.

It uses the PortMaster builder image with `gcc-10` (installed on demand)
plus warning-downgrade wrappers, because that image's default GCC 9 trips
`-Werror=maybe-uninitialized` where newer compilers stay quiet. See the
script header.

## Toolchain generation matters on RK3326

Measured 2026-09-22: same source under the PortMaster image's GCC 9/10
produces an 11.2MB binary that runs visibly worse on device than a GCC 13
build (9.6MB -- matching the reference build's size class). Weak CPUs
amplify codegen differences (auto-vectorizer, ARM backend, loop opts) that
are noise on desktop. `-O2`-vs-`-O3` within one compiler is small; jumping
compiler generations is the big lever, LTO on top. Default build type stays
RelWithDebInfo (`-O2`); device glibc is 2.41, so Ubuntu 24.04-baseline
binaries (glibc 2.39) run fine.
