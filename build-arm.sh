#!/bin/bash
# build-arm.sh - native AArch64 R36S build of ge007.aarch64 in the
# PortMaster builder container (same image hexagotchi uses). No cross
# toolchain, no ROM needed (ROM is only required at runtime/packaging).
#
#   ./build-arm.sh          configure (first time) + build build/arm64
#   ./build-arm.sh clean    remove build/arm64
#
# Run from Git Bash (or any shell with docker on PATH). Needs Docker
# Desktop; --platform linux/arm64 emulation is built in.
#
# Why the wrappers (build/arm64-wrap/): the container default gcc is 9.x,
# which (a) predates the C++20 the project requires and (b) trips the
# project's -Werror=uninitialized on src/game/propobj.c where newer GCCs
# stay quiet. The wrappers point at gcc-10/g++-10 (apt-installed below)
# and append downgrades AFTER the project's own -Werror flags (anything
# passed via CMAKE_C_FLAGS sorts before them and loses). No source changes.
# The build/include symlink satisfies the project's derive-the-toolchain-
# include-dir-from-the-compiler-location trick (see CMakeLists "Host
# <string.h> path"), which would otherwise resolve inside build/.
set -e
cd "$(dirname "$0")"

# Windows-style repo path for docker -v (matches hexagotchi's build-r36s.sh).
REPO_WIN="$(pwd -W 2>/dev/null || pwd)"
REPO_WIN="${REPO_WIN//\\//}"
BUILDER=ghcr.io/monkeyx-net/portmaster-build-templates/portmaster-builder:aarch64-latest

if [ "$1" = "clean" ]; then
  rm -rf build/arm64 build/arm64-wrap
  echo "cleaned arm64"
  exit 0
fi

# Compiler wrappers live next to the build dir so a fresh clone only needs
# this script + docker. Regenerated every run (cheap, idempotent).
mkdir -p build/arm64-wrap
cat > build/arm64-wrap/wrap-gcc <<'EOF'
#!/bin/sh
exec /usr/bin/gcc-10 "$@" -Wno-error=maybe-uninitialized -Wno-error=uninitialized -Wno-error=format-truncation
EOF
cat > build/arm64-wrap/wrap-g++ <<'EOF'
#!/bin/sh
exec /usr/bin/g++-10 "$@" -Wno-error=maybe-uninitialized -Wno-error=uninitialized -Wno-error=format-truncation
EOF

docker run --rm --platform linux/arm64 \
  -v "$REPO_WIN:/workspace" -w /workspace \
  "$BUILDER" \
  bash -c "sed -i 's/\r$//' build/arm64-wrap/wrap-gcc build/arm64-wrap/wrap-g++ \
    && chmod +x build/arm64-wrap/wrap-gcc build/arm64-wrap/wrap-g++ \
    && apt-get update -qq && apt-get install -y -qq libgbm-dev libdrm-dev gcc-10 g++-10 \
    && ln -sfn /usr/include /workspace/build/include \
    && cmake -S . -B build/arm64 -DROMID=ntsc-final \
      -DCMAKE_C_COMPILER=/workspace/build/arm64-wrap/wrap-gcc \
      -DCMAKE_CXX_COMPILER=/workspace/build/arm64-wrap/wrap-g++ \
      -DCMAKE_C_FLAGS=-DUSE_GLES=1 -DCMAKE_CXX_FLAGS=-DUSE_GLES=1 \
    && cmake --build build/arm64 -j\$(nproc) \
    && file build/arm64/ge007.aarch64 && sha256sum build/arm64/ge007.aarch64"
