# NOCT EDGE Alpha Batch Expansion v1

EDGE representative: SHADE. Consumers: SHADE, NOCT.

NOCT is a consumer of the approved EDGE contract, not a new profile implementation.
The `edgeConsumers` mapping in `pilot.ts` preserves SHADE EDGE_PRODUCTION and opts
NOCT in as SUPPLIED. Both dispatch through the unchanged `edgeProfile` renderer,
`resolveEdge`, clip loader and shared clock. No new resolver, engine or threshold.

| Sequence | Existing contract | NOCT delivery |
| --- | --- | --- |
| IDLE | Stationary/low speed; 2200ms | 5 frames × 440ms |
| EDGE_MOVE | Enter >=8pt/s; remain >3pt/s; fixed 1080ms | 6 frames × 180ms |
| TURN | NOT_APPLICABLE, no domain trigger | Not supplied |

All eleven PNGs and the delivery manifest are byte-exact ZIP copies under
`public/assets/monsters/noct/`. The canonical manifest reuses existing `firstFrame:1`
and `filePrefix:edge`; filenames are not changed. Generated static TS imports this
metadata; there is no runtime manifest fetch. NOCT base.png is unchanged.

## Registration evidence

Alpha silhouette measurements use exclusive bounds. Relative to first-frame center
(128,139.5), maximum center-X and center-Y deviation are each 0.5px; bottom is always
244px (0px variation). Center-X range 127.5–128.5px means **1.0px peak-to-peak**, not
0px or 0.5px peak-to-peak. Center-Y range 139.5–140px means 0.5px peak-to-peak.
Delivery max_delta and measured range are reported separately in
`docs/evidence/noct-edge-alpha-v1/source-measurements.json`. These source silhouette
variations are not world/panel displacement and are not actual renderer measurements.

## Native ownership and regression

MovementController retains nearest safe LEFT/RIGHT side, fixed target X, vertical
movement and wandering boundary reversal. TIMID avoidance projects onto that same
edge without adding a turn/corner behavior. NOCT NIGHT/content eligibility is unchanged.
The native test uses the existing NIGHT fixture and checks both safe sides, both
vertical avoidance directions, upper/lower wandering reversal, fixed X, retained
horizontal facing, accepted-displacement speed and completion. It calls the same
read-only speed adapter as main.rs. Deterministic native tests are not GUI proof.

SHADE/NOCT share parameterized registry, actual static-file loading, 8/3 hysteresis,
frame order/cycle, lifecycle, reduced-motion and own-base failure tests. SHADE retains
its existing TURN deterministic asset coverage with no production trigger. A failed
NOCT clip resolves to its own base only. Higher-priority lifecycle suppression and
reduced-motion presentation policy are unchanged; animation never writes world motion.

Production runtime changes: `src/animation/pilot.ts` consumer mapping and generated
`src/animation/generated-manifests.ts` metadata only. Native changes are tests only.
Renderer/resolver/clock/CSP/movement/content/base preservation hashes are recorded in
`docs/evidence/noct-edge-alpha-v1/summary.json`. Existing Monster and MOA regressions
remain part of `npm run validate:alpha:release`; final HEAD results are posted on the PR.

## GUI boundary

The common #54 harness countdown/preflight returned GUI_ENVIRONMENT_BLOCKED /
NO_SAFE_CANDIDATE. No user windows were moved/resized/closed and no production placement
bypass, mock entity or recording was used. Actual NOCT IDLE/EDGE_MOVE, transitions,
vertical/reversal footage, renderer center/bottom drift, clipping and actual cycles
remain NOT_VERIFIED / GUI_VISUAL_QA_DEFERRED in the shared sweep backlog.
Acceptance remains AUTOMATED_ACCEPTED + GUI_VISUAL_QA_DEFERRED, not GUI PASS.

## Alpha Production approval — 2026-10-06

Human approval accepts NOCT as an Alpha Production consumer of SHADE's existing
EDGE Production Profile:

| NOCT sequence | Approved state | Alpha default |
| --- | --- | --- |
| IDLE | PRODUCTION | 5 frames / 2200ms |
| EDGE_MOVE | PRODUCTION | 6 frames / 1080ms fixed 1× |
| TURN | NOT_APPLICABLE | No production trigger |

SHADE and NOCT reuse the same EDGE resolver. Entry >=8pt/s and retention >3pt/s
hysteresis are unchanged. No new resolver, engine, movement or facing behavior.
This finalization changes approval documentation only; runtime, assets and timing
are unchanged. Registry SUPPLIED continues to describe delivery readiness, while
this approval records NOCT's Production acceptance without changing runtime metadata.

GUI_ENVIRONMENT_BLOCKED remains GUI_VISUAL_QA_DEFERRED. All actual renderer
NOT_VERIFIED measurements and the Monster Visual Regression Sweep backlog are
preserved. This approval does not establish actual GUI acceptance.

After final HEAD release validation and CI pass, PR #59 may be Ready for Review
under this human approval. Automatic merge remains prohibited. Final gate/CI results
are recorded on the PR against its HEAD.
