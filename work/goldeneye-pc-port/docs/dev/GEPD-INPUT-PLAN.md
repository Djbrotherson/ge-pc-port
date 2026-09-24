# GEPD-inspired input overhaul — FINAL PLAN (issues #89, #90)

Status: **plan only** — no code changes yet. Companion to `port/src/input.c`
(current state: D118/D165/D166/D194/D214/D223/D238 lineage).

## 1. The reference (no longer vendored in the public repo)

The GEPD Edition Mouse Injector source was vendored at `reference/mouse-injector/`
and **removed from the public repo on 2026-09-19** (GPLv2 code + a prebuilt
binary inside an MIT project; never compiled here). See
`reference/mouse-injector/README.md` for provenance and how to re-vendor it
locally if you need the original. The file that mattered was
**`games/goldeneye.c`** (~380 lines, the whole GE aim model), plus `device.c`
(raw mouse polling) and `maindll.h` (tickrate — the units every per-tick
constant assumes). The model is quoted inline below and in the D194 findings;
the ported result lives in `port/src/input.c`.

### What the Mouse Injector does (GE)

### What the Mouse Injector actually does (GE)

| Aspect | GEPD implementation (`games/goldeneye.c`) |
|---|---|
| Mouse source | Raw driver deltas via ManyMouse (`device.c`), cursor locked by periodic `SetCursorPos`. No OS pointer accel, no deadzone. |
| **Hipfire look** | **Direct camera write**: `camx += XPOS/10 * (SENS/40) * (fov/basefov)` degrees per tick; `camy` likewise, clamped ±90 (−20 in tank). Linear in px — this is why GEPD "just feels right". |
| **Aim mode (R)** | Crosshair *position* accumulator `crosshairpos += XPOS/10 * SENS/292`, clamped to ±`CROSSHAIRLIMIT` (5.159° = screen edge). Gun/arm pose derived per-weapon from a 33-entry offset table. **View scrolls only past 72% of the way to the edge**: `aimx = (ratio−0.72) * 475 * timestep`, scaled by `fov/basefov`. |
| FOV coupling | Every term carries `(fov/basefov)` — scopes automatically get finer control. `basefov` = min(60, override). |
| Tank | Separate direct write to the tank x-rotation global (`0x80036484`), different scale (`360/TANKXROT * 2.5`); crosshair X locked to 0 when driving with tank equipped. |
| Menus | Mouse moves the menu cursor directly (`menux/y += px/10*SENS*6`, clamped to screen rect); aim button acts as B (back) in menus; wheel = weapon cycle macro. |
| Safety gates | Injection only when `camera==4||0 && menupage==11 && !dead && !watch && !pause && !mproundend`. |
| Extras | Crouch *toggle* mode, dedicated reload key (ROM hack — not portable to us), FOV override + viewmodel repositioning (ROM hacks — we have the clean equivalents in `port/`), intro skip on FIRE+AIM. |

### Already inherited (do not redo)

- **D194 GEPD-mirror aim** (`aimGepdCompute()`): crosshair-position model,
  ±5.159° clamp, 72% edge scroll at 475/s, fov scaling, per-tick overwrite of
  `crosshair_x/y_pos` + `gun_azimuth_angle/turning`. This *is* GEPD's aim mode.
- D223 mouse-wheel weapon cycling (A / A+Z synthesis) — mirrors
  `GE_Controller()`'s weapon macro; D214 ini key binds; click-to-lock capture;
  F10 options overlay with aim/turn sensitivity sliders; D194(b) dt-decoupled
  look; menu pointer via direct `cursor_h/v_pos` writes (mirrors GEPD's
  `menux/y` writes).

### Remaining inheritances (this plan)

