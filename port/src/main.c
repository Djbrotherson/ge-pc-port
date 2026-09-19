/*
 * PC entry point for the GoldenEye 007 port.
 *
 * Replaces the N64 boot path (boot.s -> init() -> mainproc() -> bossEntry()).
 * On the PC we:
 *   1. set up system / config / fs / rom
 *   2. load the ROM and map it at the cart base (0x10000000)
 *   3. init video (SDL2 + GL via fast3d), audio, input
 *   4. start the thread kernel and run the game's mainproc() as a real OS
 *      thread (it IS the N64 mainThread) — which runs bossEntry(), the real
 *      game loop. The game's own scheduler (src/sched.c) drives frames; see
 *      docs/internals.md.
 *   5. the host main thread then owns SDL event pumping for the lifetime of
 *      the process (Windows only dispatches window messages to the creating
 *      thread, and every game thread can be blocked on a queue).
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#ifdef PORT
#include <SDL2/SDL.h>
#endif
#if defined(__linux__)
#include <unistd.h>
#include <time.h>
#endif

#include <PR/ultratypes.h>
#include <PR/os.h>

#include "platform.h"
#include "system.h"
#include "config.h"
#include "fs.h"
#include "romdata.h"
#include "dram.h"
#include "video.h"
#include "audio.h"
#include "input.h"
#include "mixer.h"
#include "../include/crash.h"
#include "thread_config.h"

/* Defined in the game (src/init.c). The port calls into the real game entry. */
extern void mainproc(void *args);
extern OSThread mainThread; /* src/init.c:75 */

/* name:number pairs for the 21 solo levels (matches tools_pc/level_sweep.sh
 * and playtest.sh --list). boss.c decodes -level_XX as d0*10 + d1 - 0x210. */
static const struct { const char *name; const char *num; } kSoloLevels[] = {
    {"Dam","33"}, {"Facility","34"}, {"Runway","35"}, {"Surface1","36"},
    {"Bunker1","09"}, {"Silo","20"}, {"Frigate","26"}, {"Surface2","43"},
    {"Bunker2","27"}, {"Statue","22"}, {"Archives","24"}, {"Streets","29"},
    {"Depot","30"}, {"Train","25"}, {"Jungle","37"}, {"Control","23"},
    {"Caverns","39"}, {"Cradle","41"}, {"Aztec","28"}, {"Egypt","32"},
    {"Cuba","54"},
};


#ifdef PORT
/* R36S pre-game level picker.  It deliberately lives before the game's
 * video/input initialization so selecting a mission does not touch game state.
 * No SDL_ttf dependency: a tiny 5x7 font keeps the PortMaster package lean. */
