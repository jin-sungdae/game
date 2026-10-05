# FLOATING Alpha Batch Expansion v1

Representative: PUFF. Consumers: PUFF, WISP, LUNET.

This batch supplies WISP/LUNET artwork to the existing FLOATING contract, not a new
profile pilot. `floatingConsumers` in `src/animation/pilot.ts` explicitly maps the
three consumers to the same `floatingProfile`. The unchanged CharacterRenderer calls
one unchanged `resolveFloating`; no consumer-specific resolver or timing exists.
Canonical local manifests generate `generated-manifests.ts`; no runtime manifest fetch.

| Sequence | Contract | Artwork per new consumer |
| --- | --- | --- |
| HOVER | Excursion inactive; 2000ms fixed cycle | 4 PNGs / 500ms |
| FLOAT | Active excursion + existing meaningful-motion threshold; 1200ms fixed cycle | 6 PNGs / 200ms |
| SETTLE | NOT_APPLICABLE; no trigger | Not supplied |

FLOAT persists through the slow apex while active, and returns to HOVER on completion
or cancel. PUFF retains its existing deterministic SETTLE asset coverage without a
production trigger. Registry SUPPLIED matches PUFF's existing delivery flag.

All 20 PNGs equal the approved ZIP bytes. Original delivery manifest is retained once
in `docs/evidence/floating-alpha-batch-v1/delivery-manifest.json`. Canonical manifests
contain runtime metadata only; the generated TS registry has no hand-maintained copy.
Both existing base PNGs are unchanged. WISP/LUNET source alpha center-X, center-Y and
bottom drift are each 0px, independently recomputed across all ten frames per identity.
Coordinates use exclusive alpha bounds, not visual judgments about artwork identity.

Native MovementController still owns world position, trajectory, target, excursion
and facing. TIMID avoidance is exercised for both consumers with active/completed
native telemetry and both horizontal facing directions. Existing tests retain
vertical-only facing. LUNET NIGHT eligibility and all content are unchanged.

Failed manifests/frames retain each consumer's own base fallback. Lifecycle suppression,
reduced-motion first-frame policy, shared clock, source-facing RIGHT and horizontal flip
are unchanged. Tests in `floating-batch.cjs` run the same resolver, static loader, frame
order, timing, transitions, lifecycle and failure cases for PUFF/WISP/LUNET. Native
consumer tests and asset mutation tests supplement the existing full regression.

Production TypeScript changes are limited to `pilot.ts` consumer registration and
`generated-manifests.ts` generated entries. Native changes are tests only. Preservation
hashes for renderer, resolver, clock, loader, CSP, movement, content and base PNGs are
in `docs/evidence/floating-alpha-batch-v1/summary.json`.

## GUI acceptance boundary

Both fresh common-harness preflights returned GUI_ENVIRONMENT_BLOCKED /
NO_SAFE_CANDIDATE after the manual-preparation countdown. No user windows were moved,
resized or closed. No placement bypass or debug entity was used. No production app
recording was claimed. Actual HOVER/FLOAT, direction/reversal, renderer drift,
clipping and actual cycle measurements remain NOT_VERIFIED / GUI_VISUAL_QA_DEFERRED.
Source registration and deterministic tests do not establish visual acceptance.

The batch may be AUTOMATED_ACCEPTED once the final release gate and CI pass, under
the user's explicit deferred-GUI policy. Keep the PR Draft for human review and never
merge automatically. Final gate/CI results are recorded on the PR against its HEAD.
