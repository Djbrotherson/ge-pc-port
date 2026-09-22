#include <ultra64.h>
#include "indy_commands.h"
#include "indy_comms.h"

s32 indycommInit(void) {
    if (indy_ready != 1)
    {
        indy_ready = 1;
        indycommHostinit();
    }
#ifdef PORT
    return 0;
#endif
}

void indycomm_removed(void) {
    #ifdef DEBUG
        //removed
    #endif
}

void indycommHostinit(void) {
    if (indy_ready)
    {
        indycmdSendInitPacket();
    }
}

void indycommHostLoadFile(char *filename, u8 *targetloc)
{
    u32 response1;
    u32 response2;
    u32 size;
  
    if (indy_ready)
    {
        indycmdSendLoadFile(filename,0x400000);
        indycmdReceiveFile(&response1, &response2, &size, targetloc);
    }
    return;
}

void indycommHostSendDump(char *filename, u8 *data, u32 size)
{
    u32 response;
  
    if (indy_ready) 
    {
        indycmdSendDump(filename, size, data);
        indycmdAckSendDump(&response);
    }
    return;
}

void indycommHostRamRomLoad(char *filename, u8 *target, s32 size)
{
    u32 uStack4;
    u32 uStack8;
    u32 uStack12;
  
    if (indy_ready)
    {
        indycmdSendRamRomLoad(filename,target,size);
        indycmdReceiveRamRom(&uStack4,&uStack8,&uStack12);
    }
    return;
}

void indycommHostSaveFile(char *filename, s32 size, u8 * data)
{
    u32 response;
  
    if (indy_ready)
    {
        indycmdSendHostExportFile(filename,data,size);
        indycmdAckHostExportFile(&response);
    }
}

u8 * indycommHostCheckFileExists(char *name, s32 *size)
{
    u32 response = 0;
    u32 wire_size = 0;

    if (!indy_ready) {
        return NULL;
    }

    indycmdSendHostCheckFileExists(name);
    indycmdAckHostCheckFileExists(&response, &wire_size);

    if (size != NULL) {
        *size = (s32)wire_size;
    }

    return (u8 *)(uintptr_t)response;
}

u8 *indycommHostSendCmd(u8 *cmdstr)
{
    u32 response = 0;

    if (!indy_ready) {
        return NULL;
    }

    indycmdSendHostCmdPacket(cmdstr);
    indycmdAckHostCmdPacket(&response);

    return (u8 *)(uintptr_t)response;
}

void indycommHost7F0D0124(void) {
    if (indy_ready)
    {
        rmonStatus();
    }
}

void indycommHostCloseConnection(void) {
    indycommHostSendCmd("sleep 5; /etc/killall ghost gload");
}
