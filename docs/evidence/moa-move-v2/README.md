# MOA MOVE v2 anatomy-guided delivery

Replaces only the supplied MOVE bytes in the existing `walk/walk_00..07.png` slots. Original `move_01..08.png` names and hashes remain in `source-manifest.json`; `asset-validation.json` proves ZIP-byte equality and recomputed zero center/bottom drift. Frames01/05 intentionally share bytes; seven unique decoded frames exist. The alpha planes are not all identical to base, but their registration bounds meet the delivered contract; this is not an alpha-equality approval.

Base/Breath/Blink, AnimationStateResolver, static registry, shared clock, MovementController, velocity-linked rate and CSP are unchanged. Existing80ms/frame,640ms/1× cycle remains a **candidate**, not production visual approval. IDLE stays1800ms Breath,90ms Blink,3–7s randomized Blink.

`pixel-variation.json` measures adjacent frame pairs including08→01 in the prior anatomy bounding-box ROIs. These are explicit pixel measurement regions, not authoritative semantic masks. V1 front/rear paw RGB variation was zero; V2 front paw changed-pixel counts are262,168,168,262,19,16,16,19; rear paw0,0,0,0,260,162,162,260; body interior301,301,357,357,301,301,357,357. Planted rear-paw phases correctly have zero difference; phase variation is not the same as judged gait quality.

## Actual production renderer

Two captures use the **same V2 release binary**, unchanged CSP,80ms/frame and existing40pt/s walking. LEFT seed165945 was the V1 seed but the live choice sequence diverged; RIGHT used existing seed20. No runtime, movement configuration, timing or state injection was added. This is similar-condition comparison, **not identical deterministic replay**. The session launch SHA predates the asset commit; source ZIP/bundle hashes and unchanged-runtime checks bind the delivered assets separately.

| Measurement | Actual result |
|---|---|
| Recording duration | LEFT306.704s + RIGHT47.845s |
| Actual MOVE | LEFT11.742s + RIGHT3.345s = **15.088s**, five autonomous walks |
| Frame order | PASS:01→08→01; **zero AX frame-order gaps** in either recording |
| Cycle timing | Combined median **643.902ms**; LEFT641.999ms / RIGHT651.389ms; observed range587.580–685.986ms (timestamp sampling/dispatch jitter, not new timing settings) |
| IDLE→MOVE | Four direct entries; RIGHT interrupted BLINK inside IDLE as intended |
| MOVE→IDLE | Five returns to Breath; subsequent Blink observed in both sessions |
| Center/bottom drift | **0pt** within each facing; source alpha bounds also0px |
| Facing | RIGHT/LEFT PASS. Visible silhouette centers97px/94px on2× capture; **1.5pt reversal excursion** unchanged from V1. Non-regression PASS; zero-excursion criterion remains FAIL. |
| Panel/canvas | Constant96×104pt /82×82pt; no scale jump |
| Clipping/blank/base fallback | None in captured samples; IDLE/BLINK/MOVE all use animation |
| World continuity | Sampled-path PASS: no backwards steps during walks, no vertical movement, no IDLE x/y change. Entry displacement0–2pt along travel, exits0pt. Native movement ownership unchanged. |
| Network/CSP | Manifest0, XHR0, CSP violations0; only existing Tauri startup IPC listen/snapshot attempts |
| Focus/single instance | Real bounded TextEdit marker delivered; foreground retained. Three secondary launches create no additional World/panels; native activation/key-window counters0. |

The largest sampled native step is6pt during a LEFT walk; CGWindow/AX calls can coalesce multiple native ticks. Full traces preserve this value. The continuity result describes observed monotonic paths and transitions, **not an assertion that every native tick was independently measured**. This recording avoids the V1 TextEdit/Space transition during capture; focus testing happened afterward.

`production-left.json`, `production-right.json`, `playback-summary.json` retain the measurements. The dark-pixel threshold for visible silhouette bounds is the same as V1. Production captures are not HTML mocks.

![Actual LEFT capture](actual-left.png)
![Actual RIGHT capture](actual-right.png)

## V1 versus V2 human review

| Version | LEFT actual clip | RIGHT actual clip |
|---|---|---|
| V1 | `/Users/jinseongdae/Documents/LUMA QA/moa-move-v1-seeded/move-02-left.mp4` | `/Users/jinseongdae/Documents/LUMA QA/moa-move-v1-seeded/move-03-right.mp4` |
| V2 | `/Users/jinseongdae/Documents/LUMA QA/moa-move-v2/review-left.mp4` | `/Users/jinseongdae/Documents/LUMA QA/moa-move-v2-right/review-right.mp4` |

Full V2 recordings are `production-move.mp4` in each V2 directory. Raw ScreenCaptureKit buffers/PTS, AX/native frame trace, network trace and app logs are retained beside them. `recordings.json` records absolute paths, SHA256 and byte counts. Files are durable local artifacts, **not cloud-uploaded videos or temporary-only output**.

These captures track the entity panel; they show actual gait, while absolute movement comes from the accompanying native trajectory. They are not fixed-desktop shots, so sliding relative to the desktop should be assessed with that limitation. Source pixel variation increases objectively: V1 near-paw ROIs unchanged, V2 front/rear paw variation present; body interior also changes. This alone does not prove improved perceived walking.

**MANUAL_VISUAL_REVIEW:** foot motion, body bob, sliding impression, walking impression and640ms naturalness. No "prettier"/"more alive" PASS is assigned. No timing or artwork deformation was changed to influence acceptance. Existing1.5pt facing excursion remains a Known Issue, not newly attributed to V2.

## Regression and scope

Full `npm run validate:alpha:release` passed AUTOMATED_READY / MANUAL_QA_REQUIRED: frontend, animation/content, presentation,43 asset tests/validators, release policies, Rust/fmt/clippy/Tao, native harnesses and Java/PostgreSQL fresh/persistence/failure tests. Exact run binding is in `release-result.json`; final clean-HEAD rerun is linked in the PR body when complete.

Missing MOVE frames still reject the complete clip and use MOA own base; approved IDLE remains available. REACT stays NOT_SUPPLIED/own-base. Breath1800ms, Blink90ms and randomized3–7s interval unchanged. Static registry/shared RAF/source runtime have **no diff** from V1. Interaction/Evolution priority regression is automated; dedicated actual GUI Battle/Evolution scenarios were NOT_RUN for this asset-only follow-up.

Original V1 failures, anatomy annotations and recordings are retained. MOVE v2 remains a visual pilot, **not production visual approval**. PR #47 remains Draft; no merge.
