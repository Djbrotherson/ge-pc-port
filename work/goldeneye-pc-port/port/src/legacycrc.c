/*
 * port/src/legacycrc.c — D297: one-time migration of pre-D284 save-slot CRCs.
 *
 * WHY A DELIBERATELY-WRONG PRNG LIVES IN THIS TREE (read before "fixing" it):
 *
 *   v0.2.x shipped with a port-side bug in randomGetNextFrom's dsll32/dsrl32
 *   semantics (modelled as 32-bit shifts; real MIPS64 shifts by n+32 over the
 *   full register). D284 (commit 0de99b4d) fixed it. But fileGenerateCRC
 *   (src/game/crc.c) runs that PRNG off a LOCAL constant seed, so every slot
 *   checksum stored on disk is a fingerprint of the PRNG implementation that
 *   wrote it: saves written by v0.2.x validate under the OLD stream and fail
 *   the NEW one, and fileValidateSaves wipes failing slots (D295/M-148, D297).
 *
 *   This file carries the pre-D284 transform so the eeprom shim can recognize
 *   a legacy save (old-CRC match) and re-stamp its two checksum words with the
 *   current-PRNG values before the game validates. No game files are touched;
 *   the new CRCs come from the game's own fileGenerateCRC — only the OLD PRNG
 *   is duplicated here, and it must stay bit-exact-WRONG. Do not "fix" the
 *   shifts below; do not share helpers with port/src/random.c.
 *
 *   When this can be deleted: once no pre-D284 saves are expected in the wild
 *   (the v0.3.0 release is the last build that meets them un-migrated). Keep
 *   it at least until then; the cost is ~60 lines of dead-but-harmless code.
 *
 * Verification: the legacy stream below was re-derived from
 * `git show 0de99b4d^:port/src/random.c` and matches tools_pc/d295_crc.py,
 * which is bit-exact against compiled C for both PRNGs (see D295 M-148).
 */

#include <ultra64.h>
#include "file.h" /* save_data */

extern void fileGenerateCRC(u8 *addressA, u8 *addressB, save_data *retval);

/* Pre-D284 randomGetNextFrom: verbatim body from 0de99b4d^:port/src/random.c
 * with the OLD helper semantics inlined ((x << n) & 0xFFFFFFFF etc.). */
static u32 geLegacyRandomGetNextFrom(u64 *seed)
{
    u64 a3 = *seed;
    u64 a1, a2;

    a2 = (a3 << 0x1f) & 0xFFFFFFFFULL; /* dsll32, pre-D284 semantics */
    a1 = a3 << 0x1f;                   /* dsll */
    a2 = a2 >> 0x1f;                   /* dsrl */
    a1 = (a1 >> 0) & 0xFFFFFFFFULL;    /* dsrl32, pre-D284 semantics */
    a3 = (a3 << 0xc) & 0xFFFFFFFFULL;  /* dsll32, pre-D284 semantics */
    a2 = a2 | a1;
    a3 = (a3 >> 0) & 0xFFFFFFFFULL;    /* dsrl32, pre-D284 semantics */
    a2 = a2 ^ a3;
    a3 = a2 >> 0x14;                   /* dsrl */
    a3 = a3 & 0xfff;
    a3 = a3 ^ a2;

    *seed = a3;
    return (u32)a3;
}

/* Same loop as fileGenerateCRC (src/game/crc.c) stepping the legacy PRNG.
 * Keep in lockstep with crc.c if that loop ever changes. */
static void geLegacyGenerateCRC(u8 *addressA, u8 *addressB, save_data *retval)
{
    u8 *byte;
    s32 shift      = 0;
    s64 polynormal = 0x8F809F473108B3C1; /* same local constant seed as crc.c */
    s32 checksum1  = 0;
    s32 checksum2  = 0;

    for (byte = addressA; byte < addressB; byte++, shift += 7) {
        polynormal += *byte << (shift & 0xF);
        checksum1 ^= geLegacyRandomGetNextFrom(&polynormal);
    }
    for (byte = addressB - 1; byte >= addressA; byte--, shift += 3) {
        polynormal += *byte << (shift & 0xF);
        checksum2 ^= geLegacyRandomGetNextFrom(&polynormal);
    }
    retval->chksum1 = checksum1;
    retval->chksum2 = checksum2;
}

/* Migrate up to five consecutive 96-byte save slots in place. A slot is
 * migrated iff it FAILS the current-PRNG check but PASSES the legacy one;
 * re-stamped via the game's own fileGenerateCRC. Corrupt slots (fail both)
 * are left alone for the game's own wipe path. Returns the count migrated. */
int geLegacyCrcMaybeMigrateSlots(u8 *slots5)
{
    save_data *slots = (save_data *)slots5;
    int migrated = 0;

    for (int i = 0; i < 5; i++) {
        save_data calc = {0}; /* only chksum1/chksum2 are read back */
        u8 *a = &slots[i].completion_bitflags; /* slot bytes [8..96) */
        u8 *b = (u8 *)&slots[i + 1];           /* end boundary, never dereferenced */

        fileGenerateCRC(a, b, &calc);
        if (calc.chksum1 == slots[i].chksum1 && calc.chksum2 == slots[i].chksum2)
            continue; /* current-PRNG save (or already migrated) — idempotent no-op */

        geLegacyGenerateCRC(a, b, &calc);
        if (calc.chksum1 != slots[i].chksum1 || calc.chksum2 != slots[i].chksum2)
            continue; /* corrupt: game's fileValidateSaves handles it */

        fileGenerateCRC(a, b, &slots[i]); /* re-stamp chksum1/chksum2 in place */
        migrated++;
    }
    return migrated;
}
