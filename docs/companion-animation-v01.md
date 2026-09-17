# Companion Animation System v0.1

## Architecture

Rust CompanionState → WorldSnapshot → state/clip resolver → manifest + clip loader
→ elapsed-time AnimationController → React frame renderer.

Rust remains authoritative. No native, behavior, personality, safe-area, PIP lifecycle,
Tao, focus or single-instance changes are included. This branch starts at main
5118216; PR #6's unmerged single-instance work is excluded.

`src/animation/model.ts` defines the manifest, mapping, sizing and direction rules.
`loader.ts` validates and caches assets. `controller.ts` owns presentation time;
`useAnimation.ts` connects its clock to React using one requestAnimationFrame loop.
`CompanionVisual.tsx` renders the chosen frame or the existing CSS placeholder.
PIP continues to use the original placeholder and interaction behavior.

## Mapping

| Rust state | Clip |
| --- | --- |
| IDLE | idle |
| WALKING | walk |
| SITTING | sit |
| LOOKING | look |
| SLEEPING | sleep |
| REACTING | react |
| DRAGGING | idle |

A future drag clip only requires changing the resolver entry and supplying the
manifest/frames. No animation completion changes Rust state. Non-loop react holds
its last frame until Rust changes state.

## Assets and schema

Runtime paths are `/assets/creatures/{species}/stage{NN}/manifest.json`.
Vite's source directory is `public/assets/creatures/moa/stage01/`; it is copied
unchanged to the distribution and Tauri bundle. Add production frames there:
`idle/idle_00.png`, `idle/idle_01.png`, etc. The six clip directories intentionally
contain no PNGs. No new character artwork has been generated.

The checked-in manifest declares species `moa`, stage `1`, canvas 256×256,
normalized anchor (0.5, 1), display width 130, and the requested six clips.
Each clip supplies positive integer `frames` (maximum 256), positive millisecond
`frameDuration`, and boolean `loop`. Filenames use the clip key and zero-padded
frame index. Species/stage resolve independently of game evolution logic.

All frames must have identical declared canvas dimensions. The artist must align
feet/body grounding to the same bottom-center on every transparent canvas; the
renderer cannot infer visible pixel bounds or correct inconsistent art padding.
This version rejects non-bottom-center anchors rather than silently moving them.

## Timing, direction and ground contract

The injected clock defaults to performance.now(). Frame is computed from total
elapsed milliseconds, not snapshot/render count. Looping uses modulo; non-looping
clamps to the final frame and stops scheduling after its duration. State changes
restart from frame zero when the clip is ready, including IDLE ↔ DRAGGING even
though both use idle. A new presentation token prevents stale frames resurfacing
on rapid A → B → A transitions while assets load. Async results after cleanup
are ignored and the outstanding animation frame is cancelled.

The memoized visual receives state/facing only, so 33 ms position snapshots do
not reset or re-render it. React frame updates occur only when the frame changes.
Facing changes do not restart playback. Source direction is RIGHT; LEFT applies
scaleX(-1) around 50% 100% without mirroring the container.

The full canvas scales uniformly by the minimum of requested display width,
actual panel width and panel height. The image sits at the panel bottom-center,
which is the established world anchor. Native panel sizes and coordinates are
unchanged; e.g. a 130 pt requested sprite is capped by a narrower existing panel.
Sprite frames do not inherit placeholder body keyframe transforms. Debug labels
remain on placeholders, but do not push sprite canvases above the ground.

## Fallback and resource use

Missing/invalid manifest, absent clip, any missing frame, inconsistent canvas or
an image rendering error uses the existing CSS placeholder. Every frame in a clip
is loaded before activating that clip, avoiding partial playback. Failures and
successes are cached for the WebView lifetime; restart/reload after adding assets.
There are no polling retries and no RAF while assets are unavailable. One RAF is
active per mounted loaded Companion, and it is cancelled on unmount/state change.
Background throttling may skip frames on return; elapsed time remains authoritative.

No new dependencies. The test runner uses existing TypeScript and Node's built-in
test runner. Frame decoding increases memory: all 34 default 256×256 RGBA frames
are roughly 8.5 MiB before browser overhead if all clips have been used. Assets are
cached for the WebView lifetime; larger species/catalogues may need bounded cache
and loading budgets later. CPU/memory benchmarks with real PNGs are NOT_RUN.

## Validation

- `npm run test:animation`: 20 deterministic tests PASS. Seven mappings, state reset,
  repeated snapshots, elapsed loop wrap, react completion, LEFT/RIGHT, missing
  manifest/frame/clip, complete clip caching/filenames, inconsistent canvas,
  bottom-center fit/flip, invalid anchor/timing.
- `npm run build`: PASS; no dependency/version changes.
- `cargo test --locked`: 30 existing tests PASS.
- `cargo clippy --locked --no-deps -- -D warnings`: PASS; existing Tao warnings remain.
- Existing policy tests: 8 PASS. Tao integrity check: PASS.
- Existing CI desktop-static now also runs the deterministic animation tests.
- Browser build preview: missing-PNG MOA IDLE fallback visually confirmed; this is not a native focus test.
- Production PNG appearance, foot alignment across actual frames and native mouse/
  typing focus revalidation: MANUAL_REQUIRED when production assets arrive.
  Mock image I/O tests prove loader decisions, not real sprite visual quality.

## Manual verification

Run `npm ci`, `npm run test:animation`, then `npm run tauri -- dev`.
With no PNGs, verify MOA's existing CSS body/state presentation, click/drag and PIP
interaction still work. Once approved PNGs arrive, copy the exact numbered frames,
restart, and verify all six clips, left/right facing and stationary feet during
frame changes. A missing frame in one clip should fall back only for that clip.
Use the existing focus checklist; no activation/focus APIs were introduced here.
