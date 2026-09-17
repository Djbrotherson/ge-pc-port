/* Temporary R36S bring-up shim.
 *
 * The native GLES path now gets through video initialization on the R36S,
 * while the current ARM64 build faults later during GoldenEye's libaudio
 * startup.  For first-frame validation only, use the game's existing
 * g_sndBootswitchSound switch so music/SFX initialization is skipped without
 * altering renderer or game timing code.
 *
 * This file exists only on the r36s-first-frame-noaudio diagnostic branch.
 */

#include "system.h"

extern signed char g_sndBootswitchSound;

#if defined(__aarch64__) && defined(USE_GLES)
__attribute__((constructor))
static void r36sFirstFrameDisableAudio(void)
{
    g_sndBootswitchSound = 1;
    sysLogPrintf(LOG_NOTE,
                 "R36S first-frame diagnostic: GoldenEye game audio disabled");
}
#endif
