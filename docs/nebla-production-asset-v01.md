# NEBLA Stage3 Production Asset Delivery & Vertical Slice v0.1

Base origin/main `95fcacf` (Progression v0.2 merged). Branch `feature/nebla-production-asset-v01`. No production gameplay, renderer, native panel, movement, formula, migration or dependency change.

## Approved asset and registry

Canonical identity `moa/stage03`; destination `public/assets/creatures/moa/stage03/base.png`. Source was copied byte-for-byte, never regenerated/cropped/resized/recolored. Both SHA-256 values:

`32b21b0b2f0b0c3c2e9172f4f797431e3be369eae93142c2482ecccf6d0db588`

256×256, 8-bit PNG RGBA, transparent; inclusive nonzero alpha bounds x30–232/y24–250. Registry declares Stage3 `PRODUCTION_BASE` and separately `stageAnimationStatus=NOT_SUPPLIED`. No animation/manifest is invented. Validator preserves the previous missing-animation contract using explicit animation status, while validating the delivered PNG. MOA/MOKORI base paths remain unchanged.

Existing priority remains animation → same-stage base → diagnostic. A missing Stage3 animation resolves to the delivered Stage3 PNG. Failed Stage3 base loads still use diagnostic, never MOKORI/MOA images. Server EVOLVED acknowledgement precedes identity changes; existing Glow retains previous MOKORI, Reveal displays NEBLA. No renderer code changed.

## Measured bounds and facing

Measurements use the actual production React CompanionVisual/BaseSprite and CSS hierarchy, driven by serialized snapshots from compiled Desktop World. The browser measurement harness has the same96×104 logical-pixel panel size from Rust MOA_SIZE. Static measurements disable CSS animation only in the test harness. They are browser-layout evidence, not a native NSPanel screenshot audit.

| Measurement | RIGHT | LEFT |
|---|---|---|
| Source image |256×256|256×256|
| Rendered canvas (x,y,w,h)|7,22,82,82|7,22,82,82|
| Bottom-center anchor|48,104|48,104|
| Nonzero alpha bounds, exclusive max|16.609375,29.6875 →81.6328125,102.3984375|14.3671875,29.6875 →79.390625,102.3984375|
| Visible size|65.0234375×72.7109375|65.0234375×72.7109375|
| Transform|scaleX(1)|scaleX(-1)|

No clipping in either direction, no panel resize or anchor translation. Source-facing is the existing RIGHT contract, shared by all companions. The visible drawing is asymmetric, so flipping mirrors its alpha box: the left edge shifts2.2421875pt while the canvas/position/bottom anchor stay identical. Claiming identical visible x extents would be incorrect. No per-NEBLA centering or facing system was added. Native interactive motion/drag/focus and animated extreme-frame audit remain MANUAL_REQUIRED.

## Live server → compiled World → production renderer

Fresh isolated PostgreSQL database `luma_nebla_live_test` on55489, existing test-only LiveValidationServer on18109. Fixed RNG selects existing PIP Level1; production rewards/weights/personality formulas are unchanged. **No direct UPDATE of companion progression fields is used in this live trace.**

`live_nebla_natural_production_trace` runs75 real Encounter/Battle/Attack victories through the existing HTTP client and compiled World. It evolves MOA→MOKORI at15 wins, records MOKORI Lv5/EXP1480 at74 wins, then a real75th victory gives Lv6/EXP1500/Bond75. A real Shop purchase and Inventory use of Bond Berry changes Bond75→76. Server eligibility is AVAILABLE, and the explicit evolution request preserves MOKORI before acknowledgement. EVOLVED produces Glow(previous Stage2) then Reveal(Stage3). Level6/EXP1500/Bond76/Gold720 are preserved by evolution (750 victory gold minus30 Berry price).

