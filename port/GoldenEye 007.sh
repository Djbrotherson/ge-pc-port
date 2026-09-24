#!/bin/bash
# 007-r36s PortMaster launcher.
# Concept: standard PortMaster control.txt setup + first-boot sidecar
# extraction from the user's own ROM, then launch. Our own script.
#
# Layout under /roms/ports:
#   GoldenEye 007.sh        this file (ES entry point)
#   ge007/                  game directory (GAMEDIR)
#     ge007.aarch64         engine binary
#     ge007-watch           Select+Start exit watcher
#     prepare-assets/       converter bundle (ge007-convert wrapper + scripts)
#     data/                 user ROM + generated sidecars (never shipped)
#     conf/                 XDG config home (ini, saves)
#     log.txt               last session log

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
CONVERTER="$GAMEDIR/prepare-assets/ge007-convert"
GAME="$GAMEDIR/ge007.aarch64"
WATCH="$GAMEDIR/ge007-watch"

mkdir -p "$CONFDIR" "$GAMEDIR/data"
cd "$GAMEDIR" || exit 1

> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

export XDG_DATA_HOME="$CONFDIR"

echo "=== GoldenEye 007 (007-r36s clean tree) ==="
date
echo "GAMEDIR=$GAMEDIR CFW=${CFW_NAME:-unknown}"

chmod +x "$GAME" "$WATCH" "$CONVERTER" 2>/dev/null || true

if [ ! -f "$ROM" ]; then
  echo "[ROM] MISSING: $ROM"
  echo "Put your US NTSC big-endian GoldenEye ROM at ge007/data/ge007.ntsc-final.z64 and launch again."
  type pm_message >/dev/null 2>&1 && pm_message "GoldenEye ROM missing: ge007/data/ge007.ntsc-final.z64"
  type pm_finish >/dev/null 2>&1 && pm_finish
  exit 2
fi

if command -v sha1sum >/dev/null 2>&1; then
  sha1sum "$ROM"
fi

if [ ! -f "$GAMEDIR/data/pcmodels-ntsc-final/pcmodels.bin" ] || \
   [ ! -f "$GAMEDIR/data/pccg-ntsc-final/pccg.bin" ]; then
  echo "[Extract] sidecars missing: running bundled converter"
  "$CONVERTER" --rom "$ROM" --out "$GAMEDIR"
  CONVERT_RC=$?
  echo "[Extract] converter rc=$CONVERT_RC"
fi

if [ ! -f "$GAMEDIR/data/pcmodels-ntsc-final/pcmodels.bin" ] || \
   [ ! -f "$GAMEDIR/data/pccg-ntsc-final/pccg.bin" ]; then
  echo "[Extract] FAILED: sidecars still missing after converter run"
  type pm_finish >/dev/null 2>&1 && pm_finish
  exit 3
fi
echo "[Extract] PASS"

echo "[Launch] starting ge007.aarch64"
"$GAME" &
GAME_PID=$!
# Select+Start watcher: SIGTERMs the game to return to ES.
"$WATCH" "$GAME_PID" &
WATCH_PID=$!
wait "$GAME_PID"
GAME_RC=$?
kill "$WATCH_PID" 2>/dev/null || true
echo "[Exit] rc=$GAME_RC"

type pm_finish >/dev/null 2>&1 && pm_finish
exit "$GAME_RC"
