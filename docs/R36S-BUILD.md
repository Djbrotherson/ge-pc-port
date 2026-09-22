# R36S / AArch64 Build

This page documents the current target build path for our branch.

The source of truth is `.github/workflows/build-r36s.yml`. The workflow is
deliberately expensive and should be used to prove a reviewed batch, not as an
edit/compile loop.

## Preflight

Run the cheap checks first:

```sh
python3 tools/n64_port.py doctor
python3 tools/n64_port.py selftest
python3 tools/n64_port.py audit
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
