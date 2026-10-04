# PUFF Alpha Production acceptance

Human approval: AUTOMATED_ACCEPTED / GUI_VISUAL_QA_DEFERRED.

| Sequence | Production acceptance | Approved Alpha default |
| --- | --- | --- |
| HOVER | PRODUCTION | 4 frames / 2000ms cycle |
| FLOAT | PRODUCTION | 6 frames / 200ms per frame / 1200ms cycle |
| SETTLE | NOT_APPLICABLE | Supplied 400ms asset only; no native trigger |

Approval is based on FLOATING resolver, original asset integrity, historical native
HOVER evidence, automated regression, Release Gate and CI. It is not approval of
unobserved renderer behavior. Future visual polish remains possible.

No production source, assets or numerical timing values change in this finalization.
The loader's existing `SUPPLIED` flag describes delivery and already permits playback;
it is retained under the instruction not to edit production code. This acceptance
record specifies the human-approved sequence states and defaults, not a new runtime gate.

Native inactive excursion selects HOVER. Active excursion with meaningful movement
enters FLOAT; FLOAT remains through a slow apex while the excursion remains active.
Completion/cancel returns to HOVER. MovementController retains world ownership.
No preparation/recovery state, SETTLE trigger, timer, or placement bypass is added.

GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE is preserved as the actual preflight
outcome. Under this human Alpha decision it is neither a production defect nor a
merge blocker. It is never relabeled PASS. Existing historical and blocked evidence
in docs/evidence/puff-floating-v1/summary.json is preserved.

Deferred visual measurements remain NOT_VERIFIED and are tracked in
[Monster Visual Regression Sweep](monster-visual-regression-sweep.md). No new actual
FLOAT recording or renderer measurement was produced by this acceptance decision.
