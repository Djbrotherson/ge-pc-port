#!/bin/bash
# build-arm.sh - native AArch64 R36S build of ge007.aarch64 in a container.
# No cross toolchain, no ROM needed (ROM is only required at
# runtime/packaging).
#
#   ./build-arm.sh          configure (first time) + build build/arm64
#   ./build-arm.sh clean    remove build/arm64
#
# Run from Git Bash (or any shell with docker on PATH). Needs Docker
# Desktop; --platform linux/arm64 emulation is built in.
#
# Builds with ge-builder:noble (Ubuntu 24.04, GCC 13). Matches upstream
# CI's compiler generation.
set -e
cd "$(dirname "$0")"

# Windows-style repo path for docker -v (matches hexagotchi's build-r36s.sh).
REPO_WIN="$(pwd -W 2>/dev/null || pwd)"
REPO_WIN="${REPO_WIN//\\//}"
BUILDER=ge-builder:noble

if [ "$1" = "clean" ]; then
  rm -rf build/arm64
  echo "cleaned arm64"
  exit 0
fi

# The builder image is reproducible from docker/Dockerfile.noble and built
# on demand here. Requires a working `docker` CLI plus an engine that can
# run linux/arm64 containers (Docker Desktop covers Windows; on Linux,
# docker-ce + qemu-user-static does).
if ! docker images -q "$BUILDER" 2>/dev/null | grep -q .; then
  echo "builder image $BUILDER missing -- building it (one-time, ~10 min)..."
  docker build -t "$BUILDER" -f docker/Dockerfile.noble docker/ || exit 1
fi

docker run --rm --platform linux/arm64 \
  -v "$REPO_WIN:/workspace" -w /workspace \
  "$BUILDER" \
  bash -c "apt-get update -qq && apt-get install -y -qq libgbm-dev libdrm-dev \
    && cmake -S . -B build/arm64 -DROMID=ntsc-final \
      -DCMAKE_C_FLAGS=-DUSE_GLES=1 -DCMAKE_CXX_FLAGS=-DUSE_GLES=1 \
    && cmake --build build/arm64 -j\$(nproc) \
    && ls -la build/arm64/ge007.aarch64 && sha256sum build/arm64/ge007.aarch64"
