# ARM-GE Port Control Overlay

Status: **active Dam-lab UI replacement**.

The old single-column F10 list has been replaced on `dam-only-lab` with the
ARM-GE Port Control overlay. The interaction design takes cues from modern
source-port/recomp settings surfaces: categorical pages, controller-first
navigation, mouse/keyboard parity, live settings, and a persistent performance
footer. It intentionally does not copy another project's styling.

## Controls

Existing bindings are preserved:

- `F10` toggles the overlay,
- arrows/D-pad move and change values,
- Enter/A/X advances a value,
- B/Y/Left decrements,
- Start closes,
- mouse click/drag/wheel remains supported.

Added navigation:

- L/R shoulder switches category,
- Q/E or PageUp/PageDown switches category,
- clicking a tab switches category.

## Pages

### Graphics

Fullscreen, resolution, VSync, frame cap, FPS display, MSAA, texture filter,
anisotropy, mip fix, texture-wrap fix, FOV scale, automatic/manual draw
distance and automatic/manual LOD distance.

### Audio

Mute, live master volume, queue-limit tuning and SDL device-buffer size.
Device-buffer size is marked restart-required; master volume and mute are
applied directly to the PCM stream before it reaches SDL.

### Input

Mouse enable/absolute aim, aim/turn sensitivity and linking, invert Y,
smoothing, raw input, natural pitch, controller deadzone, trigger threshold
and controller Y inversion.

### Gameplay

Port-side behavior toggles currently proven safe enough to expose.

### System

Diagnostics intended for development builds. The Dam lab keeps its separate
hardware telemetry HUD; this page is for persistent port controls.

## Visual system

The new overlay uses a full-screen translucent shell, a fixed title strip,
five category tabs, separated row cards, a bright selection rail, compact
sliders, cyan/green live-state accents and a persistent footer. This is
deliberately visually distinct from the original GoldenEye watch UI and from
the previous PC overlay.

## Design rule

A setting is only exposed when the port has a real implementation behind it.
The UI must never create a placebo toggle. New renderer/audio enhancements
should land as runtime capability first and overlay control second.
