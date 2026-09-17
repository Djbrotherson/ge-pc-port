# R36S bring-up state

Known-good target path:
- ARM64 ELF
- SDL/GBM/EGL
- OpenGL ES 3.0
- GLES GLAD loader
- GLSL 300 es
- fast3d init and sustained swap loop

Current gameplay bring-up policy:
- keep the proven native GLES path unchanged
- disable GoldenEye game audio temporarily via the existing g_sndBootswitchSound
- seed SFX volume slots because stage-load bookkeeping touches them even when sound boot is disabled
- preserve ROM, sidecar, scheduler, input and full game runtime

The goal of this branch is a playable/no-audio R36S build, not another GPU probe.
