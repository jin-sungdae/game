# MOA IDLE registered artwork v2 — actual production verification

**Registration acceptance PASS. Visual vitality/breathing remains MANUAL_VISUAL_REVIEW. No timing selected; PR #46 stays Draft.** The previous six misregistered assets are rejected historical evidence, not the current delivery.

## Approved byte replacement

`moa_idle_registered_v2.zip` is the sole source. Its six PNGs are copied without generation, resize, crop, recolor or re-encoding. Source01…06 maps to the existing runtime00…05 filenames. The original [manifest](source-manifest.json) is preserved separately from runtime clip metadata. [Repository validation](asset-validation.json) checks actual file SHA-256,256×256 RGBA transparency and decoded alpha bounds against the manifest. Repository test rechecks the same values. Existing MOA stage01/base.png is unchanged.

Decoded source/repository alpha bounds use exclusive right/bottom coordinates, matching the delivery manifest. Center X=(left+right)/2 is129px in all six; bottom is248px in all six. Maximum center-X delta=**0px**, bottom delta=**0px**. Frame06 and01 are **byte-identical**;02 and04 are also intentionally identical. This is a six-state animation sequence with repeated images, not six unique bitmaps. Geometry derives from the supplied master-based artwork; no additional deformation was applied.

## Four actual production recordings

| Cycle | Actual capture span | Median observed frame interval | Horizontal hopping | Bottom hopping | Order / panel / clipping | Recording |
|---|---:|---:|---:|---:|---|---|
|600ms|8.077s|99.26ms|0px / **0pt**|0px / **0pt**|PASS / fixed / none|[600ms](moa-idle-600ms.mp4)|
|900ms|8.040s|150.11ms|0px / **0pt**|0px / **0pt**|PASS / fixed / none|[900ms](moa-idle-900ms.mp4)|
|1500ms|8.085s|249.05ms|0px / **0pt**|0px / **0pt**|PASS / fixed / none|[1500ms](moa-idle-1500ms.mp4)|
|1800ms|7.995s|301.50ms|0px / **0pt**|0px / **0pt**|PASS / fixed / none|[1800ms](moa-idle-1800ms.mp4)|

These are ScreenCaptureKit recordings of real release Tauri `.app` / WKWebView / CharacterRenderer panels, not HTML mocks or source-frame reconstructions. Same96×104pt panel,82×82pt image canvas, isolated backend and pointer placement protocol. Only IDLE frameDuration differs among the four builds. The existing static registry is regenerated for each candidate then restored together with the original manifest. All builds use the **unchanged production CSP**, without the old QA CSP exception. No playback or domain state is forced by QA code.

MP4s use actual native sample PTS intervals, resampled to60fps and enlarged3× only for review. PNG source assets remain unchanged. GitHub may require downloading the MP4 file to play it. Native captured PNGs and signed release candidate bundles are retained at `/Users/jinseongdae/Documents/LUMA QA/moa-idle-v2/`, not only in /tmp.

## Measurement method and findings

[Registration analysis](registration-analysis.json) and `*-capture-timestamps.json`, `*-frame-trace.jsonl`, `*-renderer-trace.jsonl` provide reproducible evidence. `scripts/gui_qa/analyze_registered_capture.py <root>` decodes every distinct captured bitmap to RGBA. It measures nonblack silhouette bounds (max RGB>40, below y60 to exclude the evolution button) in192×208 capture pixels at2× scale. This threshold-based screen metric is explicitly separate from exact source-alpha bounds. Source assets themselves are never edited by analysis.

The cached production img AX node is sampled approximately every10–13ms by an external QA helper. This adds no production RAF, timer or polling. High-rate labels prove01→02→03→04→05→06→01 even though06=01 and02=04 pixels cannot distinguish those states. Analysis restricts AX observations to the video capture interval;650–658 samples per candidate show all six frames, with no skipped/reordered transition. Observed06→01 counts are13/9/6/5 respectively. The first/last partial hold and OS capture/AX scheduling jitter are not used to approve final timing.

All observed panels remain x1584,y1025,width96,height104pt. Image origin remains x1591,y1047 with82×82pt size. Every distinct captured silhouette has the same center X and bottom within its recording, including the06→01 boundary: **horizontal hopping0pt, bottom hopping0pt**. No measured body silhouette touches the panel edge; no observed clipping. The previous approximately22.75pt horizontal hopping is absent under the same panel/renderer geometry. This is bounds/registration verification, not an anatomical-landmark tracker or a claim covering unobserved battle/evolution poses.

Frame06=01 source bytes plus unchanged panel/image bounds and zero per-recording silhouette drift establish a seamless positional boundary. Fine breathing intensity, liveliness and subjective comfort at600/900/1500/1800ms remain **MANUAL_VISUAL_REVIEW**. Do not enlarge deformation based on this result. Existing600ms runtime metadata is preserved as the preexisting value, not newly approved production timing;1500ms remains a candidate.

## Regression and unchanged contracts

[Unchanged contract hashes](unchanged-contracts.json) confirm byte-identical production CSP configuration, static generated registry after QA restoration, loader, shared RAF clock, network inventory and MOA base.png against5350853. Existing tests retain static lookup, no manifest fetch, unavailable MOVE/REACT/PIP, invalid/missing metadata/frame and own-base fallback coverage. No gameplay activation changes.

`npm run validate:alpha:release`: **AUTOMATED_READY / MANUAL_QA_REQUIRED**, all18 composed checks PASS. [Release result](release-result.json) includes frontend, animation/content, presentation,39 asset tests, policies, Rust/fmt/clippy, Tao, native harness compilation and isolated Java/PostgreSQL regression. Report correctly identifies the precommit working tree; pushed-HEAD CI is separate.

[Actual Focus / Single Instance result](focus-single-instance.json): the running signed production binary retained its primary window; three real secondary launches (two LaunchServices, one direct executable) exited0, were confirmed gone, and created no World or panel. Primary/secondary native audit showed0 activation/key-window events; an8s foreground observer never saw a LUMA PID become frontmost. This is **PASS for observed native focus and single-instance contracts**. A separate TextEdit typing trial was interrupted by the front-application guard and is **NOT_VERIFIED**, not silently converted to PASS. No focus restoration workaround was added.

## Environment failures retained, not hidden

- First high-rate trace could not find the lazily initialized AX image; retry now waits for tree availability before recording. The incomplete initial capture remains in `first-trace-initialization-failure/`; it is not counted as a passing comparison.
- First release gate failed on duplicate generated migration resources (`V1__game_schema 2.sql`, etc.) inside local server/build, not modified source migrations. [Duplicate-resource evidence](local-build-duplicate-resources.json) is retained. Gradle clean followed by a full gate rerun passed. No database schema/source change or validation bypass.
- The original native launch harness encountered LaunchServices-10810; codesign also reported local Finder/resource-fork metadata on the durable app copy. A `ditto --norsrc --noextattr` copy passed signature verification. Its executable hash exactly matches the recorded1800ms bundle (see unchanged-contracts.json). Direct launch and three-secondary protocol then passed. Failed harness reports remain in the durable evidence root. No app binary or artwork modification was used to recover the environment; /tmp holds only this verification copy, not the sole video/evidence.

Owned preview app/server/PostgreSQL sessions were stopped. All four videos and machine-readable measurements are committed to PR #46 for human review. Do not merge or mark Ready for Review automatically.
