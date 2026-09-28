# MOA IDLE: actual production renderer timing review

Historical artwork evidence: the rejected v1 source has now been replaced by registered v2. See [v2 actual production measurements](../moa-idle-v2/README.md). Original records below remain unchanged in meaning.

**HUMAN_REVIEW_REQUIRED — visual acceptance FAIL; no timing selected.**

The historical QA-CSP recordings below are retained unchanged. The approved Option B follow-up now demonstrates playback with unchanged production CSP: [static registry verification](../moa-static-registry/README.md).

These are continuous ScreenCaptureKit recordings of the actual Tauri release `.app` / WKWebView / `CharacterRenderer`, not a browser mock, source-frame slideshow, or reconstructed animation. Each recording uses the same six supplied PNG byte streams, shared animation clock, native 96×104pt MOA panel, isolated backend, pointer proximity, and 82×82pt image canvas. The native idle/looking presentation resolves to renderer IDLE throughout the observed image samples. Facing is LEFT in all four recordings (the existing renderer mirrors RIGHT-source art).

## Watch the four candidates

| Candidate | Actual capture span | Captured changed frames | Observed 06→01 transitions | Median frame interval | Video |
|---|---:|---:|---:|---:|---|
| 600ms | 8.017s | 82 | 13 | 101.8ms | [600ms MP4](moa-idle-600ms.mp4) |
| 900ms | 8.069s | 55 | 9 | 148.7ms | [900ms MP4](moa-idle-900ms.mp4) |
| 1500ms | 7.996s | 33 | 5 | 247.8ms | [1500ms MP4](moa-idle-1500ms.mp4) |
| 1800ms | 7.810s | 28 | 5 | 300.7ms | [1800ms MP4](moa-idle-1800ms.mp4) |

ScreenCaptureKit requested 60fps for 8s; static/idle buffers are omitted by the recorder, so the complete buffers above predominantly represent frame changes. MP4s preserve their actual PTS intervals, encoded at60fps and enlarged3× for readability. Capture starts mid-cycle; the first hold is partial. No source art was shifted, rescaled, or regenerated. MP4 upscaling affects review footage only. GitHub may require downloading the MP4 via its file page.

## Important production configuration boundary

A release build with the **unchanged baseline CSP displays own-base fallback**: `AssetLoader` fetches the local manifest, but baseline `connect-src` omits `'self'`. For these four QA release bundles only, the build command adds `'self'` to `connect-src`, permitting same-origin bundled manifest reads. With that single QA configuration difference, all six animation frames were observed. The checked-in `src-tauri/tauri.conf.json`, network inventory, native focus policy and shared clock are unchanged. This is actual production renderer evidence, **not certification that the unmodified default bundle plays the clip**. Any permanent CSP change requires separate human review. Baseline fallback footage and build logs are retained locally.

## Findings

| Check | Result | Evidence / limit |
|---|---|---|
| Frame order 01→06 | PASS | All four pixel sequences follow1,2,3,4,5,6 cyclically. Six exact PNG capture hashes recur across all candidates; AX labels identify each hash. |
| Loop continuity | PASS for scheduling | No missing/out-of-order frame transition in captured sequences; visual seamlessness fails below. |
| Panel/canvas bottom anchor | PASS | All observed panels: x1584,y1025,96×104pt. Image:x1591,y1047,82×82pt. No panel/canvas movement across frames/candidates. |
| Artwork bottom | Approximately stable | Main-body last visible row201–202 in192×208 capture pixels; threshold-based measurement, not anatomical landmark tracking. |
| Horizontal body stability | **FAIL** | Main-body bounding-box center ranges72.5–118px:45.5 capture pixels /22.75pt. This measures silhouette bounds, not a tracked joint. Video confirms visible hopping. |
| Character size stability | **FAIL** | Main-body bounds width91–111px, height86–102px; fixed renderer canvas, varying source silhouettes. |
| Identity consistency | **MANUAL_VISUAL_REVIEW** | Face, leaf/tail silhouette and proportions vary. Do not label artwork accepted from mechanical tests. |
| Blink naturalness | **MANUAL_VISUAL_REVIEW** | Closed-eye frames02/05 visible; assess four speeds. Stray edge fragments appear in these source frames. |
| Breathing naturalness | **MANUAL_VISUAL_REVIEW** | Shape changes and lateral hopping remain; a slower cycle does not repair registration. |
| 06→01 visual seam | **FAIL** | Main-body bounds center118→72.5px (22.75pt jump); confirmed in actual captures. |
| Actual panel clipping | PASS for observed pose | None of six main-body bounds touches the panel edge. Tiny source fragments are not panel clipping. No broader gameplay pose coverage claimed. |
| Timing approval | **PENDING HUMAN CHOICE** |1500ms remains only a candidate. Existing manifest100ms/frame is retained, not newly approved as a production default. |

