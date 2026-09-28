# MOA IDLE registered v3 pilot

## Alpha Pilot Production approval — 2026-09-28

The user approved registered Breath v3 + measured Blink v3 as the **MOA Stage1 IDLE Production Animation**, with these Alpha Pilot defaults:

| Setting | Approved default |
|---|---|
| Breathing | 4 frames × 450ms = **1800ms per cycle** |
| Blink | 3 frames × **90ms per frame**, non-looping |
| Blink interval | **3000–7000ms randomized**, scheduled at IDLE entry and after each blink returns |

This is Alpha Pilot approval; later visual polish may tune timing/artwork through a future reviewed change. It does not approve other animation states or claim that every future visual concern is resolved. After final-HEAD Release Gate and CI pass, PR #46 is Ready for Review; no automatic merge.

| Animation | Final delivery state |
|---|---|
| MOA Stage1 IDLE (BREATH + occasional BLINK) | **PRODUCTION**; existing registry value `IDLE_PRODUCTION` |
| MOA MOVE | **NOT_SUPPLIED**; own-base fallback |
| MOA REACT | **NOT_SUPPLIED**; own-base fallback |
| PIP animation | **NOT_SUPPLIED**; own-base fallback |

No runtime status rename is needed: `pilotDefinition('moa',1)` already returns `IDLE_PRODUCTION`, and `PilotAssets.load` permits only IDLE/BLINK for that status. PIP remains `NOT_SUPPLIED`. Canonical manifest and generated registry already contain the approved timings. The legacy six-frame `idle` metadata is not the selected MOA pilot sequence.

Current asset/production evidence: [measured Blink v3](evidence/moa-blink-v3/README.md). Historical v1/v2 failures and prior candidate reports remain immutable observations; their pending-review wording records the state at capture time and is superseded for approval by this section. The earlier facing-reversal excursion is not claimed fixed by this approval.

The approved registered Breath v3 (four PNGs) and measured Blink v3 (three PNGs) are copied byte-for-byte to the existing zero-based asset convention: `breath_01..04` → `breath/breath_00..03`, `blink_01..03` → `blink/blink_00..02`. Base PNG and previous six idle PNGs remain unchanged. The previous `idle` clip is retained for historical/legacy contract compatibility; the MOA pilot explicitly selects `breath` for IDLE. MOVE/REACT/PIP remain NOT_SUPPLIED.

Canonical stage01 manifest declares both clips and `idleSequences`. The existing generator projects it to the static TS registry. No runtime manifest request, new asset engine, dependency or CSP change is needed. Original delivery manifest and hashes are evidence, not a second runtime metadata source.

`IdleSequencer` consumes existing shared clock timestamps. A renderer-local seeded PRNG receives one crypto entropy seed; unit tests inject a repeatable seed or random sequence. It has no timer/RAF/polling ownership. At IDLE entry it schedules a delay uniformly in [3000,7000]ms. At the deadline BLINK plays three 90ms frames, returns to BREATH frame01, and schedules a fresh delay after completion. Start-to-start intervals therefore include the blink duration. Blink can interrupt a breathing cycle; it is not tied to each cycle. Existing bounded frame-phase integration handles suspended WebViews without replaying a backlog of blinks.

The existing state resolver takes priority: REACT or MOVE interrupts the idle sequencer; suppression for battle/evolution/drag/sleep also cancels it. Unsupplied or failed sequence uses the character's own base. Cleanup resets scheduling and unsubscribes from the same shared clock. Reduced Motion conservatively preserves the previous static frame contract: breath frame01, no blink; disabling it schedules a new interval.

A fixed 5-second loop or one blink per breath cycle was rejected because it would violate occasional randomized scheduling. Independent timers or character RAFs were rejected because the shared clock already provides lifecycle-safe timestamps.

Validation includes source-byte/decoded-alpha checks, seeded scheduling and cancellation tests, atomic clip decode/fallback, existing clock StrictMode/leak tests, unchanged CSP/inventory checks, full release regression and actual release WKWebView capture. Native GUI capture uses existing QA instrumentation only; it neither patches CSP nor substitutes an HTML preview.
