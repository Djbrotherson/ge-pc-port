# Accuracy / code review — N64 fidelity sweep (2026-09-20)

A thorough pass over the PC port with one question: *where does the port diverge from the
N64 original, and what latent failure classes of the D318 kind are still unpriced?*
Method: static review against the decomp ground truth + targeted verification builds.
Findings below; new finding **D320** logged in `findings.md`.

## 1. PRNG — verified bit-exact

`port/src/random.c` re-checked line-by-line against both `src/random.s` and
`src/game/chrObjRandom.s`. The MIPS64 `dsll32`/`dsrl32` semantics (post-D284) are
emulated correctly: the 32-bit LFSR state advances identically, and
`randomGetNext()` returns the same 31-bit values in the same order. No divergence.

## 2. Known bug-class sweeps — all clean or already fixed

| Class | Result |
|---|---|
| **A1** raw-byte/padding aliases (32→64-bit layout shift) | Remaining `padding[]` uses are in pointer-free structs (layout-stable) or already fixed (D115, D209, D312). No live misreads. |
| Shifts by 32 / pointer-width arithmetic in game logic | Only port-layer code (`d318watchdog` print, `DRAM_SIZE`). Game logic clean. |
| Signed-overflow UB | `-fwrapv` enabled in `CMakeLists.txt` — the whole class is neutralized to N64-wrap semantics. |
| `#ifdef PORT` hygiene (N64 path preserved) | 307 hunks audited; 178 are pure additions (diagnostics / struct extensions). No hunk alters the non-PORT control flow. |
| **§B** Gfx/Vtx 16-byte records (raw byte indexing) | `bg.c` uses typed `.words`/`.dma` fields throughout; no remaining raw byte offsets. D312's fix pattern is the last of this class. |
| `osVirtualToPhysical` call sites (88) | All flow through fast3d's `seg_addr()` (D131 fix intact). No site assumes N64 segment RAM layout. |
| Dead code | `objecthandler_2.c` compiles but is not linked on PC (symbols absent from the binary). Harmless; noted for a future source-list prune. |

## 3. Timing layer — intentional, documented

Frame-locked virtual clock (vsync tick), `GE_DETERM` fixed-tick mode, and
`g_GlobalTimerDelta` zero-guarded at every division site. All deliberate port-layer
design, each documented in its finding. No hidden drift source found beyond the
already-fixed D204 tempo work.

## 4. D318-class latent softlock sweep → **D320** (the main new result)

D318's mechanism is generic, not Facility-specific: `actor_fire_or_aim_at_target_update`
(`chraction.c:4882`) retargets any ACT_ATTACK chr with an AIM_ONLY/DONTTURN attacktype and
only moves the model's **endframe** — it never re-inits the animation. If the chr is pinned
on a pre-shoot aim-hold pose (hold endframe H < variant shoot window) and the new endframe
lands above H, the model pins forever and the timer-gated fire events never open; if the
surrounding AI script's only escape is an `if_guard_has_stopped_moving` gate, it can never
pass (`chrHasStoppedOrPatroling` is FALSE for ACT_ATTACK). **Permanent softlock — on N64 too.**

Swept every level's AI scripts (`assets/obseg/setup/*.c`): 17 lists in 8 levels contain an
aim-hold + `_update` pair. Risk-ranked table in the D320 entry. Headlines:

- **Facility ai_19** — HIGH. Same non-self-healing shape as ai_22 (second softlock point in
  the same level).
- **Control ai_9** — HIGH. Near-exact ai_22 mirror (pre-aim hold → timer → update → fire
  loop gated on the target dying from this guard's shot).
- **Depot ai_12** — MED-HIGH. The kill is scripted, but the objective bit is gated behind a
  stop-check; pinned guard → level-complete softlock.
- **Bond-combat loops** (Aztec/Control/Egyptian/Depot/Streets/Bunker/Surface) — likely safe:
  sustained fire keeps the model inside the shoot window by design, and every playtest
  exercises them without freezes. Inferred, not probe-verified per list.

Classification: **as-authored latent race(s), faithfully reproduced** — same bucket as D318,
not a port bug. Verification path (generalized timeline probe) and the
generalize-the-watchdog recommendation are in D320.

## 5. Fixed this session

- `port/fast3d/gfx_pc.cpp:2417` — the GE_D116 diagnostic printf used `%f` for `uint32_t`
  args (`v->u`, `tex_width`) and `%d` for unsigned tile fields; wrong debug output only, no
  runtime impact. Casts added; build now warning-free on that file.

## 6. Verification ritual

Full `./build-pc.sh ntsc-final` configure + compile + link: **PASS**, no warnings on
touched files. All new/changed symbols resolve exactly once (link is the sweep). D318
watchdog/timeline symbols confirmed present in the binary.

## 7. Deliberately not committed (release-prep WIP, separate workstream)

`.github/release-notes.md`, `README.md`, `docs/index.md`, `docs/media/goldeneye-gh-preview.gif`,
`docs/dev/agentic-development.md`, `.gitignore` (`/local/` exclude), and non-D318 scratch
artifacts — left in the working tree for their owner.