[analysis.json](analysis.json) includes per-frame PTS, hash-to-frame correlation votes and measured bounds. `*-capture-timestamps.json` contains native sample timestamps; `*-renderer-trace.jsonl` records independent AX observations. AX and video are asynchronous, so labels were correlated inside the longer1800ms candidate's frame holds, then identical capture hashes map all four videos. [actual-frame-01.png](actual-frame-01.png) through `actual-frame-06.png` are representative actual panel captures, not replacements for video.

## Assets and runtime boundaries

The original [source manifest](source-manifest.json) is preserved. ZIP `idle_01.png`…`idle_06.png` map byte-for-byte to the existing zero-based runtime `idle_00.png`…`idle_05.png` contract. Hash, RGBA,256×256, transparency and alpha-bounds assertions are covered by `tests/assets/test_moa_idle.py`. MOA base.png is unchanged. Only MOA Stage1 IDLE is opted in; MOVE/REACT/PIP stay unavailable and retain own-base fallback. There is no new clock, per-character RAF, gameplay activation, or progression change.

## Reproduction and durable originals

- Worktree: `/Users/jinseongdae/Documents/ChatGPT/luma-moa-idle-animation-pilot-v1`
- Complete original PNG captures, release bundles, logs, isolated QA save and regression evidence: `/Users/jinseongdae/Documents/LUMA QA/moa-idle-pilot-v1/`
- Build: set `CARGO_TARGET_DIR`, run `python3 scripts/gui_qa/build_moa_timings.py --output <root>/playback-candidates`. It restores the original manifest even on failure.
- Compile `record_window.swift` with `swiftc -parse-as-library`. Use existing `run.py --keep-running` to create a fresh isolated session; then `capture_moa_timings.py --root <root>`. Requires macOS ScreenCaptureKit/Screen Recording/Accessibility/PostEvent permission, ffmpeg, Java21,PG16. Output dirs must be new.
- `analyze_moa_capture.py <root>` reproduces frame-order/PTS/AX correlation. Visual bounds in the committed analysis were separately measured from largest connected nonblack component below y60, threshold max RGB>40, excluding the evolution button and stray fragments.

The initial GUI focus smoke was interrupted when the front application ceased to be TextEdit (guard exit4); this run is **NOT a focus PASS**. Capture traces show no LUMA front activation during the final recordings. No full Focus/Single Instance/Movement/Evolution GUI certification is claimed by this timing comparison. All owned preview app/server/PostgreSQL processes were stopped; evidence retained. Initial recorder initialization failure, baseline fallback capture and first scaffold-test failure remain in local evidence. The scaffold tests were corrected to own empty temporary fixture directories independently of newly delivered PNGs; production assets were not removed to satisfy them.

## Automated regression

`npm run validate:alpha:release` completed **AUTOMATED_READY / MANUAL_QA_REQUIRED** on this working tree (precommit parent77c56a6). [release-result.json](release-result.json) reports all18 composed checks, including frontend, animation/content, presentation, assets, policies, Tao, Rust/fmt/clippy, native harness compilation and isolated Java/PostgreSQL fresh/persistence/failure regression. These checks do not waive the visual defects or certify unchanged-CSP animation playback. Source fingerprints record the production renderer inputs used for these recordings.
