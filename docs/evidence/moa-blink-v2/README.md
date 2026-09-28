# MOA Blink v2 replacement — visual acceptance FAIL

The three supplied PNGs are copied byte-for-byte. **Actual facial eyes remain open in blink02**: the new closed-eyelid drawings are placed above the face on the head/leaves. Do not approve the artwork. PR #46 stays Draft; no timing approval or merge.

[Actual production video, 25.878 seconds](production-v3-playback.mp4) · [actual blink02](actual-blink-02.png). Raw buffers, two recordings, release `.app`, logs and traces remain at `/Users/jinseongdae/Documents/LUMA QA/moa-blink-v2/`. The video filename comes from the existing v3 sequence capture helper; it contains the new Blink v2 assets. Source PNGs are not resized/recolored; the review video is 3× nearest enlargement of actual ScreenCaptureKit buffers using captured PTS.

| Check | Result |
|---|---|
| Blink Asset Integrity | PASS: 3 ZIP/repository byte matches; hashes, 256×256 RGBA/transparency |
| Blink02 Closed Eyes | **FAIL**: actual facial eyes remain open; eyelid graphics are misplaced above them |
| Artwork Seam | PASS for removal of the previous horizontal cut across head/leaves; **new misplaced eyelid patches remain a visual defect** |
| Source Registration | PASS: all 65,536 alpha bytes match production base; center/bottom drift 0px; blink01==03 bytes |
| Renderer Registration | **FAIL for whole-recording zero-horizontal-drift criterion**: center excursion 3 capture px / 1.5pt during facing reversal; bottom 0px/0pt |
| Breathing | PASS: original 4 PNGs byte-unchanged; candidate 1800ms untouched; ten complete cycles 1794.90–1809.63ms |
| Blink Scheduling | PASS: 6 complete 01→02→03→BREATH returns, zero order errors; unchanged 90ms frames and randomized 3–7 second waits |
| Actual Production App | PASS: real release WKWebView, unchanged production CSP, no mock or CSP exception |
| GUI Evidence | Recording delivered; visual and whole-recording geometry acceptance **FAIL** as above |
| Focus / Single Instance | PASS native observation: three secondaries exit without World/panels; no LUMA foreground, activations or key windows |
| Static Registry / Shared RAF / Lifecycle / Priority | PASS: production source hashes unchanged; existing regressions retained |
| CSP / Network | PASS: config unchanged; zero manifest attempts, XHR attempts and CSP violations; existing 2 IPC fetches only |
| Release Gate | PASS: AUTOMATED_READY; all 18 checks, including 41 asset tests and Rust/Java/PostgreSQL/frontend/fmt/clippy/Tao regressions |

## Quantitative evidence

The original face-eye region `[190,130,243,171)` is pixel-identical to the base in **all three source images**. Blink02 changes are confined to `[66,82,181,129)` (3244 pixels), above/left of the actual eyes. Thus alpha registration PASS cannot imply closed eyes. `asset-validation.json` records exact change bounds and byte/alpha comparisons. The three actual renderer stills supplement the continuous video; visual findings are not inferred from screenshots alone.

Observed blink completion→next-start waits: **3437.32, 4955.79, 3815.52, 4477.42, 5525.04ms**. Start→start: **3704.84, 5234.56, 4097.16, 4770.78, 5813.06ms**. No deterministic production override was used; the unchanged scheduler produced six blinks during capture.

Full breathing cycle trace (ms): **1801.96, 1809.63, 1796.46, 1803.91, 1800.73, 1799.94, 1794.90, 1795.00, 1801.01, 1801.00**. These are native AX observation times and include sample quantization, not a changed timing contract.

Panel fixed at **(1584,1025,96,104)pt**; image fixed at **(1591,1047,82,82)pt**. No clipping. Actual image buffers contain both left-facing and right-facing sprites. Silhouette center changes from 94 to 97 capture px with facing; each center group is stable across the different animation images and bottom stays at201. We do not hide this excursion or label the entire recording 0pt. No position/facing/runtime code was changed to force a passing result. The first 25.860-second trial also had a facing reversal and 1.5pt center excursion (`first-facing-change.json`); full first-trial video is retained locally. No additional capture retries were used.

The automated analyzer's whole-recording zero-center assertion **fails**, preserved in local `analysis.log`; it was not weakened. Registration source tests and the full release gate pass independently. Breathing strength, blink naturalness and overall liveliness remain **MANUAL_VISUAL_REVIEW**, with the closed-eyes defect explicitly failed rather than deferred as a taste judgment.

Full typing/movement/evolution GUI sweeps and soak were NOT_RUN in this replacement session. Existing automated regression plus native focus/single-instance observation are scoped separately. QA app/backend/PostgreSQL were stopped afterward.

## Files and unchanged contracts

- `source-manifest.json`, `asset-validation.json`: supplied contract and exact bytes/alpha/change regions.
- `playback-analysis.json`, `frame-trace.jsonl`, `runtime-trace.jsonl`, `capture-timestamps.json`: full measured sequence, native geometry and network trace.
- `unchanged-contracts.json`: before/after hashes for breath PNGs, base, canonical manifest, generated registry, animator/scheduler/renderer, clock, CSP and runtime inventory.
- `release-result.json`: full gate on implementation tree based on a1d75d1 before evidence commit; committed HEAD also receives CI.
- `focus-single-instance.json`: native audit.

Only the three blink PNGs change in production. Tests now validate retained v3 breath separately from replacement blink. QA helper accepts `--seconds 26` and places the pointer inside the screen; production timing and scheduling are untouched.