static const unsigned char *portGlyph(char c)
{
    static const unsigned char blank[7]={0,0,0,0,0,0,0};
    static const unsigned char A[7]={14,17,17,31,17,17,17},B[7]={30,17,17,30,17,17,30};
    static const unsigned char C[7]={14,17,16,16,16,17,14},D[7]={30,17,17,17,17,17,30};
    static const unsigned char E[7]={31,16,16,30,16,16,31},F[7]={31,16,16,30,16,16,16};
    static const unsigned char G[7]={14,17,16,23,17,17,15},H[7]={17,17,17,31,17,17,17};
    static const unsigned char I[7]={31,4,4,4,4,4,31},J[7]={7,2,2,2,18,18,12};
    static const unsigned char K[7]={17,18,20,24,20,18,17},L[7]={16,16,16,16,16,16,31};
    static const unsigned char M[7]={17,27,21,21,17,17,17},N[7]={17,25,21,19,17,17,17};
    static const unsigned char O[7]={14,17,17,17,17,17,14},P[7]={30,17,17,30,16,16,16};
    static const unsigned char Q[7]={14,17,17,17,21,18,13},R[7]={30,17,17,30,20,18,17};
    static const unsigned char S[7]={15,16,16,14,1,1,30},T[7]={31,4,4,4,4,4,4};
    static const unsigned char U[7]={17,17,17,17,17,17,14},V[7]={17,17,17,17,17,10,4};
    static const unsigned char W[7]={17,17,17,21,21,21,10},X[7]={17,17,10,4,10,17,17};
    static const unsigned char Y[7]={17,17,10,4,4,4,4},Z[7]={31,1,2,4,8,16,31};
    static const unsigned char n0[7]={14,17,19,21,25,17,14},n1[7]={4,12,4,4,4,4,14};
    static const unsigned char n2[7]={14,17,1,2,4,8,31},n3[7]={30,1,1,14,1,1,30};
    static const unsigned char n4[7]={2,6,10,18,31,2,2},n5[7]={31,16,16,30,1,1,30};
    static const unsigned char n6[7]={14,16,16,30,17,17,14},n7[7]={31,1,2,4,8,8,8};
    static const unsigned char n8[7]={14,17,17,14,17,17,14},n9[7]={14,17,17,15,1,1,14};
    static const unsigned char dash[7]={0,0,0,31,0,0,0};
    switch (c) {
        case 'A': return A; case 'B': return B; case 'C': return C; case 'D': return D;
        case 'E': return E; case 'F': return F; case 'G': return G; case 'H': return H;
        case 'I': return I; case 'J': return J; case 'K': return K; case 'L': return L;
        case 'M': return M; case 'N': return N; case 'O': return O; case 'P': return P;
        case 'Q': return Q; case 'R': return R; case 'S': return S; case 'T': return T;
        case 'U': return U; case 'V': return V; case 'W': return W; case 'X': return X;
        case 'Y': return Y; case 'Z': return Z;
        case '0': return n0; case '1': return n1; case '2': return n2; case '3': return n3;
        case '4': return n4; case '5': return n5; case '6': return n6; case '7': return n7;
        case '8': return n8; case '9': return n9; case '-': return dash;
        default: return blank;
    }
}

static void portDrawText(SDL_Renderer *r, int x, int y, int scale, const char *text)
{
    for (; *text; ++text, x += 6 * scale) {
        char c=*text;
        if (c>='a' && c<='z') c=(char)(c-'a'+'A');
        const unsigned char *g=portGlyph(c);
        for (int row=0; row<7; ++row)
            for (int col=0; col<5; ++col)
                if (g[row] & (1u << (4-col))) {
                    SDL_Rect p={x+col*scale,y+row*scale,scale,scale};
                    SDL_RenderFillRect(r,&p);
                }
    }
}

