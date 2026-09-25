# Character Animation System v1 — MOA/PIP Pilot

## Proposed scope and alternatives (before implementation)

Behavior/gameplay → AnimationStateResolver → IDLE/MOVE/REACT → CharacterAnimator → CharacterRenderer. MovementController retains all position, velocity and safe-area authority. The native runtime observes pre/post MovementController positions to publish quantized speed changes; the renderer never writes world coordinates. Existing snapshots are state-only, so inferring speed from their sparse positions would be incorrect.

Reuse the existing frame-sequence manifest/AssetIO architecture, registry-derived own-character roots and browser image cache. Decode each complete clip before use. A shared lifecycle-managed requestAnimationFrame clock replaces per-character animation clocks for the pilot. Keep React entity identity stable across state/frame changes and same-encounter reconciliation.

Alternative: a new sprite-sheet framework would add another asset format and validator path; per-character timers would fragment lifecycle ownership. Neither is needed. Existing frame sequences are the smaller extension. Only MOA Stage1 and PIP opt in; other stages/species retain their base path.

Animation transforms live inside facing and existing spawn/gameplay/evolution wrappers. Special presentation suppresses pilot animation; REACT then MOVE then IDLE follow. Missing/unprovided/invalid animation falls back to the same character production base, then existing diagnostic fallback. Production PNGs are immutable in this PR; no animation artwork supplied/generated.

This explicitly requested presentation-layer addition requires human architectural review before merge. Implementation and validation evidence will be appended; no automatic merge.


## Final architecture / runtime ownership

`presentation::animation::speed` observes actual native tick displacement, rejects discontinuities/non-finite inputs and quantizes in4pt/s buckets with a4pt/s hold band. Only bucket/state changes trigger the existing world event; no unconditional30Hz React publication. Rust owns all movement. The pure TypeScript resolver consumes speed, enters MOVE at8pt/s and leaves below3pt/s. REACT comes from rising existing REACTING/ENGAGED signals, lasts480ms, then samples current movement. No new interaction request is introduced.

`CharacterAnimator` integrates bounded0.5–2× rate against the shared animation clock. `AnimationClock` has one RAF subscription mechanism per existing WebView (native panels have separate JS contexts), regardless of subscriber count, and cancels when the last subscriber leaves. No character-owned RAF or interval. A frame change updates the existing image src after the complete clip loads through cached AssetLoader; entityId and character—not frame/state—own resolver lifetime. Same Encounter stays mounted; new Encounter/restart resets phase; despawn removes subscriptions and media listeners. Non-pilot characters retain their existing implementation.

Priority: spawn/despawn, any Battle/busy/gameplay impulse or Evolution GLOW/REVEAL suppresses pilot motion; then REACT > MOVE > IDLE. Suppression clears pending REACT. Drag/sleep are still in v1; SLEEP/BATTLE/HAPPY animation extensions are reserved only.

