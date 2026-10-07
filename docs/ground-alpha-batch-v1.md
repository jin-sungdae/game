# GROUND Alpha Batch Expansion v1

Representative: PIP. Consumers: PIP, MOSSY, PEBB, TIKKI.

## Minimal frame-count generalization

Before: the generic pilot loader used `p.character === 'PIP'` to select IDLE4.
After: `groundProfile: GROUND` selects shared `groundClips` metadata (IDLE4 / 450ms,
MOVE8 / 80ms); the canonical manifest is validated against that profile contract.
Character identity does not determine frame count. The focused profile guard rejects
invalid count/timing/loop and retains existing asset failure behavior.

The explicit consumer mapping selects PIP's existing `walk` clip versus the new
consumers' `move` clip. PIP's canonical manifest, 00-based files and all bytes are
unchanged. New delivery files retain original 01-based names through existing
`firstFrame:1`. No new manifest schema, resolver, rate system or loader redesign.
The generated static registry includes the three new canonical manifests without
runtime fetch or CSP changes. Original ZIP manifest is preserved once under
`docs/evidence/ground-alpha-batch-v1/delivery-manifest.json`.

All four consumers use the same unchanged AnimationStateResolver and CharacterAnimator
through the unchanged CharacterRenderer dispatch. IDLE is 4 frames / 1800ms; MOVE is
8 frames / 640ms at 1×. Existing speed-based cadence stays bounded at 0.5–2× (slow
MOVE can take 1280ms; fast MOVE 320ms). Existing entry/retention thresholds remain
unchanged, including the GROUND resolver's >=3pt/s retention boundary.

## Domain boundary and compatibility

MOSSY remains SLEEPY: initial pause and slow 8pt/s wander. PEBB remains PASSIVE: idle/
pause and 10pt/s wander. TIKKI remains CURIOUS: 14pt/s approach. Native tests exercise
real profile decisions and each identity's grounded motion, LEFT/RIGHT facing and
stationary facing retention. Animation does not copy PIP gameplay behavior or modify
spawn/content, world position, velocity, target or native movement.

Each failed animation uses that monster's own base. New consumers have no REACT
asset/trigger added. Existing PIP deterministic REACT coverage and mouse ENGAGED/Battle
contract remain unchanged. Lifecycle/rarity/capture/despawn suppression is still
owned by the existing caller. Reduced motion affects presentation only; native motion
is untouched. MOA and all other profile loading paths retain their existing contract.

Production runtime changes are limited to `src/animation/pilot.ts` (profile metadata,
consumer mapping and loading guard) and generated `src/animation/generated-manifests.ts`.
Native changes are tests only. Preservation hashes include the complete PIP asset tree,
three existing bases, renderer, loader, model, clock, CSP, movement and content. Resolver
and animator source portions are identical to baseline. See the evidence summary.

## Evidence and acceptance boundary

36 PNG bytes match the approved ZIP. All are 256×256 RGBA with transparent pixels.
Measured alpha silhouette center-X, center-Y and bottom variation are 0px for each
consumer across its twelve frames. These source measurements are not renderer drift.

Parameterized tests cover four consumers' static files, frame counts/order/cycles,
rate bounds, transition, lifecycle, reduced motion and invalid/missing asset fallback.
Native fixtures test the actual SLEEPY/PASSIVE/CURIOUS decisions and movement/facing.
The full release gate includes PIP, MOA and every previously supplied Monster profile.
Final clean HEAD gate/CI results are recorded on the PR.

All three #54 common harness preflights returned GUI_ENVIRONMENT_BLOCKED /
NO_SAFE_CANDIDATE after their five-second countdowns. No user windows were moved,
resized or closed; no placement bypass/debug entity was used. Actual GUI playback,
transition, facing, renderer drift, clipping, observed cycle and recording remain
NOT_VERIFIED / GUI_VISUAL_QA_DEFERRED in the Monster Visual Regression Sweep backlog.
AUTOMATED_ACCEPTED remains separate from GUI acceptance.

## Alpha Production approval — 2026-10-07

Human approval accepts MOSSY, PEBB and TIKKI as Alpha Production consumers of the
existing PIP GROUND Production Profile.

| Consumer | IDLE | MOVE |
| --- | --- | --- |
| MOSSY | PRODUCTION — 4 frames / 1800ms | PRODUCTION — 8 frames / 640ms at 1× |
| PEBB | PRODUCTION — 4 frames / 1800ms | PRODUCTION — 8 frames / 640ms at 1× |
| TIKKI | PRODUCTION — 4 frames / 1800ms | PRODUCTION — 8 frames / 640ms at 1× |

The existing bounded 0.5–2× playback and PIP backward compatibility are approved.
GROUND profile/manifest metadata defines IDLE4/MOVE8 instead of a character == PIP
frame-count decision. PIP/MOSSY/PEBB/TIKKI share the same resolver/animator contract;
no new resolver, engine or rate system is introduced.

This finalization changes approval documentation only. Production runtime, assets
and timing remain unchanged. Existing SUPPLIED values describe delivery readiness;
this record establishes human Production approval without changing runtime metadata.

GUI_ENVIRONMENT_BLOCKED remains GUI_VISUAL_QA_DEFERRED. All actual GUI NOT_VERIFIED
items and the Monster Visual Regression Sweep backlog are preserved, not relabeled PASS.
After final HEAD release validation and CI pass, PR #60 is Ready for Review under
this human approval. Automatic merge remains prohibited. Final results are recorded
on the PR against its HEAD.
