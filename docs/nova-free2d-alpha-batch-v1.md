# NOVA FREE_2D Alpha Batch Expansion v1

Representative: EMBER. Alpha Production consumers: EMBER and NOVA.
The user approved NOVA on 2026-10-07 as a consumer of the existing Production
FREE_2D profile: FLICKER = PRODUCTION, FLOW = PRODUCTION,
INTENSE = NOT_APPLICABLE. This approval is documentation-only; runtime, assets,
timing and the shared resolver remain unchanged.

The consumer table in `src/animation/pilot.ts` resolves identity-specific paths into
the unchanged FREE_2D resolver and loader. Generated static metadata has no runtime
manifest fetch. FLICKER5 = 360ms/frame / 1800ms; FLOW6 = 160ms/frame / 960ms fixed 1x.
Enter FLOW at speed >=8pt/s; remain while >3; stop/completion/cancel returns FLICKER.
INTENSE is NOT_APPLICABLE, with no NOVA asset/trigger or new high-speed threshold.

Native MovementController owns 2D outbound movement, descent, completion/cancel,
world X/Y, velocity, target, trajectory and facing. CURIOUS approach/ambient decisions
remain native-owned. Horizontal facing follows existing threshold; vertical-only
retains facing. Lifecycle/suppression and reduced motion remain unchanged; animation
cannot alter native movement. Invalid/missing animation uses NOVA own base only.

11 supplied PNGs and the original delivery manifest are byte-preserved. NOVA base
and every EMBER asset remain unchanged. Source center (129.5,147.5), bottom246;
center-X/Y/bottom variation 0px. These are source measurements, not renderer proof.

## Coverage and validation

`tests/animation/alpha-coverage.cjs` joins content, asset and animation registries,
loads all required clips from actual static metadata/PNG files, verifies profile
mapping, identity-specific base paths and fail-closed missing-frame behavior.
Result: Active Alpha 15/15 COMPLETE (100%), NOT_SUPPLIED 0. Provisional15 excluded
and disabled; no content activation. COMPLETE means required production-state asset
coverage, not universal human visual approval. The user approved this repository
coverage gate and NOVA Alpha Production consumer status; GUI acceptance remains
deferred and no NOT_VERIFIED GUI item becomes PASS.

| Profile | Consumers |
| --- | --- |
| GROUND | PIP, MOSSY, PEBB, TIKKI |
| JUMP | MELLO, BUBU |
| FLYING | CHIRP |
| FLOATING | PUFF, WISP, LUNET |
| STATIC | MIMI |
| EDGE | SHADE, NOCT |
| FREE_2D | EMBER, NOVA |

FREE_2D tests exercise both consumers through shared hysteresis, horizontal/vertical/
diagonal vectors, stop/completion, fixed cadence, suppression, reduced motion and
own-base fallback. Native regression includes NOVA facing/accepted motion, CURIOUS
approach/pause and existing FREE_2D vector/descent/completion/cancel tests.
Final clean-HEAD full Release Gate and CI results are recorded on the Draft PR.

Common #54 preflight: GUI_ENVIRONMENT_BLOCKED / NO_SAFE_CANDIDATE, no user-window
mutations. Actual NOVA, transitions/vectors, facing, renderer drift/bounds/clipping,
measured cycles and recording remain NOT_VERIFIED / GUI_VISUAL_QA_DEFERRED.
AUTOMATED_ACCEPTED is separate from GUI acceptance. See the consolidated sweep.

Evidence: `evidence/nova-free2d-alpha-v1/` contains delivery SHA metadata, decoded
source bounds, preservation hashes, registry coverage and sanitized preflight.

## Scope freeze

Active Alpha Animation scope is frozen following this approval. No new animation
profile, secondary animation, state, engine, resolver, threshold or timing system
is introduced. Next: Monster Visual Regression Sweep -> Alpha Integration QA ->
Release Candidate. The 15-species sweep backlog remains open; the sweep itself is
not performed here. Provisional15 remain excluded and are not activated.
