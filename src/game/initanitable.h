#ifndef _INITANITABLE_H_
#define _INITANITABLE_H_
#include <ultra64.h>
#include <assets/animationtable_data.h>



/**
 * Struct to hold animation data. This is never instantiated.
 * Instead, only a pointer to this will exist.
 */
struct animation_table_data {
    /**
     * Array length is arbitrary and shouldn't matter. The largest offset
     * into this is for the last animation pointer 0xE7C0, so just choosing
     * a value bigger than that, like u16_max_value.
    */
    u8 data[0xffff];
};

/**
 * Data holder for animations.
 */
extern struct animation_table_data* ptr_animation_table;

/**
 * Contains offsets into ptr_animation_table for player and guard animations.
 * The index of each value corresponds to `enum ANIMATION`.
 * The value corresponds to (e.g. index=0) PTR_ANIM_idle (same as ANIM_DATA_idle)
*/
extern s32 animation_table_ptrs1[];

/**
 * Contains offsets into ptr_animation_table for object/vehicle animations.
 * The index of each value corresponds to `enum AIRCRAFT_ANIMATION`.
 * The value corresponds to (e.g. index=0) PTR_ANIM_helicopter_cradle (same as ANIM_DATA_helicopter_cradle)
 *
 * D32/D33: s32 offsets (N64 layout — 4-byte elements on both targets);
 * cast to ModelAnimation * at the use sites.
*/
extern s32 animation_table_ptrs2[];

#ifdef PORT
/*
 * animation_table_ptrs1/2 keep the original N64 4-byte storage. After
 * expand_ani_table_entries() each non-sentinel element is the low 32 bits of
 * a valid host address in the port's 32-bit-compatible mapping. The arrays
 * remain s32 for source/layout parity, so an ordinary integer->pointer cast
 * would sign-extend values >= 0x80000000 on AArch64. Always zero-extend the
 * token at a native-pointer boundary.
 */
#define ANIM_TABLE_EXPANDED_PTR(token) ((void *)(uintptr_t)(u32)(token))
#else
#define ANIM_TABLE_EXPANDED_PTR(token) ((void *)(token))
#endif

#endif
