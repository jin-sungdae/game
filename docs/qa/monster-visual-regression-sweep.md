# Monster Visual Regression Sweep backlog

Run one consolidated visual sweep when the approved #54 Native GUI QA Harness has a
READY environment. Do not reopen individual Monster pilot PRs solely for deferred
visual validation. Include PUFF and other Monsters whose actual renderer evidence is
still incomplete; determine their inventory from their evidence, not assumptions.

Use manual preparation, 5s countdown, read-only preflight and 3s stability gate.
GUI_ENVIRONMENT_BLOCKED ends the attempt without moving/resizing/closing user windows,
automating Mission Control, changing production behavior or replacing real entities.
Use unchanged release app, real isolated Server Encounters and real safe-placement.

## PUFF — DEFERRED_VISUAL_QA / Known Risk

Acceptance: AUTOMATED_ACCEPTED / GUI_VISUAL_QA_DEFERRED. These are not current Alpha
merge blockers. Each row remains NOT_VERIFIED until actual evidence is collected.

| Measurement | Current status |
| --- | --- |
| Actual FLOAT production recording; HOVER → FLOAT → HOVER | NOT_VERIFIED |
| FLOAT RIGHT | NOT_VERIFIED |
| FLOAT LEFT | NOT_VERIFIED |
| Vertical FLOAT visual evidence | NOT_VERIFIED |
| Direction reversal visual evidence | NOT_VERIFIED |
| Native excursion active ↔ FLOAT agreement in actual GUI | NOT_VERIFIED |
| Renderer center-X drift | NOT_VERIFIED |
| Renderer center-Y drift | NOT_VERIFIED |
| Bottom drift | NOT_VERIFIED |
| Panel/canvas bounds and clipping | NOT_VERIFIED |
| Mirror offset on actual reversal | NOT_VERIFIED |
| Actual FLOAT cycle measurement | NOT_VERIFIED |

Source center-X=131px gives a 6px source mirror-center difference. This is a Known
Risk, not a measured renderer jump. Without actual reversal, mirror offset stays
NOT_VERIFIED. Keep raw timestamps and native motion/animation/facing/flip observations,
record panel-local pixel measurements separately from world movement, and retain
sampling/mask limits. Preserve unavailable fields as null, never guessed PASS.

HOVER 2000ms and FLOAT 1200ms are now approved Alpha defaults; do not tune them as
part of evidence collection. SETTLE remains NOT_APPLICABLE. Publish reviewed native
clips/measurements with the sweep results, while retaining historical blocked evidence.

## WISP / LUNET — FLOATING batch, DEFERRED_VISUAL_QA

Both common harness preflights: GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE.
Actual HOVER → FLOAT → HOVER, LEFT/RIGHT/vertical movement, reversal, renderer center-X,
center-Y, bottom drift, mirror offset, panel/canvas bounds, clipping and measured
cycles remain NOT_VERIFIED. Collect real release-app Server Encounter evidence when
READY, using profiles `wisp.json` and `lunet.json`; no individual follow-up PR required.
The measured 0px source registration drift is not renderer evidence. Batch details and
preservation hashes are in `docs/evidence/floating-alpha-batch-v1/summary.json`.

## NOCT — EDGE consumer, DEFERRED_VISUAL_QA

Common harness preflight: GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE. Actual NOCT,
IDLE/EDGE_MOVE cycles and transitions, vertical movement/reversal, facing, renderer
center-X/center-Y/bottom drift, panel/canvas bounds, clipping and production recording
remain NOT_VERIFIED. Use `scripts/gui_qa/profiles/noct.json` in a future READY sweep
with the real release app, isolated Server Encounter and unchanged safe-placement.
Source reference X/Y deviation 0.5px each (X peak-to-peak 1px), bottom 0px is not GUI
proof. See `docs/evidence/noct-edge-alpha-v1/` for original-source measurements.

## MOSSY / PEBB / TIKKI — GROUND batch, DEFERRED_VISUAL_QA

All three common harness preflights returned GUI_ENVIRONMENT_BLOCKED /
NO_SAFE_CANDIDATE. Actual IDLE/MOVE cycles, transition, LEFT/RIGHT facing, renderer
center-X/center-Y/bottom drift, panel/canvas bounds, clipping and production recording
remain NOT_VERIFIED. Use the respective `mossy.json`, `pebb.json`, `tikki.json` profiles
in a future READY sweep with real release app and real Server Encounters. Source 0px
variation does not establish renderer PASS. No individual follow-up PR is required.
