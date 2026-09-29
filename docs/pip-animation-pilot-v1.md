# PIP Character Animation Pilot v1

PIP reuses the existing CharacterRenderer, AnimationStateResolver, Shared Animation Clock and canonical-manifest → generated TypeScript registry. Only PIP animation readiness and supplied metadata change. No animation engine, production event, RAF, interval, polling or manifest fetch is introduced. MOA production animation and all supplied MOA bytes remain unchanged.

| PIP sequence | Readiness | Alpha Pilot approved default / coverage |
|---|---|---|
| IDLE | PRODUCTION |4frames,450ms/frame,1800ms loop |
| MOVE | PRODUCTION |8frames,80ms/frame,640ms at1× |
| REACT | SUPPLIED — mouse event NOT_APPLICABLE |6frames,80ms/frame,480ms non-looping |
| BLINK | NOT_SUPPLIED | No clip, schedule or borrowed MOA frames |

Source ZIP byte hashes and metadata are retained under [evidence](evidence/pip-animation-v1/source-manifest.json). `idle/breath_01..04` map to `idle/idle_00..03`, `move/move_01..08` to `walk/walk_00..07`, and `react/react_01..06` to `react/react_00..05`. Only names change. All18 originals validate256×256 RGBA, transparency, bottom-center,RIGHT source and0px center/bottom registration. PIP own base is untouched.

## Actual Monster contract

PIP content is GROUND / PLAYFUL / NEAR_DOCK, not a Companion WALKING state machine. Native Monster movement owns all x/y. The renderer receives measured speed while native state remains ROAMING. Zero speed selects IDLE; actual ambient movement selects MOVE with existing8/3 speed hysteresis. The existing shared resolver uses a bounded0.5–2× playback rate relative to40pt/s. PIP's14pt/s Wander (telemetry quantized near16) reaches the0.5× floor, so its actual cycle can be1280ms;24pt/s ShortBurst gives approximately1066.7ms at0.6×.640ms is the approved1× Alpha default, not a claim that actual movement always plays that period. No PIP world speed or timing policy is changed to force a comparison.

Actual PIP click enters ENGAGED/encounter and may start battle through the existing server command. ENGAGED is intentionally suppressed by the resolver. There is no unsuppressed production REACT event for PIP. **Actual mouse REACT: NOT_APPLICABLE.** REACT frame order/completion/fallback is covered by deterministic animator/state tests; no new gameplay trigger is invented for QA.

Creature's existing Spawn/Rarity, battle, capture/effect, busy, evolution and despawn suppression remains above animation. Missing/invalid clips fail atomically to `/assets/monsters/pip/base.png`; no MOA or other-monster fallback. No idleSequences metadata is supplied, so PIP does not schedule Blink. The stable encounter-id renderer identity and existing subscriber cleanup are retained.

## Historical facing limitation (resolved by merged PR50)

Existing native server PIP starts with facing−1 and does not update facing from ordinary ambient movement direction; it only flips after the existing boundary-clamp branch. Thus RIGHT travel can remain LEFT-facing. Source RIGHT and renderer horizontal flip are preserved; both directions are covered deterministically. No native facing repair is included without separate scope confirmation. Actual RIGHT-facing proof must not be inferred from RIGHTward travel.

## Verification and human gate

The initial full release gate passed18 composed checks;46 asset tests and animation/content/presentation, Rust/clippy/fmt/Tao and Java/PostgreSQL integration pass. [Initial report](evidence/pip-animation-v1/release-initial.json) records its dirty pre-commit status. Final clean-HEAD result is reported in the PR.

GUI tooling is extended only with an optional named recorder window and `frames-pip` observer. It captures actual ScreenCaptureKit pixels/native AX labels, never HTML mock playback. PIP selection fixture modifies weights only in run.py's newly created isolated QA DB; production DB/defaults are untouched. The existing native right-click requests a real server encounter and normal placement/reconciliation.

Initial actual GUI attempt: server encounter succeeds, but existing window-obstruction checks deny safe placement because other apps cover the main screen's ground band. No bypass/debug-PIP substitution is accepted. That historical attempt did not establish playback/transition/clipping PASS. A subsequent user-authorized minimal window adjustment enabled actual GUI QA; see the follow-up below. The first QA session was stopped with evidence retained under `/Users/jinseongdae/Documents/LUMA QA/pip-animation-v1/`.

Historical pilot visual review preceded the final human approval below. IDLE/MOVE artwork and timing are now approved Alpha defaults; future visual polish may tune them. REACT remains deterministic asset/state coverage only. No automatic merge.

## Actual GUI follow-up

[Server PIP recordings, quantitative measurements, facing trace and window restoration](evidence/pip-animation-v1/gui/README.md) now cover actual IDLE and LEFT/RIGHT movement on the unchanged production bundle. Ambient center/bottom drift0pt, no clipping or base fallback. RIGHT-facing remains an existing native runtime KNOWN_ISSUE; it was not repaired or hidden with inverted artwork. Both adjusted user windows were restored exactly.

## Latest-main final integration

PR50 is now integrated from main `c7aadd8`. [Final production GUI evidence](evidence/pip-animation-v1/integration/README.md) verifies animation plus native facing together:249 stable moving samples match direction, IDLE4/MOVE8 order has no observed gaps,10 transitions each way, and0pt center/bottom drift. The older limitation and blocked-session evidence above are historical. PIP IDLE/MOVE subsequently received human Alpha Production approval; REACT asset readiness is SUPPLIED. Mouse REACT remains NOT_APPLICABLE.

## Alpha Pilot Production approval — 2026-09-29

Human approval finalizes supplied PIP IDLE4/1800ms and MOVE8/80ms per frame,640ms at1× as Alpha defaults. Existing bounded0.5–2× velocity-linked playback remains. Registry uses the existing IDLE_PRODUCTION status plus moveStatus PRODUCTION; reactStatus SUPPLIED describes retained6-frame deterministic coverage, not a mouse-triggered behavior. Blink remains NOT_SUPPLIED.

Click → ENGAGED/Battle is the production interaction contract. Mouse REACT remains NOT_APPLICABLE. Merged PR50 native facing and249 stable moving samples/zero mismatches are preserved. MOA's historical1.5pt silhouette reversal is not a PIP blocker. All prior failed/blocked-placement and GUI evidence is retained unchanged as history. Future artwork/timing polish is permitted by the approval, but no tuning is performed here.

Final-head release gate and GitHub CI are reported in PR49. Ready for Review follows passing verification; no automatic merge.
