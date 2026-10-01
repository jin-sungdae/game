# MELLO JUMP Animation Profile Pilot v1

## Architecture proposal before implementation

MovementController remains the sole owner of world position, trajectory and ground contact. Existing JUMP uses normalized motion progress p and y = ground + height * 4p(1-p), not a physics velocity integrator. Publish a bounded native jump presentation sample (phase, grounded, analytic vertical velocity, progress) with the existing snapshot. The reusable resolver selects the matching supplied frame, without elapsed animation time, new RAF/timers, fetch, or animation-driven movement. Keep higher-priority encounter/presentation suppression and reduced-motion own-base fallback.

Alternative: a fixed eight-frame loop would detach landing from ground contact and is rejected. React-derived trajectory inference would duplicate movement ownership and is rejected. No preparation/recovery delay is added: CROUCH and SETTLE have no native runtime state and are NOT_APPLICABLE in this pilot. NEUTRAL/ordinary IDLE uses MELLO own base. LAUNCH/ASCEND/APEX/DESCEND/LAND are derived from actual accepted JUMP movement; cancellation is not landing.

Use the existing canonical manifest → generated static TS pipeline; preserve supplied delivery manifest and byte-identical PNGs. JUMP phase mapping is reusable by movement profile, while asset availability remains registered per character. No production activation of IDLE/REACT artwork, policy/inventory expansion, gameplay change, or visual approval is implied.

Implementation, tests and actual production GUI evidence: NOT_RUN at proposal creation. Visual review was pending at proposal creation; the Alpha approval below supersedes that historical status. No automatic merge.

## Implemented contract and verification

Native `movement::jump::Sample` reports progress, accepted position, analytic vertical velocity, grounded and phase. Phase windows: first5% LAUNCH, until45% ASCEND,45–55% APEX, after55% DESCEND; LAND requires completed movement and actual ground coordinate. Monotonic progress provides apex hysteresis without direction chatter. Blocked/cancelled motion clears the sample instead of inventing LAND. The next inactive tick returns to own-base IDLE. No CROUCH/SETTLE state or delay is invented.

MELLO and BUBU share the same JUMP movement implementation; their CURIOUS/PLAYFUL behavior decisions can differ in distance/speed, so animation uses movement progress rather than a fixed640ms loop. Only MELLO supplies the registered artwork in this pilot. `jumpProfile` opts assets into the reusable phase resolver, without a MELLO-specific native movement path.

Canonical metadata keeps the existing clip schema; the80ms field is schema compatibility metadata and is never used to advance JUMP frames. Supplied1-based file names are preserved. IDLE/REACT/Blink remain unavailable for MELLO. Static loader validates identity, phase map, canvas and complete frame loading before use; failures resolve to MELLO own base. Shared clock ownership, native facing, CSP, server authority, arrival/rarity and battle/capture suppression remain intact. Reduced Motion uses own base while gameplay trajectory continues.

Actual production capture found and fixed a one-callback stale-frame boundary: JUMP now selects its frame directly in the same native-snapshot render, bypassing time-loop playback. [Final evidence and explicit limitations](evidence/mello-jump-v1/README.md) includes real-server identity,25s review video, two complete jumps, phase trace, registration, Focus/Single Instance and restoration. Original failed evidence is retained. The historical MANUAL_VISUAL_REVIEW status is superseded by the Alpha approval below. Final release/CI results are recorded on the PR against its final HEAD.


## Alpha Pilot Production approval — 2026-10-01

The user approved the supplied MELLO artwork and movement-owned resolver as the reusable Alpha Pilot Production JUMP Profile. Registry status is `JUMP_PRODUCTION`: LAUNCH, ASCEND, APEX, DESCEND and LAND are PRODUCTION; CROUCH and SETTLE remain NOT_APPLICABLE. MELLO IDLE uses its own base; REACT remains NOT_SUPPLIED with own-base fallback.

Future JUMP monsters reuse `jumpProfile`, the native phase sample and phase resolver, while registering their own artwork separately. MovementController continues to own world x/y, trajectory and ground contact. Monotonic progress with the45–55% apex band and same-snapshot LAND rendering are approved. No timer-driven sequence, preparation/recovery state, or gameplay delay is introduced to extend LAND.

Squash/stretch strength and overall liveliness may be refined in future visual polish and are not Alpha blockers. The approximately1.5pt facing reversal silhouette excursion remains a Known Visual Issue. Historical failure/GUI evidence is preserved. Final-head release and CI results are recorded on PR51; no automatic merge.