static int portLevelPicker(void)
{
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER | SDL_INIT_EVENTS) != 0) {
        sysLogPrintf(LOG_WARNING, "level picker: SDL init failed: %s", SDL_GetError());
        return -1;
    }

    SDL_Window *w=SDL_CreateWindow("GoldenEye R36S Level Select",
        SDL_WINDOWPOS_CENTERED,SDL_WINDOWPOS_CENTERED,640,480,SDL_WINDOW_SHOWN);
    SDL_Renderer *r=w ? SDL_CreateRenderer(w,-1,SDL_RENDERER_ACCELERATED|SDL_RENDERER_PRESENTVSYNC) : NULL;
    if (!r && w) r=SDL_CreateRenderer(w,-1,SDL_RENDERER_SOFTWARE);
    if (!w || !r) {
        sysLogPrintf(LOG_WARNING, "level picker: window/renderer failed: %s", SDL_GetError());
        if (r) SDL_DestroyRenderer(r); if (w) SDL_DestroyWindow(w);
        SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER | SDL_INIT_EVENTS);
        return -1;
    }

    SDL_GameController *pad=NULL;
    for (int i=0;i<SDL_NumJoysticks();++i) if (SDL_IsGameController(i)) { pad=SDL_GameControllerOpen(i); break; }

    int sel=0, done=0, result=-1, axisHeld=0;
    const int count=(int)(sizeof(kSoloLevels)/sizeof(kSoloLevels[0]));
    while (!done) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type==SDL_QUIT) { done=1; result=-2; }
            else if (e.type==SDL_KEYDOWN && !e.key.repeat) {
                if (e.key.keysym.sym==SDLK_UP) sel=(sel+count-1)%count;
                else if (e.key.keysym.sym==SDLK_DOWN) sel=(sel+1)%count;
                else if (e.key.keysym.sym==SDLK_RETURN || e.key.keysym.sym==SDLK_SPACE) {result=sel;done=1;}
                else if (e.key.keysym.sym==SDLK_ESCAPE) {result=-1;done=1;}
            } else if (e.type==SDL_CONTROLLERBUTTONDOWN) {
                if (e.cbutton.button==SDL_CONTROLLER_BUTTON_DPAD_UP) sel=(sel+count-1)%count;
                else if (e.cbutton.button==SDL_CONTROLLER_BUTTON_DPAD_DOWN) sel=(sel+1)%count;
                else if (e.cbutton.button==SDL_CONTROLLER_BUTTON_A) {result=sel;done=1;}
                else if (e.cbutton.button==SDL_CONTROLLER_BUTTON_B) {result=-1;done=1;}
            } else if (e.type==SDL_CONTROLLERAXISMOTION && e.caxis.axis==SDL_CONTROLLER_AXIS_LEFTY) {
                if (e.caxis.value < -16000 && axisHeld!= -1) {sel=(sel+count-1)%count;axisHeld=-1;}
                else if (e.caxis.value > 16000 && axisHeld!=1) {sel=(sel+1)%count;axisHeld=1;}
                else if (e.caxis.value > -8000 && e.caxis.value < 8000) axisHeld=0;
            }
        }

        SDL_SetRenderDrawColor(r,8,12,8,255); SDL_RenderClear(r);
        SDL_SetRenderDrawColor(r,220,210,150,255);
        portDrawText(r,28,22,3,"GOLDENEYE LEVEL SELECT");
        SDL_SetRenderDrawColor(r,150,160,150,255);
        portDrawText(r,28,55,2,"DPAD SELECT   A START   B NORMAL BOOT");

        int first=sel-6; if(first<0) first=0; if(first>count-12) first=count-12; if(first<0) first=0;
        int last=first+12; if(last>count) last=count;
        for(int i=first;i<last;++i) {
            int y=92+(i-first)*29;
            if(i==sel) {
                SDL_Rect hi={18,y-5,604,25};
                SDL_SetRenderDrawColor(r,55,90,55,255); SDL_RenderFillRect(r,&hi);
                SDL_SetRenderDrawColor(r,255,255,190,255);
            } else SDL_SetRenderDrawColor(r,195,205,195,255);
            char line[64]; snprintf(line,sizeof(line),"%02d  %s",i+1,kSoloLevels[i].name);
            portDrawText(r,34,y,2,line);
        }
        SDL_RenderPresent(r);
        SDL_Delay(8);
    }

    if (pad) SDL_GameControllerClose(pad);
    SDL_DestroyRenderer(r); SDL_DestroyWindow(w);
    SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER | SDL_INIT_EVENTS);
    return result;
}
#endif


#if defined(__linux__)
static unsigned long long telemetryReadSystemJiffies(void)
{
    FILE *f = fopen("/proc/stat", "r");
    unsigned long long u=0,n=0,sy=0,id=0,iw=0,irq=0,si=0,st=0;
    if (!f) return 0;
    if (fscanf(f, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
               &u,&n,&sy,&id,&iw,&irq,&si,&st) < 4) {
        fclose(f);
        return 0;
    }
    fclose(f);
    return u+n+sy+id+iw+irq+si+st;
}

static unsigned long long telemetryReadProcessJiffies(void)
{
    FILE *f = fopen("/proc/self/stat", "r");
    char buf[4096];
    char *p;
    unsigned long long utime=0, stime=0;
    int field = 3;
    if (!f) return 0;
    if (!fgets(buf, sizeof(buf), f)) { fclose(f); return 0; }
    fclose(f);
    p = strrchr(buf, ')');
    if (!p) return 0;
    p += 2;
    while (*p && field <= 15) {
        char *end = p;
        while (*end && *end != ' ') end++;
        if (field == 14) utime = strtoull(p, NULL, 10);
        if (field == 15) stime = strtoull(p, NULL, 10);
        p = (*end) ? end + 1 : end;
        field++;
    }
    return utime + stime;
}

static long telemetryReadLongFile(const char *path)
{
    FILE *f = fopen(path, "r");
    long v = -1;
    if (f) { if (fscanf(f, "%ld", &v) != 1) v = -1; fclose(f); }
    return v;
}

