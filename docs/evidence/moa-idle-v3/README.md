> Historical initial v3 blink artwork. See [Blink v2 replacement evidence](../moa-blink-v2/README.md) for the current assets and failed closed-eyes acceptance.

# MOA registered v3 — actual production playback

PR #46 remains **Draft**. No merge, final timing selection, or automatic visual approval.

[Watch the actual release-app recording](production-v3-playback.mp4) (19.923 seconds). Full local evidence, original ScreenCaptureKit PNG buffers, release `.app` and logs are retained at `/Users/jinseongdae/Documents/LUMA QA/moa-idle-v3/`. The committed MP4 uses actual capture PTS, 60fps resampling and 3× nearest enlargement for review; source assets are unchanged. This is WKWebView production CharacterRenderer, not an HTML mock.

## Results

| Check | Result |
|---|---|
| Breath / Blink assets | PASS: 4 + 3 source PNGs, byte-identical to ZIP, SHA256 and 256×256 RGBA transparency validated |
| Registration | PASS: decoded source center-X / bottom deltas 0px; breath04 == breath01 bytes |
| Breath playback | PASS: 01→02→03→04, eight complete observed cycles 1792.93–1812.92ms |
| Blink playback | PASS: 3 events, each 01→02→03 then BREATH01; zero sequence-order errors |
| Blink scheduling / RNG | PASS: pure shared-clock scheduling, injected deterministic RNG tests; runtime seed from crypto |
| Priority / Lifecycle | PASS automated: MOVE/REACT/suppression cancels idle; cleanup reset; fresh IDLE reschedules |
| Reduced Motion | PASS automated: static BREATH01, blink suspended; no policy change |
| Static Registry / Shared RAF | PASS: canonical manifest → existing generated TS module; existing clock source byte-unchanged |
| Production CSP / Network | PASS: unchanged; manifest attempts 0, XHR attempts 0, CSP violations 0 (2 existing IPC fetches) |
| Actual `.app` / GUI evidence | PASS for sequence/geometry: 55 complete ScreenCaptureKit buffers, 1632 AX samples within video |
| Focus / Single Instance | PASS native observation: no app activation/key window, no LUMA foreground; three secondary launches exit without World/panels |
| Release Gate | PASS `AUTOMATED_READY`; 18 checks including 40 asset tests, content/behavior/presentation, Rust, fmt/clippy/Tao, frontend, isolated Java/PostgreSQL persistence/failure regression |
| Human visual gate | **MANUAL_VISUAL_REVIEW**; breathing strength, blink naturalness, overall liveliness and identity consistency |

Blink return→next-start intervals were **3166.91ms**, **6033.40ms**. Start→start intervals were 3449.97ms and 6319.97ms (include the preceding blink). Three blink durations were approximately 283.06 / 286.58 / 276.09ms; shared-clock and AX sampling introduce frame-level quantization around the 270ms candidate. No fixed 5-second loop. The runtime recording uses production entropy, while reproducibility is tested with seed 46 and injected RNG; no alternate QA scheduling or CSP bundle was used.

Actual rendered center drift **0 capture px / 0pt**, bottom drift **0 capture px / 0pt** across all distinct recorded images, including blink transitions and breath04→01. No panel clipping. Panel fixed at `(1450,1025,96,104)`pt; image fixed at `(1457,1047,82,82)`pt. Pixel analysis uses nonblack RGB >40 below y60 to exclude the evolution button in the 192×208 capture; this measures silhouette registration, not perceptual liveliness. Breathing changes top geometry intentionally; canvas size remains fixed. AX labels disambiguate byte-identical frames.

**Visible artwork concern:** supplied blink02 still shows open eyes and a horizontal cut/seam around the upper head/leaves. This is visible in [actual production frame](actual-blink-frame02.png) and the source. Its exact bytes are preserved. Playback PASS does not approve this as a natural blink or consistent artwork. Human review remains required; no deformation/recolor/crop was added.

First capture had zero internal sprite drift and valid sequence order but transient panel-coordinate changes and one delayed cycle; it failed the panel-stability acceptance. Its report is retained in `first-panel-unstable.json`, with full failed-trial capture at the durable local `first-panel-unstable/` directory. No production code changed between trials. A second unchanged-app observation is the passing recording linked above; cause of the first system-coordinate excursion is not established.

Full interactive typing, movement/evolution GUI sweeps and soak were **NOT_RUN** in this v3 capture session; automated regression covers those code paths, and native nonactivation/single-instance observations are reported separately. The app/backend/isolated PostgreSQL were stopped, and PID/ports verified absent afterward.

## Evidence and reproduction

- `asset-validation.json`, `source-manifest.json`: byte identity and delivery contract.
- `playback-analysis.json`, `frame-trace.jsonl`, `runtime-trace.jsonl`, `capture-timestamps.json`: sequence timing, pixels, native geometry and document-start request observer.
- `unchanged-contracts.json`: before/after hashes for CSP/config, clock, loader, runtime inventory, base PNG and release binary.
- `release-result.json`: full gate ran against the dirty implementation tree based on d127c57, before committing evidence; later CI validates the committed HEAD.
- `focus-single-instance.json`: actual native primary/secondary observations.

Build with `npm run tauri build -- --bundles app`; use existing `run.py --keep-running --capture-only --metadata-audit`, then `capture_idle_sequences.py ROOT --recorder RECORD_WINDOW_BINARY` and `analyze_idle_sequences.py ROOT`. Native capture and AX tracing are QA-only processes. Runtime artwork/timing metadata remain canonical stage01 manifest data. Legacy v2 idle PNGs are retained but not selected by the v3 pilot.
