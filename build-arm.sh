#!/bin/bash
# build-arm.sh - incremental ARM64 R36S build of work/goldeneye-pc-port.
# Output goes to build/arm64 (out-of-source).
#
#   ./build-arm.sh                                   build work/ (incremental)
#   SRC=reference/goldeneye-pc-port BUILD=build/reference ./build-arm.sh
#                                                    build untouched upstream
#   ./build-arm.sh clean                             remove build dir
set -e
cd "$(dirname "$0")"

SRC_DIR="${SRC:-work/goldeneye-pc-port}"
BUILD_DIR="${BUILD:-build/arm64}"

DEV_WIN="$(pwd -W 2>/dev/null || pwd)"
DEV_WIN="${DEV_WIN//\\//}"
BUILDER=ge-builder:noble

if [ "$1" = "clean" ]; then
  rm -rf "$BUILD_DIR"
  echo "cleaned $BUILD_DIR"
  exit 0
fi

docker run --rm --platform linux/arm64 \
  -v "$DEV_WIN:/workspace" -w /workspace \
  "$BUILDER" \
  bash -c "cmake -S /workspace/$SRC_DIR -B /workspace/$BUILD_DIR -DROMID=ntsc-final -DCMAKE_C_FLAGS=-DUSE_GLES=1 -DCMAKE_CXX_FLAGS=-DUSE_GLES=1 \
    && cmake --build /workspace/$BUILD_DIR -j\$(nproc) \
    && gcc -O2 -Wall /workspace/watch/ge007-watch.c \$(pkg-config --cflags --libs sdl2) -o /workspace/$BUILD_DIR/ge007-watch \
    && ls -la /workspace/$BUILD_DIR/ge007.aarch64 /workspace/$BUILD_DIR/ge007-watch \
    && sha256sum /workspace/$BUILD_DIR/ge007.aarch64"
