/* Temporary R36S bring-up shim.
 *
 * The native GLES path now gets through video initialization on the R36S.
 * For first-frame validation only, use GoldenEye's existing
 * g_sndBootswitchSound switch so music/SFX initialization is skipped without
 * altering renderer or game timing code.
 *
 * A few stage-load paths still touch the SFX slot-volume arrays even when the
 * boot sound switch is set. Normally sndNewPlayerInit() allocates those arrays;
 * in this diagnostic build that initialization is intentionally skipped, so
 * provide the same default 0x7fff values from static storage to keep those
 * bookkeeping calls valid while all actual sound playback remains disabled.
 *
 * This file exists only on the r36s-first-frame-noaudio diagnostic branch.
 */

#include "system.h"
#include "snd.h"

extern signed char g_sndBootswitchSound;
extern s16 *g_sndSfxSlotNaturalVolume;
extern s16 *g_sndSfxSlotVolume;

#if defined(__aarch64__) && defined(USE_GLES)
static s16 s_r36sNaturalVolume[SFX_SLOT_COUNT];
static s16 s_r36sScaledVolume[SFX_SLOT_COUNT];

__attribute__((constructor))
static void r36sFirstFrameDisableAudio(void)
{
    for (int i = 0; i < SFX_SLOT_COUNT; ++i) {
        s_r36sNaturalVolume[i] = (s16)0x7fff;
        s_r36sScaledVolume[i] = (s16)0x7fff;
    }

    g_sndSfxSlotNaturalVolume = s_r36sNaturalVolume;
    g_sndSfxSlotVolume = s_r36sScaledVolume;
    g_sndBootswitchSound = 1;

    sysLogPrintf(LOG_NOTE,
                 "R36S first-frame diagnostic: game audio disabled; "
                 "SFX volume slots seeded");
}
#endif
