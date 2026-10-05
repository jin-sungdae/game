# Alpha Production EDGE Animation Profile

SHADE IDLE (5 frames / 2200ms) and EDGE_MOVE (6 frames / 1080ms, fixed 1×) are human-approved Alpha Pilot Production defaults. Other EDGE monsters use their own artwork with this reusable presentation contract.

Native EDGE selects the nearest LEFT/RIGHT safe side, fixes target X, moves vertically and can reverse vertically at a boundary. World x/y, target, edge behavior and reversal remain owned by MovementController. Horizontal perimeter traversal and corner traversal are NOT_APPLICABLE.

Presentation uses existing accepted-displacement speed: enter EDGE_MOVE at >=8pt/s; remain only above 3pt/s. Low/stopped speed selects IDLE. Finalization aligns the exact 3pt/s boundary with this approved contract (previous pilot used >=3). Smoke flow is not a stride cycle, so cadence stays fixed at 1×. Shared clock, static registry, lifecycle priorities, reduced motion and own-base fallback are preserved.

TURN is NOT_APPLICABLE: its assets remain for deterministic coverage, with no production trigger, random timer or cycle-driven event.

## Known risk and deferred visual QA

Source center-X is 131.5–132.5px: reference deviation ±0.5px and peak-to-peak 1.0px. This is not 0px. Actual renderer hopping is NOT_VERIFIED.

GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE is neither a production defect nor GUI PASS. Actual SHADE, vertical movement/reversal footage, renderer center-X/Y/bottom drift, panel/canvas bounds, clipping and smoke naturalness remain GUI_VISUAL_QA_DEFERRED for Monster Visual Regression Sweep. Historical [acceptance](evidence/shade-edge-v1/acceptance.json) and [source measurements](evidence/shade-edge-v1/source-registration.json) are retained.