static void telemetryReadMemory(long *rssKb, long *vmKb, long *threads,
                                long *memTotalKb, long *memAvailKb)
{
    FILE *f;
    char key[64];
    long val;
    char unit[16];
    *rssKb = *vmKb = *threads = *memTotalKb = *memAvailKb = -1;

    f = fopen("/proc/self/status", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            if (sscanf(line, "VmRSS: %ld kB", &val) == 1) *rssKb = val;
            else if (sscanf(line, "VmSize: %ld kB", &val) == 1) *vmKb = val;
            else if (sscanf(line, "Threads: %ld", &val) == 1) *threads = val;
        }
        fclose(f);
    }

    f = fopen("/proc/meminfo", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            if (sscanf(line, "MemTotal: %ld kB", &val) == 1) *memTotalKb = val;
            else if (sscanf(line, "MemAvailable: %ld kB", &val) == 1) *memAvailKb = val;
        }
        fclose(f);
    }
}

static void telemetryTick(void)
{
    static unsigned long long lastSys = 0, lastProc = 0;
    static struct timespec lastTs = {0,0};
    struct timespec now;
    unsigned long long sys, proc, dSys, dProc;
    long rssKb, vmKb, threads, memTotalKb, memAvailKb;
    long tempMilli, freqKhz;
    double dt, procCpu = 0.0, sysBusy = 0.0;

    clock_gettime(CLOCK_MONOTONIC, &now);
    if (lastTs.tv_sec || lastTs.tv_nsec) {
        dt = (double)(now.tv_sec - lastTs.tv_sec) +
             (double)(now.tv_nsec - lastTs.tv_nsec) / 1000000000.0;
        if (dt < 2.0) return;
    }

    sys = telemetryReadSystemJiffies();
    proc = telemetryReadProcessJiffies();
    if (lastSys && lastProc && sys > lastSys) {
        long hz = sysconf(_SC_CLK_TCK);
        dSys = sys - lastSys;
        dProc = proc - lastProc;
        dt = (double)(now.tv_sec - lastTs.tv_sec) +
             (double)(now.tv_nsec - lastTs.tv_nsec) / 1000000000.0;
        if (hz > 0 && dt > 0.0)
            procCpu = 100.0 * ((double)dProc / (double)hz) / dt;
        sysBusy = 100.0 * (double)dProc / (double)dSys;
    }

    telemetryReadMemory(&rssKb, &vmKb, &threads, &memTotalKb, &memAvailKb);
    tempMilli = telemetryReadLongFile("/sys/class/thermal/thermal_zone0/temp");
    freqKhz = telemetryReadLongFile("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq");

    sysLogPrintf(LOG_NOTE,
        "R36S HW cpu_proc=%.1f%% cpu_share=%.1f%% rss=%.1fMB vm=%.1fMB "
        "ram_avail=%.1f/%.1fMB threads=%ld temp=%.1fC cpu0=%.0fMHz",
        procCpu, sysBusy,
        rssKb >= 0 ? rssKb / 1024.0 : -1.0,
        vmKb >= 0 ? vmKb / 1024.0 : -1.0,
        memAvailKb >= 0 ? memAvailKb / 1024.0 : -1.0,
        memTotalKb >= 0 ? memTotalKb / 1024.0 : -1.0,
        threads,
        tempMilli >= 0 ? tempMilli / 1000.0 : -1.0,
        freqKhz >= 0 ? freqKhz / 1000.0 : -1.0);

    lastSys = sys;
    lastProc = proc;
    lastTs = now;
}
#endif

static void portPrintVersion(void)
{
    printf("GoldenEye 007 PC port\n"
           "  rom      : %s\n"
           "  platform : %s\n"
           "  build    : %s (%s)\n"
           "  origin   : %s\n",
           GE007_ROMID, GE007_TARGET_PLATFORM, GE007_VERSION_HASH,
           GE007_VERSION_CODENAME, GE007_ORIGIN_URL);
}

static void portPrintHelp(const char *argv0)
{
    portPrintVersion();
    printf("\nusage: %s [options] [-level_XX]\n\n"
           "  --help            this message\n"
           "  --version         build id only\n"
           "  -fresh            wipe playtest data + config before starting\n"
           "                    (removes ge007.eep save and ge007.ini; the\n"
           "                    ini is re-written with defaults on exit)\n"
           "  -level_XX         boot straight into a solo level (per-level\n"
           "                    memory pools are auto-injected)\n\n"
           "config: ge007.ini in the data dir (written on first run).\n\n"
           "solo levels (-level_XX):\n", argv0 ? argv0 : "ge007");
    for (size_t i = 0; i < sizeof(kSoloLevels) / sizeof(kSoloLevels[0]); ++i) {
        printf("  %-10s -level_%s\n", kSoloLevels[i].name, kSoloLevels[i].num);
    }
}