GEPD's *hipfire* is a direct linear camera write — we still route hipfire
through the N64 stick curve (#89). Also un-inherited: raw-input-by-default,
crouch toggle, GEPD-style safety gates on our always-live look paths, and its
sensitivity/FOV coupling discipline. That's WIs 1–3 + 6 below.

### Reference split (GEPD vs PD port)

Two references, two jobs (decided during #89/#90 triage):

- **GEPD Mouse Injector** (was `reference/mouse-injector/`, removed from the
  public repo 2026-09-19 — see its README stub) = *what the mouse does to the
  camera*. The only reference with GE-specific knowledge (camera fields,
  crosshair limits, tank case, safety gates). Primary for WI-1.
- **PD PC port checkout** (standing reference, see AGENTS.md) = *how a PC game
  presents and captures input*: cursor-lock behavior, raw input handling,
  sensitivity units/scaling, and the shipped in-game options/keybind UI.
  Primary for WI-2 conventions and WI-5's menu design. PD knows nothing about
  GE — never use it for camera math.

## 2. Issue #89 — "mouse movement is not uniform; slow motion barely registers"

### Diagnosis (high confidence)

The complaint is the **hipfire** path. Today hipfire converts mouse px into an
*analog stick value* (`sx += (int)(hipEdx * hipSens * MOUSE_TURN_GAIN)`), and
the game then runs that stick through its own N64-era natural-turn response —
a **quadratic-ish curve with a soft floor** (D238: "saturates the game's
quadratic natural-turn curve at ~13 px/poll"). Consequences, exactly as the
reporter describes:

1. Slow mouse motion → small stick values → squared-off tiny turn rates →
   "almost unrecognised".
2. Fast motion saturates the curve at full 315°/s — so the usable band is
   narrow and the feel is non-uniform (bang-bang-ish).
3. `(int)` truncation of the stick adds a quantized dead zone on top.

GEPD/PD-PC never hit this because **they write the camera angles directly** —
the stick curve is bypassed entirely, and sensitivity is linear in px with
FOV scaling. We already do exactly that in aim mode (D194); hipfire is the one
leftover N64-stick-shaped path.

Secondary contributors worth folding in:

- `Input.MouseRawInput` defaults to **0** — on X11/Wayland (the #90 reporter
  is on Linux) OS pointer acceleration still shapes relative deltas; GEPD
  reads the raw driver. Windows is largely unaffected.
- Sensitivity is spread over 4 knobs (`MouseSensitivity`, `MouseTurnSpeed`,
  `AimModeSens`, legacy `MouseAimSpeed`) — the reporter "tried adjusting
  ge007.ini" and couldn't find the one that mattered for hipfire.

### Work items

**WI-1 (core fix): direct camera writes for hipfire look.**
Mirror GEPD's hipfire branch in `input.c`.

*Pre-flight:* skim the PD port's `port/src/input.c` mouse path first and match
its conventions (sensitivity units, dt handling, focus-loss behavior) so the
result feels like PD PC rather than a reinvention. GEPD supplies the GE camera
math; PD supplies the UX shape.

Implementation:

- New path `hipDirectCompute()` next to `aimGepdCompute()`: convert this
  poll's dt-scaled px to degrees using the *current* viewport
  (deg/px = fovy/viewH, or hfov/viewW — reuse whatever D194 absolute aim used),
  scale by `MouseTurnSpeed * MouseSensitivity`, and add straight to
  `g_CurrentPlayer->vv_theta` / `vv_verta` (clamp ±90). Same confinement as
  today: only when `idx==0`, cursor captured, in a running stage.
- **GEPD's safety gates** must be ported over (aim mode got away without them
  because it requires RMB held; hipfire is always live): check the decomp
  equivalents of GEPD's `camera==4||0 && menupage==11 && !dead && !watch &&
  !pause` before writing. `menupage` → `current_menu` (already have); the rest
  are `player`/game globals — read-only, no logic change.
- **Tank**: GEPD writes a separate tank-rotation global with its own scale and
  locks crosshair X to 0 when driving with the tank equipped. Find the decomp
  symbol for `0x80036484` (tank.c) and mirror it; if too fiddly, phase 2 —
  tanks are rare in single-player.
- Keyboard turn (arrows → stick) keeps the existing stick path; only mouse px
  goes direct. Escape hatch: `Input.MouseDirectLook=1` default, `0` reverts to
  the current stick path (kept as-is).
- This makes hipfire and aim mode share one linear mental model: px → screen
  angle, FOV-scaled, dt-normalized. Expect to then simplify or delete the
  D166/D238 curve-tuning knobs that become inert (`MouseAimCurve`, `AimBand`,
  legacy `MouseAimSpeed`) — *after* playtest, and keep the config keys as
  no-op aliases so existing inis don't break.

**WI-2: raw input by default.** Flip `Input.MouseRawInput` default to 1 (SDL
hints already handled in `inputInit`). Verify Windows relative-mode deltas are
unaffected; this mainly fixes Linux feel. Keep the escape hatch.

**WI-3: one honest sensitivity number.** With WI-1, hipfire and aim both scale
off px→degrees, so `MouseSensitivity` becomes genuinely master. Add it to the
F10 overlay (see WI-5), document the knob hierarchy in the generated ini
header comment, and re-calibrate defaults against GEPD's SENS≈40 ≈ 1:1
screen-angle mapping (our current 38/50/100 trio should land close; measure,
don't guess).

**Verification:** `GE_INPUTLOG` linearity check — log px-in vs deg-out at slow
and fast speeds (ratio must be constant); headless script harness for the
stick-fallback path; manual playtest checklist (hipfire slow/fast, aim mode,
scope zoom, tank, menu, death/cutscene safety gates). New finding `Dxxx` in
`docs/dev/findings.md`, index row added.

## 3. Issue #90 — in-game key bindings + "ini binds don't work" + sensitivity menu

### Diagnosis candidates for "binds don't work properly" (repro before fixing)

1. **Not a bug, GE design:** in-game, a fresh A edge *without* Z held is the
   weapon-cycle-forward signal (D223 documents `weaponForwardOffset`). The
   default Action bind includes E — so "pressing E changes weapon" is the
   game's own behavior, and "Escape reloads/activates switches" is the default
   Cancel=Escape → B button. The user's mental model (PC: E = interact)
   collides with GE's A/B semantics. Address via documentation + possibly a
   PC-idiomatic default set (product decision; GEPD itself uses Q=A, E=B).
2. **Ini syntax footgun:** keys must be written as `Input.Bind.Action=E` (or
   `Bind.Action=E` under `[Input]`). A bare `Action=E` under `[Input]` resolves
   to `Input.Action`, which is unregistered and silently ignored. `configLoad`
   also ignores unknown keys with no warning — add a log line for unrecognized
   keys so users get feedback.
3. **Key-name format:** binds use SDL scancode names (`"Left Ctrl"`, `"Up"`,
   `"Space"`); nothing documents this in the ini. Add per-key comments in
   `configSave` output and/or a `# valid names: ...` header.
4. There may still be a real parse bug lurking (`strtok` on the seeded buffer,
   constructor ordering vs `configLoad`) — **repro first**: write an ini with
   `Input.Bind.Action=E`, launch, confirm via `GE_INPUTLOG` that E alone
   produces A. Fix whatever actually breaks; don't fix hypotheticals.

### Work items

**WI-4: keybind audit + ini ergonomics.** Repro (above), fix real bugs, add
unknown-key warnings, document scancode names in the saved ini. Cheap, do first
— it unblocks #90's half regardless of the UI work.

**WI-5: F10 overlay — bindings section + master sensitivity.**
Model the UX on the PD port's shipped in-game options menu (standing reference
checkout) where anything is player-facing. `optionsoverlay.c` already has
row/hit-test/scroll infrastructure and owns all input while open; what's missing:

- A new row kind `ROW_BIND`: label = action, value = first bound key name;
  click → "press a key…" state that captures the *next* scancode (keyboard or
  mouse button), writes it into `g_bindStr[a]` (replacing or appending —
  decide: GEPD/PD use one primary + optional secondary; simplest v1 = replace
  single key, keep multi-key only for ini power users), then `inputRebuildBinds()`
  + persist via the existing config save path.
- Expose `Input.MouseSensitivity` (master), and after WI-1 trim the panel to
  master + per-mode fine-trim + invert Y (drop inert legacy rows).
- Bind capture must swallow all input while armed (overlay already does this)
  and handle ESC = cancel, Backspace/Delete = clear.

**WI-6 (nice-to-have, from GEPD): crouch toggle.** GEPD's `CROUCHTOGGLE` state
machine (`GE_Crouch`) is ~20 lines and pure port-side (stance flag write).
Low priority; include only if WI-1..5 land cleanly.

## 4. Suggested order

1. **WI-4** (keybind repro/fix + ini docs) — small, unblocks #90 partially.
2. **WI-1** (direct hipfire) + **WI-2** (raw input default) — the #89 fix;
   playtest-heavy, needs the safety gates done right.
3. **WI-5** (overlay binds + master sens) — completes #90.
4. **WI-3** (sensitivity consolidation/cleanup) — after WI-1 defaults settle.
5. **WI-6** (crouch toggle) — optional garnish.

## 5. Constraints reminders

- All work is `port/`-only: direct struct writes are the established D194
  pattern (read/write live game state from the input poll, no logic change).
  Any temptation to "fix" the natural-turn curve in `src/game` = rule-2 sign-off
  territory — don't.
- Keep every removed/renamed ini key registered as an alias so shipped inis
  keep loading; log deprecations at startup.
- Findings: new `Dxxx` entries for WI-1 (hipfire direct look), the #90 bind
  repro outcome, and the overlay bind UI; update `findings-index.csv`.
