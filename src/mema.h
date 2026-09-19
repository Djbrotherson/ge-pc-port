#ifndef _MEMA_H_
#define _MEMA_H_

#include <ultra64.h>

void memaInit(void);
void memaReset(void *heapaddr, u32 heapsize);
void memaSingleDefragPass(void);
void *memaAlloc(u32 size);
void memaFree(void *addr, s32 size);
void memaDumpPrePostMerge(void);
s32 memaGetLongestFree(void);
#ifdef PORT
s32 memaRealloc(uintptr_t addr, u32 newsize, u32 oldsize);
#else
s32 memaRealloc(s32 addr, u32 newsize, u32 oldsize);
#endif

#endif