static void portAtExit(void)
{
    /* Clean-exit only (exit(0) from videoPumpEvents). Crash/fatal paths call
     * abort(), which does not run atexit handlers. */
    videoSaveWindowState();
    configSave();
}

int main(int argc, char **argv)
{
    sysSetArgs(argc, argv);

#ifdef PORT
    /* Unless an explicit direct-level argument was supplied, show a controller
     * friendly pre-game picker. B/Escape preserves the normal front end. */
    {
        int hasLevel=0;
        for (int i=1;i<argc;++i) if (!strncmp(argv[i], "-level_", 7)) { hasLevel=1; break; }
        if (!hasLevel && !getenv("GE_SKIP_LEVEL_PICKER")) {
            int picked=portLevelPicker();
            if (picked == -2) return 0;
            if (picked >= 0) {
                static char levelArg[16];
                char **newv=(char **)calloc((size_t)argc+2,sizeof(char *));
                if (!newv) return 2;
                for (int i=0;i<argc;++i) newv[i]=argv[i];
                snprintf(levelArg,sizeof(levelArg),"-level_%s",kSoloLevels[picked].num);
                newv[argc++]=levelArg;
                newv[argc]=NULL;
                argv=newv;
                sysSetArgs(argc,argv);
                sysLogPrintf(LOG_INFO,"level picker: selected %s (%s)",kSoloLevels[picked].name,levelArg);
            }
        }
    }
#endif

    if (sysArgCheck("--version")) { portPrintVersion(); return 0; }
    if (sysArgCheck("--help") || sysArgCheck("-h")) {
        portPrintHelp(argv[0]);
        return 0;
    }

    sysLogPrintf(LOG_INFO, "GoldenEye 007 PC port starting "
                "(%s, %s %s) -- %s",
                GE007_ROMID, GE007_VERSION_HASH, GE007_VERSION_CODENAME,
                GE007_ORIGIN_URL);

    /* Crash handler first, so any failure below is debuggable. */
    crashInit();

    /* -fresh: clean-slate run -- drop the file-backed EEPROM save and the
     * ini before anything reads them (configLoad below, eeprom's lazy load).
     * sysResolvePath returns one static buffer, so copy each path out. */
    if (sysArgCheck("-fresh") || sysArgCheck("--fresh")) {
        char ini[1024], eep[1024];
        strncpy(ini, sysResolvePath("$S/ge007.ini"), sizeof(ini) - 1);
        ini[sizeof(ini) - 1] = 0;
        strncpy(eep, sysResolvePath("$S/ge007.eep"), sizeof(eep) - 1);
        eep[sizeof(eep) - 1] = 0;
        if (remove(ini) == 0) sysLogPrintf(LOG_INFO, "fresh: removed %s", ini);
        else                  sysLogPrintf(LOG_NOTE, "fresh: no %s to remove", ini);
        if (remove(eep) == 0) sysLogPrintf(LOG_INFO, "fresh: removed %s", eep);
        else                  sysLogPrintf(LOG_NOTE, "fresh: no %s to remove", eep);
    }

    /* 1. Platform + config + filesystem. Steam Deck / SteamOS: seed the
     * first-run preset (native 1280x800 fullscreen, MSAA 4, longer draw/LOD
     * distances) before the load so a missing ini saves these values; an
     * existing ini always wins. */
    if (getenv("STEAMOS")) {
        sysLogPrintf(LOG_INFO, "video: SteamOS detected; applying Steam Deck first-run defaults");
        videoApplySteamOSDefaults();
    }
    configLoad();
    atexit(portAtExit);   /* persist config + window geometry on clean exit */

    /* 1a. D257: Game.AllUnlocked (default OFF; F10 'All unlocked' enables)
     *     -- when set, seed the game's own RAM unlock flags so mission
     *     select offers every solo level at every
     *     difficulty plus 007 mode, with no save data required. Both are
     *     plain s32 globals in src/game/debugmenu_handler.c (compiled because
     *     the PC build defines LEFTOVERDEBUG); file2.c's
     *     fileIsStageUnlockedAtDifficulty() and front.c's 007-mode gate OR
     *     them in ahead of the EEPROM completion bits. Port-layer memory
     *     writes only -- no game-logic edits (AGENTS rule 2), same class as
     *     the existing GE_UNLOCK_ALL getenv hook in the getter. No active
     *     cheats (invincibility / all guns) are enabled; weapons remain
     *     per-mission pickups as on the N64. Separately, the eep shim
     *     (libultra.c geEepromPatchAllCheats) sets every progression-gated
     *     cheat-unlock bit in the save block at read time (per-slot CRC
     *     recomputed via the game's own fileGenerateCRC), so the cheat
     *     menu is fully populated without completed levels. */
    {
        extern s32 portAllUnlocked;            /* port/src/video.c */
        extern s32 debug_enable_all_levels_flag;  /* src/game/debugmenu_handler.c */
        extern s32 debug_007_unlock_flag;         /* ditto */
        if (portAllUnlocked) {
            debug_enable_all_levels_flag = 1;
            debug_007_unlock_flag = 1;
            sysLogPrintf(LOG_INFO, "all-unlocked: RAM unlock flags seeded "
                        "(Game.AllUnlocked=1)");
        }
    }

    /* 2. Load the ROM and map segments. */
    if (romdataInit() != 0) {
        sysLogPrintf(LOG_ERROR, "Failed to load ROM (expected a .z64 in the "
                    "data/ dir, see README)");
        return 1;
    }

    /* 2a. Sanity: the image MUST have loaded at its preferred base.
     *     dram_syms.s absolute symbols are referenced through pointer-typed
     *     externs, which on x86-64/PE become .refptr slots with BASE
     *     relocations. The build disables ASLR (--disable-dynamic-base) so the
     *     loader loads at 0x140000000 and those relocations are no-ops; if we
     *     ever got relocated, every such slot would be silently corrupted.
     *     Fail loudly instead. */
#if defined(PLATFORM_WINDOWS)
    if (sysImageBase() != 0x140000000ul) {
        sysLogPrintf(LOG_ERROR,
            "image loaded at %p, expected preferred base 0x140000000; "
            "absolute DRAM symbols would be corrupted (ASLR must be off)",
            (void *)sysImageBase());
        return 1;
    }
#else
    /* Linux/ELF no-PIE: dram_syms.s absolute symbols resolve to their literal
     * values independent of the image base (no .refptr indirection), so the
     * load address is not constrained. sysImageBase() is a stub here anyway. */
#endif

    /* 2b. Reserve the N64-DRAM region: s32-safe view @ 0x70000000 (cfb_16,
     *     mempools) + KSEG0 mirror @ 0x80000000 (see port/src/dram.c). */
    dramReserve();

    /* 3. Video / audio / input. */
    if (videoInit() != 0) {
        sysLogPrintf(LOG_ERROR, "videoInit failed");
        return 1;
    }
    audioInit();
    mixerInit();
    inputInit();

    /* 4. Run the game. mainproc() runs as the N64 mainThread (a real OS
     *    thread with its own stack); it creates the rmon/idle/scheduler/
     *    audio threads and never returns in practice. */
    sysLogPrintf(LOG_INFO, "ROM mapped at 0x%08X (%u bytes); starting game",
                (unsigned)0x10000000, romdataGetRomSize());
    portKernelInit();
    osCreateThread(&mainThread, MAIN_THREAD_ID, &mainproc, NULL, NULL,
                   MAIN_THREAD_PRIORITY);
    osStartThread(&mainThread);

    /* 5. Host thread: pump SDL events until the window is closed / ESC.
     *    videoPumpEvents() exits the process on quit. */
    for (;;) {
        videoPumpEvents();
#if defined(__linux__)
        telemetryTick();
#endif
        sysSleep(8);
    }

    /* Unreachable in practice; clean up if we ever get here. */
    inputDestroy();
    mixerDestroy();
    audioDestroy();
    videoDestroy();
    romdataDestroy();
    configSave();

    return 0;
}
