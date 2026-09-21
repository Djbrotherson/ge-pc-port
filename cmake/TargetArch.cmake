# Determine the target architecture and set TARGET_ARCH / TARGET_IS_64BIT.
# Modelled on the Perfect Dark PC port's cmake/TargetArch.cmake.

function(target_architecture OUT_VAR)
  if(CMAKE_CROSSCOMPILING)
    # CMAKE_C_COMPILER_TARGET is populated reliably by Clang but is often
    # empty for GCC cross compilers such as aarch64-linux-gnu-gcc. Prefer it
    # when present, then fall back to the toolchain's CMAKE_SYSTEM_PROCESSOR.
    string(REGEX MATCH "^(i[3-6]86|x86_64|aarch64|arm|powerpc|wasm32)" _arch
           "${CMAKE_C_COMPILER_TARGET}")
    if(NOT _arch)
      string(REGEX MATCH "^(i[3-6]86|x86_64|aarch64|arm64|arm|powerpc|wasm32)" _arch
             "${CMAKE_SYSTEM_PROCESSOR}")
      if(_arch STREQUAL "arm64")
        set(_arch "aarch64")
      endif()
    endif()
  else()
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
      set(_arch "x86_64")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(i[3-6]86|x86)$")
      set(_arch "i686")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
      set(_arch "aarch64")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm)$")
      set(_arch "arm")
    else()
      set(_arch "${CMAKE_SYSTEM_PROCESSOR}")
    endif()
  endif()

  if(_arch STREQUAL "i386")
    set(_arch "i686")
  endif()

  set(${OUT_VAR} "${_arch}" PARENT_SCOPE)
endfunction()
