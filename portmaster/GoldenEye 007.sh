#!/bin/bash

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

source "$controlfolder/control.txt"
[ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"
get_controls

GAMEDIR="/$directory/ports/ge007"
CONFDIR="$GAMEDIR/conf"
ROM="$GAMEDIR/data/ge007.ntsc-final.z64"
MARKER="$GAMEDIR/.force-first-run-extract"
CONVERTER="$GAMEDIR/prepare-assets/ge007-convert"
GAME="$GAMEDIR/ge007.aarch64"
SIDECAR_SCHEMA="arm-ge-sidecar-v1"
PCMODEL_SCHEMA="$GAMEDIR/data/pcmodels-ntsc-final/.converter-schema"
PCCG_SCHEMA="$GAMEDIR/data/pccg-ntsc-final/.converter-schema"

mkdir -p "$CONFDIR" "$GAMEDIR/data"
cd "$GAMEDIR" || exit 1

> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

export XDG_DATA_HOME="$CONFDIR"

echo "=== GoldenEye 007 R36S fresh-install test ==="
date
echo "directory=$directory"
echo "GAMEDIR=$GAMEDIR"
echo "ARCH=${DEVICE_ARCH:-${ARCH:-unknown}}"
echo "CFW=${CFW_NAME:-${CFW:-unknown}}"
echo "param_device=${param_device:-unset}"
echo "controlfolder=$controlfolder"
echo "SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-unset}"
echo "SDL_AUDIODRIVER=${SDL_AUDIODRIVER:-unset}"

echo "[Build]"
cat "$GAMEDIR/build-info.txt" 2>/dev/null || true
file "$GAME" 2>/dev/null || true
ls -lh "$GAME" "$CONVERTER" 2>/dev/null || true

chmod +x "$GAME" "$CONVERTER" 2>/dev/null || true

# Convenience: accept the names used by our earlier test folders, but always
# stage the runtime ROM at the canonical path expected by the engine.
if [ ! -f "$ROM" ]; then
  for cand in \
    "$GAMEDIR/baserom.u.z64" \
    "$GAMEDIR/ge007.ntsc-final.z64" \
    "$GAMEDIR/b.z64" \
    "$GAMEDIR/data/baserom.u.z64" \
    "$GAMEDIR/data/b.z64"; do
    if [ -f "$cand" ]; then
      echo "[ROM] staging $(basename "$cand") -> data/ge007.ntsc-final.z64"
      cp -f "$cand" "$ROM"
      break
    fi
  done
fi

if [ ! -f "$ROM" ]; then
  echo "[ROM] MISSING: $ROM"
  echo "Put the US NTSC big-endian GoldenEye ROM at ge007/data/ge007.ntsc-final.z64 and launch again."
  if type pm_message >/dev/null 2>&1; then
    pm_message "GoldenEye ROM missing. Put the US NTSC .z64 at ge007/data/ge007.ntsc-final.z64"
  fi
  type pm_finish >/dev/null 2>&1 && pm_finish
  exit 2
fi

echo "[ROM]"
ls -lh "$ROM"
if command -v sha1sum >/dev/null 2>&1; then
  sha1sum "$ROM"
fi

# This marker is shipped in the test package. It guarantees the first launch
# really exercises clean extraction even when PortMaster installs over an old
# ge007 directory instead of deleting it first.
if [ -f "$MARKER" ]; then
  echo "[Extract] fresh-install marker present: removing old sidecars"
  rm -rf "$GAMEDIR/data/pcmodels-ntsc-final" "$GAMEDIR/data/pccg-ntsc-final"
fi

PCMODEL_HAVE="$(cat "$PCMODEL_SCHEMA" 2>/dev/null || true)"
PCCG_HAVE="$(cat "$PCCG_SCHEMA" 2>/dev/null || true)"
if [ -d "$GAMEDIR/data/pcmodels-ntsc-final" ] || [ -d "$GAMEDIR/data/pccg-ntsc-final" ]; then
  if [ "$PCMODEL_HAVE" != "$SIDECAR_SCHEMA" ] || [ "$PCCG_HAVE" != "$SIDECAR_SCHEMA" ]; then
    echo "[Extract] sidecar schema mismatch: expected=$SIDECAR_SCHEMA pcmodels=${PCMODEL_HAVE:-missing} pccg=${PCCG_HAVE:-missing}"
    echo "[Extract] removing stale sidecars before regeneration"
    rm -rf "$GAMEDIR/data/pcmodels-ntsc-final" "$GAMEDIR/data/pccg-ntsc-final"
  fi
fi

if [ ! -f "$GAMEDIR/data/pcmodels-ntsc-final/pcmodels.bin" ] || \
   [ ! -f "$GAMEDIR/data/pccg-ntsc-final/pccg.bin" ]; then
  echo "[Extract] sidecars missing: starting bundled ARM64 converter"
  "$CONVERTER" --rom "$ROM" --out "$GAMEDIR"
  CONVERT_RC=$?
  echo "[Extract] converter rc=$CONVERT_RC"
  if [ "$CONVERT_RC" -ne 0 ]; then
    echo "[Extract] FAILED"
    type pm_finish >/dev/null 2>&1 && pm_finish
    exit "$CONVERT_RC"
  fi
fi

if [ ! -f "$GAMEDIR/data/pcmodels-ntsc-final/pcmodels.bin" ] || \
   [ ! -f "$GAMEDIR/data/pccg-ntsc-final/pccg.bin" ]; then
  echo "[Extract] FAILED: converter returned but required sidecars are missing"
  find "$GAMEDIR/data" -maxdepth 2 -type f -printf '%p %s bytes\n' 2>/dev/null | sort || true
  type pm_finish >/dev/null 2>&1 && pm_finish
  exit 3
fi

PCMODEL_HAVE="$(cat "$PCMODEL_SCHEMA" 2>/dev/null || true)"
PCCG_HAVE="$(cat "$PCCG_SCHEMA" 2>/dev/null || true)"
if [ "$PCMODEL_HAVE" != "$SIDECAR_SCHEMA" ] || [ "$PCCG_HAVE" != "$SIDECAR_SCHEMA" ]; then
  echo "[Extract] FAILED: converter/schema mismatch"
  echo "[Extract] expected=$SIDECAR_SCHEMA pcmodels=${PCMODEL_HAVE:-missing} pccg=${PCCG_HAVE:-missing}"
  echo "[Extract] Rebuild/bundle ge007-convert from this same source revision."
  type pm_finish >/dev/null 2>&1 && pm_finish
  exit 4
fi

rm -f "$MARKER"

echo "[Extract] PASS"
ls -lh "$GAMEDIR/data/pcmodels-ntsc-final/pcmodels.bin" \
       "$GAMEDIR/data/pccg-ntsc-final/pccg.bin"
wc -l "$GAMEDIR/data/pcmodels-ntsc-final/manifest.csv" \
      "$GAMEDIR/data/pccg-ntsc-final/manifest.csv" 2>/dev/null || true

echo "[Launch] starting ge007.aarch64"
"$GAME"
GAME_RC=$?
echo "[Exit] ge007.aarch64 rc=$GAME_RC"

type pm_finish >/dev/null 2>&1 && pm_finish
exit "$GAME_RC"