Stop Spring PID52260; restart a new Spring process against the same DB and execute the live test in a new process/fresh World. Bootstrap restores NEBLA Stage3/Level6/EXP1500/Bond76 with idle presentation. The exact exported before-ack/Glow/Reveal/restored World snapshots were loaded into the production renderer harness. UI observations confirmed:

- request-before-ack and Glow: actual MOKORI image;
- Reveal: actual `/assets/creatures/moa/stage03/base.png`, no asset-pending diagnostic;
- restored: same actual NEBLA PNG after Spring/fresh World restart;
- browser image decode confirms natural256×256 and measured alpha bounds above.

### Important requested-fixture incompatibility

Under unchanged production rules a victory grants at most60 EXP and always+1 Bond. Fresh progression to1500 EXP therefore requires at least25 victories and Bond>=25. **Natural Lv6/Bond11 is unreachable** with these rules, and no authorized Bond-decrease flow exists. The request also forbids direct progression UPDATE and reward changes. Therefore the exact requested Lv6/Bond11→Berry→Bond12 *live fixture* was NOT_RUN; it must not be reported as a passing natural path.

The new `NeblaEligibilityBoundaryTest` checks the exact11/12 boundary with immutable server-domain values and no database mutation. Existing full Inventory/Evolution regression remains intact. The natural live trace verifies the real Berry+1 flow75→76, not a fabricated11→12 claim. A clarification was requested; absent an explicit fixture exception, the no-UPDATE constraint was preserved. A separately authorized initial save fixture would be required for that exact isolated scenario.

## Reproduction and regression

Create a fresh dedicated loopback `_test` PostgreSQL database. Start `./server/gradlew -p server liveValidation` with explicit LUMA_DB_URL/LUMA_DB_USER/LUMA_SERVER_PORT and no batch RNG flags. Run:

```
LUMA_GAME_SERVER_URL=http://127.0.0.1:18109 \
LUMA_NEBLA_MODE=natural \
LUMA_NEBLA_TRACE_PATH="$PWD/tests/live/nebla-natural.json" \
cargo test --manifest-path src-tauri/Cargo.toml live_nebla_natural_production_trace -- --ignored --nocapture
```

Actually stop/start Spring on that same DB; repeat with `LUMA_NEBLA_MODE=restored` and trace path `tests/live/nebla-restored.json`. Serve Vite and open `/tests/live/nebla.html`; select each trace frame, RIGHT/LEFT and Measure. The harness renders real components from trace data, not invented browser state. JSON outputs are local ignored files; no production/UI hooks are introduced. The harness is typechecked by the presentation test script.

AUTOMATED PASS: Java/PostgreSQL185 tests; Rust142 passed/14 explicitly ignored (the new live fixture separately executed twice); Asset30 tests; Animation/Content/Base/Presentation, automation9, npm build, bootJar, clippy, formatting, diff check and Tao integrity. Full regression includes Progression, Stage1/2/3, Inventory, Battle Personality, Monster Behavior, Discovery, Rare Spawn Presentation and all15 Monster gameplay. Optional asset validation permits the existing undelivered animations; it is not a claim of delivered NEBLA animation. Original and repository SHA rechecked after testing.

Changed files: approved PNG; companions.json; validator animation-status lookup; existing base/presentation assertions; new PNG/alpha/bounds tests; new server boundary test; compiled World live trace; browser renderer harness and its typecheck; this document. Parallel overlap: companion registry, asset validator and evolution test module only. No production Rust/Java domain logic changes, no Monster/Companion pipeline merge, no new movement engine.

## Review boundary

READY_FOR_HUMAN_REVIEW after CI; never auto merge. Exact Bond11 live fixture remains NOT_RUN for the incompatibility above. Actual native NSPanel foreground typing, click/drag ownership, Never Steal Focus and animated motion must be manually checked; unchanged code plus regression/native compile is not proof of those manual interactions. NEBLA animation is still NOT_SUPPLIED. Future asset loss correctly restores diagnostic fallback; successful production delivery does not remove that safety path.
