# MOA Blink v3 measured replacement

[Actual production recording — 25.856 seconds](production-v3-playback.mp4) · [BREATH still](actual-breath.png) · [BLINK02 still](actual-blink02.png).

Four actual BLINK01→02→03→BREATH events were observed in the release WKWebView. Facial eyes visibly close in BLINK02. The former head/leaf eyelid patches and horizontal seam are absent. This is the unchanged production renderer/CSP, not a mock. Timing stays1800ms breathing,90ms per blink frame, randomized3–7 second waits. Final timing/liveliness approval remains human review; PR #46 stays Draft, no merge.

| Check | Result |
|---|---|
| Blink v3 integrity | PASS: all3 PNGs exactly match ZIP bytes/SHA;256×256 RGBA/transparency;blink01==03 |
| Alpha / outside-safe RGB | PASS: every alpha byte matches production base;0 RGB pixel changes outside specified safe regions |
| Source registration | PASS: center129, bottom248, center/bottom deltas0px |
| Actual eye closure | PASS observed source pixels and actual renderer; open iris/highlight appearance replaced by closed curved eyelid lines in facial eye regions |
| Misplaced eyelids / horizontal seam removed | PASS observed in source and actual sequence; head/leaves outside safe regions exactly match base |
| Renderer center / bottom drift | PASS:0 capture px /0pt for both across this recording; panel and canvas fixed; no clipping |
| Breathing / Blink scheduling | PASS:11 complete observed breathing cycles,4 complete blink sequences; no order errors; unchanged runtime |
| Static registry / Shared RAF / CSP | PASS unchanged hashes; no manifest fetch, XHR or CSP violations;2 existing IPC fetches |
| Focus / Single Instance | PASS native observation:3 secondary launches exited without World/panels, no app activations/key windows/foreground takeover |
| Release Gate | PASS AUTOMATED_READY:18 checks including41 asset tests, animation/content/presentation, frontend, Rust/fmt/clippy/Tao, isolated Java/PostgreSQL |
| Human gate | MANUAL_VISUAL_REVIEW: breathing strength, blink naturalness, overall liveliness, final timing choice |

## Pixel and timing evidence

Measured safe rectangles are inclusive: LEFT x190..213,y136..165; RIGHT x228..238,y136..159. Each supplied frame changes638 RGB pixels, all inside those regions. Original base and all four breathing assets remain byte-identical to prior HEAD. Pixel validation reads actual repository PNGs, not manifest assertions alone.

With explicitly defined `max(R,G,B)<100` within measured eye bounds, base dark pixels are278/70 and blink02 is61/22. Left dark vertical span changes from y138..162 to155..160; right from138..156 to152..157. Combined with direct pixel/renderer inspection this supports closed eyes rather than merely displaced dark pixels. Manifest's base_dark_eye_pixels288/71 uses an unspecified criterion; our reproducible criterion and exact counts are reported separately, not forced to match. Half-close/open frames have77/27 dark pixels; all original bytes are preserved. `eye-pixel-analysis.json` includes row counts.

Actual breathing cycle trace (ms):1830.75,1836.16,1770.52,1801.91,1802.33,1805.10,1800.32,1799.99,1801.26,1798.61,1804.12. These are AX-observed wall-clock cycles (sampling quantization); canonical candidate remains1800ms.

Blink completion→next-start waits (ms):6219.91,5817.55,6852.18. Start→start intervals:6496.60,6096.63,7142.40 (include the preceding blink). No fixed5-second period, no QA timing/seed override.70 complete ScreenCaptureKit buffers and2110 high-rate AX samples were captured. Source-identical frame01/03 are distinguished by AX labels.

Panel bounds:(1584,1025,96,104)pt. Image:(1591,1047,82,82)pt. Horizontal and bottom hopping0pt, no clipping. This recording kept one facing; it does not claim to fix or revalidate the earlier1.5pt facing-reversal excursion. Position/facing/runtime code is unchanged. Analyzer passed without modifying its zero-center assertion.

## Evidence scope

Full typing/movement/evolution GUI sweeps and soak NOT_RUN this session; existing automated regressions and native focus/single-instance observation are separate. Code-sign verification initially rejected Finder/resource-fork metadata on the durable Documents copy; a metadata-free copy verified with identical executable SHA (see bundle-verification.json). Actual release app launched and was captured successfully; no CSP/security/runtime changes were made.

Video uses actual native PTS,60fps resampling and3× nearest enlargement for review only. All raw buffers, release app and logs are retained at `/Users/jinseongdae/Documents/LUMA QA/moa-blink-v3/`. No source PNG was generated/resized/cropped/recolored. QA app/backend/isolated PostgreSQL were stopped and listeners verified absent.

- `asset-validation.json`, `source-manifest.json`, `eye-pixel-analysis.json`: original bytes, all-pixel checks, eye analysis.
- `playback-analysis.json`, `capture-timestamps.json`, `frame-trace.jsonl`, `runtime-trace.jsonl`: actual capture and transitions.
- `unchanged-contracts.json`: production metadata/runtime/CSP/base/breath hashes before/after.
- `release-result.json`: full gate against implementation tree based on ae37865 before evidence commit; latest committed HEAD also receives CI.
- `focus-single-instance.json`, `bundle-verification.json`: native audit/build evidence.
