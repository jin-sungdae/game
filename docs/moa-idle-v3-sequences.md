# MOA IDLE registered v3 pilot

PR #46 remains Draft. Breathing strength, blink naturalness and overall liveliness require human visual review; 1800ms is a candidate, not a final production timing approval.

The supplied seven PNGs are copied byte-for-byte to the existing zero-based asset convention: `breath_01..04` → `breath/breath_00..03`, `blink_01..03` → `blink/blink_00..02`. Base PNG and previous six idle PNGs remain unchanged. The previous `idle` clip is retained for historical/legacy contract compatibility; the MOA pilot explicitly selects `breath` for IDLE. MOVE/REACT/PIP remain NOT_SUPPLIED.

Canonical stage01 manifest declares both clips and `idleSequences`. The existing generator projects it to the static TS registry. No runtime manifest request, new asset engine, dependency or CSP change is needed. Original delivery manifest and hashes are evidence, not a second runtime metadata source.

`IdleSequencer` consumes existing shared clock timestamps. A renderer-local seeded PRNG receives one crypto entropy seed; unit tests inject a repeatable seed or random sequence. It has no timer/RAF/polling ownership. At IDLE entry it schedules a delay uniformly in [3000,7000]ms. At the deadline BLINK plays three 90ms frames, returns to BREATH frame01, and schedules a fresh delay after completion. Start-to-start intervals therefore include the blink duration. Blink can interrupt a breathing cycle; it is not tied to each cycle. Existing bounded frame-phase integration handles suspended WebViews without replaying a backlog of blinks.

The existing state resolver takes priority: REACT or MOVE interrupts the idle sequencer; suppression for battle/evolution/drag/sleep also cancels it. Unsupplied or failed sequence uses the character's own base. Cleanup resets scheduling and unsubscribes from the same shared clock. Reduced Motion conservatively preserves the previous static frame contract: breath frame01, no blink; disabling it schedules a new interval.

A fixed 5-second loop or one blink per breath cycle was rejected because it would violate occasional randomized scheduling. Independent timers or character RAFs were rejected because the shared clock already provides lifecycle-safe timestamps.

Validation includes source-byte/decoded-alpha checks, seeded scheduling and cancellation tests, atomic clip decode/fallback, existing clock StrictMode/leak tests, unchanged CSP/inventory checks, full release regression and actual release WKWebView capture. Native GUI capture uses existing QA instrumentation only; it neither patches CSP nor substitutes an HTML preview.
