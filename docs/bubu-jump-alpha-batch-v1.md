# BUBU JUMP Alpha Batch Expansion v1

Representative: MELLO. Consumers: MELLO and BUBU, sharing the existing movement-owned
JUMP phase resolver. BUBU is approved as an Alpha Production consumer; SUPPLIED runtime metadata records asset delivery readiness.
No new resolver, engine, MovementController or timing system is introduced.

The `jumpConsumers` table in `src/animation/pilot.ts` resolves identity-specific paths.
Canonical BUBU metadata generates the static registry; no runtime manifest fetch.
Original delivery manifest and eight PNG bytes are preserved in `bubu/jump/`.

| Slot | Phase | Runtime applicability |
| --- | --- | --- |
| 01 | NEUTRAL | Not an active jump phase |
| 02 | CROUCH_SLOT / canonical CROUCH | NOT_APPLICABLE |
| 03 | LAUNCH | Existing native phase |
| 04 | ASCEND | Existing native phase |
| 05 | APEX | Monotonic progress 45–55% |
| 06 | DESCEND | Airborne descent |
| 07 | LAND | Ground contact snapshot, same render |
| 08 | SETTLE_SLOT / canonical SETTLE | NOT_APPLICABLE |

The existing eight-slot non-looping loader is unchanged. Its 80ms metadata does not
time JUMP: native movement snapshots select frames. No preparation/recovery timers.
World X/Y, trajectory, ground contact, velocity and facing remain native-owned.
PLAYFUL/ShortBurst is unchanged. Horizontal movement controls facing; vertical-only
movement retains it. Missing/invalid JUMP falls back to BUBU own base, never MELLO.
IDLE/REACT remain own-base. Lifecycle and reduced-motion policies remain unchanged.

Source center-X 129.5px, center-Y 138.5px, bottom 245px; variation is 0px for all three
across eight frames. jump08 equals jump01 byte-for-byte. Evidence and preservation
hashes: `evidence/bubu-jump-alpha-v1/`. Source registration is not renderer evidence.

Tests cover both consumers, all active phases, APEX boundaries, same-snapshot LAND,
rejection of airborne LAND/stale grounded DESCEND, eight slots, invalid metadata,
missing frames, own-base fallback, suppression, reduced motion, native PLAYFUL
ShortBurst, trajectory and LEFT/RIGHT/vertical facing. The full release gate covers
all existing Monster profiles, MOA and server gameplay. Final clean-HEAD release/CI
results are recorded on the PR.

Common #54 preflight returned GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE with zero
user window mutations. Actual BUBU playback, renderer drift, bounds, clipping,
facing and production recording remain NOT_VERIFIED / GUI_VISUAL_QA_DEFERRED.
Automated acceptance does not imply GUI acceptance. See the shared sweep backlog.

## Alpha Production approval — 2026-10-07

Human approval accepts BUBU JUMP as PRODUCTION using the existing MELLO JUMP Profile.
LAUNCH, ASCEND, APEX, DESCEND and LAND are Production phases. CROUCH and SETTLE
remain NOT_APPLICABLE; no synthetic preparation or recovery is introduced.

MELLO/BUBU share the unchanged JUMP resolver, movement-progress 45–55% APEX band,
ground-contact same-render LAND selection and eight-frame loader contract.
PLAYFUL/ShortBurst retains native ownership. No new resolver, MovementController
or timing system is added. This finalization changes approval documentation only;
Production runtime, assets and timing remain unchanged.

GUI_ENVIRONMENT_BLOCKED remains GUI_VISUAL_QA_DEFERRED. Actual GUI NOT_VERIFIED
items and the Monster Visual Regression Sweep backlog are preserved, not marked PASS.
Final clean-HEAD Release Gate and CI results are recorded on PR #61 before marking
it Ready for Review. Automatic merge remains prohibited.