Layers: native world position → existing arrival / gp-pose / gp-impulse / gp-visual / evolution-pose → character-facing → character-animation → stable image. Flip origin and breathing origin are50%100%. Full256px canvas is fit inside the same82pt base envelope (PIP's existing outer0.8 scaling remains exactly once). Breathing contracts Y1→0.99→1 over2.8s without translation. Reduced Motion removes breathing and pins sprite playback to frame0; gameplay and native movement remain untouched.

## MOA / PIP asset delivery contract

No animation PNG is supplied in this PR. Both pilot registry statuses are NOT_SUPPLIED; they perform no speculative frame requests. After validated delivery, change only that pilot's status to SUPPLIED. Missing manifest, any missing/corrupt/wrong-dimension frame or incompatible metadata rejects the entire clip. An image render failure disables that clip for the current entity. Fallback is own base, then named diagnostic; never another species or stage.

| Field | MOA | PIP |
|---|---|---|
| Root | `/assets/creatures/moa/stage01` | `/assets/monsters/pip` |
| Manifest | root + `/manifest.json` (existing) | root + `/manifest.json` (new metadata only) |
| Own fallback | root + `/base.png` | root + `/base.png` |
| IDLE | `idle/idle_00.png` … `idle_05.png` | same relative names |
| MOVE | `walk/walk_00.png` … `walk_07.png` | same relative names |
| REACT | `react/react_00.png` … `react_05.png` | same relative names |

Each PNG is **256×256px RGBA8, transparent**, one full canvas per frame. **Frame size = canvas size; no packed sprite sheet, cropping, trimming or rotation.** Zero-based two-digit contiguous filenames, case-sensitive. All frames share bottom-center(128,256), normalized(0.5,1), identical body registration/foot baseline and source facing **RIGHT**. Transparent padding must remain identical; silhouette motion is allowed, canvas/foot offset motion is not. Artist must verify baseline/registration because alpha metadata alone cannot prove semantic feet.

IDLE6×100ms loops600ms; MOVE8×80ms loops640ms at1×, bounded40–160ms/frame at playback0.5–2×; REACT6×80ms non-looping480ms. Existing MOA manifest's non-pilot sit/look/sleep slots remain untouched; v1 reads only idle/walk/react. Actual rendering clamps the existing MOA display.width130 to the established82pt envelope; PIP manifest display.width82. Do not resize production base art.

Future18-character expansion is explicit registry opt-in plus same-character manifest identity and tests; no automatic enablement by asset existence. Asset delivery never changes gameplay contentReady/enabled or companion progression.

## Validation record

Automated: pilot13/13, asset33/33, existing animation/content/15-monster/presentation/evolution suites PASS; Rust148 PASS/16 ignored; clippy/fmt/Tao/build PASS. Isolated Java/PostgreSQL and natural Stage3 regression PASS (`/tmp/luma-animation-server-regression`). Development checks corrected a CSS test matching an explanatory comment and extended strict Alpha's root-file whitelist to accept only a validated canonical PIP manifest. Other unexpected/case-mismatched root filenames remain errors. No production artwork modifications.


## Approved RAF inventory delta (2026-09-25)

Reason: **Character Animation v1 shared clock**. The user explicitly approved only the RAF scheduling inventory migration. The prior approval blocker is resolved; no focus/network/backend-worker/setInterval/polling/per-frame HTTP/Tao policy or non-RAF inventory entry changed.

| Before | After |
|---|---|
| `src/animation/useAnimation.ts`: `if(!sample.finished) request=requestAnimationFrame(tick);` | `src/animation/clock.ts`: `export const animationClock=new AnimationClock(cb=>requestAnimationFrame(cb),id=>cancelAnimationFrame(id));` |

The update compared actual `alpha_release_policy.sources()`/`inventory()` output to the prior JSON. An assertion required exactly these two changed paths and these exact old/new call sites; all other inventory values were preserved. The policy scanner itself is unchanged. The shared singleton owns scheduling; renderers and the legacy hook only subscribe. A WebView with0 subscribers has0 RAF;1–16 subscribers have at most1 pending RAF. Separate native WebViews have separate JS runtimes, so this is explicitly one clock per WebView, not one cross-process/global clock.

A new reentrant-subscription test first reproduced2 pending RAF callbacks when a listener subscribed during a tick. The minimal guard now schedules the next frame only when no frame is already pending. Evidence: `/tmp/luma-raf-lifecycle-before.log` and `/tmp/luma-raf-lifecycle-after.log`. This is the third automatic correction in the PR; no broader runtime refactor.

Lifecycle unit verification:16 subscribers,100 setup/cleanup/remount cycles, repeated cleanup calls, zero pending RAF after final unsubscribe, and reentrant subscription all PASS. Real React development StrictMode verification: `tests/live/animation-clock.html` renders16 actual CharacterRenderer instances (MOA+PIP),20 mount/unmount cycles; **640 setups /640 cleanups, maximum pending RAF1, final pending0, all60 assertions PASS**. This tests the actual exported singleton and actual renderer effects, not just a simulated StrictMode sequence. Run `npm run dev -- --port 14209`, open `/tests/live/animation-clock.html`, and read its JSON output. The harness is test-only and not imported by the production entrypoint. It uses bounded waits for React effect delivery and restores its browser RAF wrappers after testing.

GUI evidence: `/tmp/luma-gui-qa-animation-v1`. Actual production PID80434, AX/CGEvent/TextEdit and per-owned-window screenshots using #44 helpers. Three typing runs retained exact markers/frontmost TextEdit; native activation/key-window count0. Actual PIP MOVE→REACT→IDLE and MOA IDLE/REACT recorded. Observed AX images kept bottomY1129pt during state/1% breathing changes; actual image rectangles fit their96×104pt panels. Secondary actual process exited0 without another World/panel. Gross clipping not observed in inspected images; aesthetics and unsupplied-frame registration remain MANUAL_VISUAL_REVIEW. MOA MOVE was not observed in the bounded natural-behavior observation; it remains NOT_OBSERVED, not a GUI PASS.

The original MOA/PIP base PNGs and all other production art are unchanged. No dependencies or movement/gameplay rules changed. Added native speed telemetry is observational only. The existing legacy frame hook also uses the shared clock now, retaining its state/clip controller semantics; each WebView has a single clock rather than each character constructing a new RAF loop.


Final shared-clock bundle replay: `/tmp/luma-gui-qa-animation-final`, actual production launch, exact TextEdit input/focus and real click Bond0→1 PASS. The original session contains18 screenshots plus1 fresh replay screenshot. Both owned QA apps/servers/PostgreSQL instances were stopped. No user Dock/Reduce Motion/other-app visibility settings were changed for this task. Scratch TextEdit documents remain for inspection. No animation artwork or placeholder PNG created.


Approved-delta validation rerun: `npm run validate:alpha:release -- --output /tmp/luma-raf-approved-release` completed **AUTOMATED_READY / MANUAL_QA_REQUIRED**. Pilot15, assets33, Rust148(16 ignored), Java/PostgreSQL, frontend, clippy, fmt and Tao PASS. Previous failure entries describe the pre-approval run only.

Production bundle rebuilt and rerun with #44 GUI tools: `/tmp/luma-gui-qa-raf-approved` and `/tmp/luma-gui-qa-raf-retest`. MOA/PIP simultaneous render, actual click and secondary-instance exit0/no extra World or panel verified; all native activation/key-window counts0. The first concurrent-capture/spawn typing run had one newline-order mismatch despite TextEdit remaining frontmost. Original typing document/diff are retained. The same input protocol spawn retest passed exact text and137 focus samples; no production focus defect is asserted or hidden. Aesthetic/supplied-frame and natural MOA MOVE observations retain their earlier limits. QA-owned app/server/DB processes were stopped. GUI JSON lists each trial individually; no failed trial erased.

Latest remote CI and Ready-for-Review state are verified on PR #45 after pushing these changes; hosted CI is not a substitute for the native GUI evidence above.
