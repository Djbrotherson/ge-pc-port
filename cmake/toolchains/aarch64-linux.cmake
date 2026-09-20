set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_ASM_COMPILER aarch64-linux-gnu-gcc)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# Ubuntu multiarch target headers/libraries live under the AArch64 triplet.
# Programs remain host-native while CMake resolves libraries/packages for the
# R36S-compatible AArch64 Linux target.
set(CMAKE_FIND_ROOT_PATH
    /usr/aarch64-linux-gnu
    /usr
)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
