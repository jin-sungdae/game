# MELLO JUMP Animation Profile Pilot v1

## Architecture proposal before implementation

MovementController remains the sole owner of world position, trajectory and ground contact. Existing JUMP uses normalized motion progress p and y = ground + height * 4p(1-p), not a physics velocity integrator. Publish a bounded native jump presentation sample (phase, grounded, analytic vertical velocity, progress) with the existing snapshot. The reusable resolver selects the matching supplied frame, without elapsed animation time, new RAF/timers, fetch, or animation-driven movement. Keep higher-priority encounter/presentation suppression and reduced-motion own-base fallback.

Alternative: a fixed eight-frame loop would detach landing from ground contact and is rejected. React-derived trajectory inference would duplicate movement ownership and is rejected. No preparation/recovery delay is added: CROUCH and SETTLE have no native runtime state and are NOT_APPLICABLE in this pilot. NEUTRAL/ordinary IDLE uses MELLO own base. LAUNCH/ASCEND/APEX/DESCEND/LAND are derived from actual accepted JUMP movement; cancellation is not landing.

Use the existing canonical manifest → generated static TS pipeline; preserve supplied delivery manifest and byte-identical PNGs. JUMP phase mapping is reusable by movement profile, while asset availability remains registered per character. No production activation of IDLE/REACT artwork, policy/inventory expansion, gameplay change, or visual approval is implied.

Implementation, tests and actual production GUI evidence: NOT_RUN at proposal creation. Human visual review of squash/stretch strength remains required. No automatic merge.
