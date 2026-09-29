# Monster Facing Runtime Fix v1

Latest-main base: `7bea47f63e54f0201183eddc942434232d341842` (PR48). PR49 is still separate and is not modified or imported: user explicitly selected a main-based native fix and actual PIP base-renderer QA. PIP animation integration remains deferred until that asset PR lands.

## Cause and minimal fix

`World::place_server_monster` initializes facing to−1. The server-owned ambient branch previously assigned MovementController's x/y without updating facing; the later boundary-only flip could not reflect ordinary RIGHT travel. Renderer correctly used the native facing. This defect existed before PIP animation assets.

Movement owns facing: derive horizontal velocity from the accepted controller displacement and capped dt, before committing that position. `vx > 3pt/s` means RIGHT(+1), `vx < −3pt/s` LEFT(−1); inside the inclusive deadband keep the previous value. This stateful deadband prevents small sign noise from toggling facing. No extra timer, polling, engine, RNG or temporal accumulator is introduced. Threshold matches the existing native presentation telemetry jitter floor; it is a domain constant, not an import from the frontend. The existing presentation 8/3 speed hysteresis determines animation state and is not made an authority over native orientation.

Finite dt0.001–0.1s is required; nonfinite or >256pt/s discontinuities preserve facing, matching the telemetry discontinuity guard. Threshold comparison uses displacement versus epsilon×dt to avoid division rounding at exact3pt/s. Active accepted ambient motion updates facing; stopped/cancelled, STATIC, pure vertical motion and interaction/battle locks retain it. Server monsters no longer use the debug-only boundary bounce flip; Debug PIP's old facing-driven movement remains unchanged.

Production changes are only `src-tauri/src/behaviors.rs` and `src-tauri/src/movement/mod.rs`. No renderer, asset geometry, CSP, clock, spawn threshold, interaction, Battle/Capture/Discovery policy or MOA movement change. This is a correction inside existing movement ownership, not an architecture replacement.

## Automated regression

- Deadband boundaries, alternating subthreshold jitter, standstill, real reversals, invalid time and discontinuities.
- Actual World/controller paths: PIP/GROUND, MELLO/JUMP, CHIRP/FLYING, PUFF/FLOATING, SHADE/EDGE, EMBER/FREE_2D, MIMI/STATIC. Direction alternation in moving profiles, vertical EDGE and stationary STATIC preservation, lock retention.
- Existing all15 identity world traces now assert velocity/facing correspondence while preserving positions, profiles, server identity, budgets and Companion independence.
- Full `npm run validate:alpha:release` is run on the final committed HEAD; exact report is attached to the PR. CI results must be checked on that same SHA.

## Actual production GUI

[Evidence, review clips and trace](evidence/monster-facing-v1/README.md). Actual release `.app`, unchanged production CSP, real PIP encounter on fresh isolated PostgreSQL/server. Native window screenshots provide a timestamped49.82s recording at approximately2.6 observed frames/sec. MP4 retains actual time; encoding60fps repeats samples and is not a claim of60fps capture.

LEFT→RIGHT→LEFT→RIGHT observed.85 stable moving image samples match both the logged native facing and independently inspected pixel direction. No facing mismatch away from150ms transition sampling uncertainty. Source-facing RIGHT and original horizontal flip are unchanged. Animation state is read from existing AX labels; source remains base on this main revision.

PIP horizontal visible silhouette excursion0pt. PIP bottom visible raster bound varies0.5pt across orientations, while native panel y stays fixed; this is reported, not asset-corrected or called0pt. MOA's preexisting reversal excursion is remeasured1.5pt, bottom0pt, no worsening. No panel clipping. Source visible bounds and output pixel bounds are preserved; asymmetric visible geometry plus mirroring/raster quantization explains why a facing flip can shift a silhouette despite a fixed canvas. This is an inference, not a geometry correction or proof of every compositing detail.

Focus/Single Instance: actual audit/three secondary launches pass; typing-in-another-app was not rerun. Actual live GUI profile coverage is PIP/GROUND; other profiles are deterministic native World tests, not fabricated GUI observations.

Temporary window adjustment: Kakao restored exactly. Four adjusted Excel window handles ceased to exist during QA; the app stayed alive with the three previously unadjusted windows. No Excel close/quit command was issued. No temporary850px window remains, but exact restoration of the disappeared windows is **NOT_VERIFIABLE**, not PASS. No closed document was reopened. See restoration snapshots.

No automatic merge. No PIP artwork/timing approval is implied by this native runtime fix.
