#include <PR/os_internal.h>
#include <PR/rcp.h>
#include <os/osint.h>

/**
 * It is worth noting that a previous hardware bug has been fixed by a software
 * patch in osAiSetNextBuffer. This bug occurred when the address of the end of the
 * buffer specified by osAiSetNextBuffer was at a specific value. This value
 * occurred when the following was true:
 *
 *     (vaddr + nbytes) & 0x00003FFF == 0x00002000
 *
 * (when the buffer ends with address of lower 14 bits 0x2000) In this case, the
 * DMA transfer does not complete successfully. This can cause clicks and pops in
 * the audio output. This bug no longer requires special handling by the application
 * because it is now patched by osAiSetNextBuffer.
 */
s32 osAiSetNextBuffer(void *bufPtr, u32 size)
{
	static u8 hdwrBugFlag = 0;
	char *bptr = bufPtr;
	if (hdwrBugFlag != 0)
		bptr -= 0x2000;

#ifdef PORT
	if ((((uintptr_t)bufPtr + size) & 0x3fffu) == 0x2000u)
#else
	if ((((u32)bufPtr + size) & 0x3fff) == 0x2000)
#endif
		hdwrBugFlag = 1;
	else
		hdwrBugFlag = 0;

	if (__osAiDeviceBusy())
		return -1;

	IO_WRITE(AI_DRAM_ADDR_REG, osVirtualToPhysical(bptr));
	IO_WRITE(AI_LEN_REG, size);
	return 0;
}
