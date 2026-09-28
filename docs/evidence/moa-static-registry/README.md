# Option B implemented — unchanged-CSP production playback

**Architecture verification PASS. Artwork remains FAIL / REPLACEMENT_REQUIRED. PR #46 stays Draft; no timing approval or automatic merge.**

[Actual production .app playback (8.10s)](production-static-playback.mp4) · [verification and hashes](verification.json) · [runtime before](runtime-before.json) · [runtime after](runtime-after-trace.jsonl) · [release gate](release-result.json).

## Implementation

Canonical `public/assets/**/manifest.json` remains the metadata authority. `scripts/sync_animation_manifests.py` walks the existing companion/monster registry paths and emits deterministic `src/animation/generated-manifests.ts`. Run `npm run sync:animation` after editing metadata. `prebuild`, `predev` and the animation test entry point check freshness; CI already invokes build and those tests. There is no new build framework/package, giant switch, runtime catalog or remote dependency. Five existing manifests are projected; absent optional18-character slots are not invented. Existing RUU/NOX metadata remains compatible. The current production MOA IDLE metadata is required.

The existing loader statically imports this module, checks an exact own key and returns an isolated clone. Existing parseManifest, clip validation, PNG Image decode/cache and frame URL calculation remain. Missing keys, malformed metadata, invalid states or unavailable frames reject the clip and preserve the character's own base. PIP/MOVE/REACT delivery status is unchanged. Shared clock, RAF ownership, native panel/focus behavior, gameplay activation and production CSP are unchanged. Source facing RIGHT remains in the existing pilot contract; animation state→clip mapping also remains there, avoiding a second manually edited metadata authority.

## Actual native before/after

Both cases use release Tauri .apps with **the same original production CSP**, the same six approved PNG bytes and the same opt-in document-start observer. The before control temporarily reinstated the prior JSON-fetch implementation during its isolated build; the static loader was restored immediately afterward. The control is explicitly labeled, not represented as a pristine historical binary. Final build target was restored to Option B.

| MOA WebView observation | Before control | Static registry production |
|---|---:|---:|
| Animation manifest fetch attempts |1|0|
| Existing Tauri IPC fetch attempts |2|2|
| Total fetch attempts |3|2|
| XHR attempts |0|0|
| CSP violations |1 (`connect-src`, actual `tauri://localhost/.../manifest.json`)|0|
| Display |MOA own base|MOA IDLE frames1–6 animation|

`LUMA_METADATA_AUDIT=1` enables a document-start request observer via WebviewWindowBuilder. It wraps existing fetch/XHR entry points, observes CSP events, and exposes bounded records via an invisible noninteractive AX status element. It initiates no requests, polling, timers or RAF and changes no rendering inputs or CSP. Normal launches install no observer. A positive-control unit test verifies rejected fetch/XHR attempts and CSP events are counted; the real before-control rejection additionally proves the observer detects this exact failure. Thus after=0 is not inferred solely from an empty network panel.

This is an actual WebView request-attempt trace, **not an OS packet capture or a claim of zero application-wide backend traffic**. This WKWebView run produced no ResourceTiming entries for custom-protocol image loads; those empty arrays are not used as proof. Existing IPC calls are expressly excluded from the manifest count and preserved. PNG loading is independently evidenced by actual decoded frame playback. Observer instrumentation is disclosed; no QA CSP exception was used. `build_moa_timings.py` no longer adds one and now regenerates/restores the registry when testing candidate timings.

ScreenCaptureKit captured83 complete buffers over8.100s; the six recurring pixel patterns follow01→06 cyclically with14 observed06→01 transitions. The actual canvas now faces RIGHT; pixel matching accounts for the earlier LEFT-facing reference captures mathematically without editing footage/artwork. [Pixel matching scores](pixel-label-mapping.json) and native [capture timestamps](capture-timestamps.json) are included. Independent AX samples show all six `MOA IDLE frame N animation` labels, not base fallback. The video is3× enlarged for review and resampled at60fps using native PTS intervals. Existing600ms metadata is retained for this architecture test, not approved as final production timing.

## Exact approved inventory and CSP delta

Only the loader's one fetch call-site entry is removed from `alpha-release-runtime-inventory.json`; all other entries compare equal to76404d6. Runtime policy source scan PASS. Metadata lookup adds no replacement networking interface. CharacterAnimator itself never owned the fetch; it remains a pure phase sampler, with the change confined to its asset loader.

SHA-256 over UTF-8 production CSP string, before **and** after:
`ec17f98f93751c43639cd59c9022e26c2a7d2d700715fe6e360227803fcd0a4f`

Whole unchanged `src-tauri/tauri.conf.json` SHA-256:
`cf5e621e0e9e62294759f24152578b05af8a01b9deb77329f4ee2657c4c7efed`

No `connect-src 'self'`, wildcard, remote manifest allowance or security-policy weakening was added. The shared clock source hash and full CSP file hash are regression-asserted against the approved prior implementation. The native observer initializer does not change the frozen network/scheduling inventory or focus contracts.

## Validation and limits

- `npm run validate:alpha:release`: **AUTOMATED_READY / MANUAL_QA_REQUIRED** — all18 composed checks PASS, including frontend, animation/content, presentation,39 asset tests, optional/strict delivery, frozen policy, Tao, Rust/fmt/clippy, native harness compilation, Java/PostgreSQL fresh/persistence/failure regression.
- Static-registry tests: MOA IDLE lookup with fetch forbidden; MOVE/REACT/PIP unavailable; unknown/external/prototype keys; invalid metadata/state; missing frame; own-base selection; mutation isolation; document-start observer positive control.
- Generator tests: fresh/deterministic output, edited manifest detection, invalid/required-missing metadata, optional missing entries, external paths, duplicate JSON keys, CSP and shared-clock unchanged.
- The full gate report names the precommit parent and dirty working tree honestly. Runtime source fingerprints and recorded binary hash are in verification.json; CI validates the pushed commit separately.
- Artwork: **FAIL / REPLACEMENT_REQUIRED**, unchanged. This architecture test does not certify visual registration, natural blink/breathing or approve timing. This capture-only session does not claim a new full focus/interaction/soak GUI pass.

Durable original .app, all captured PNGs, logs and isolated regression evidence: `/Users/jinseongdae/Documents/LUMA QA/moa-static-registry-v1/`. Actual playback uses the root `LUMA Spike.app`; `before-control/` is diagnostic only. QA app/server/PostgreSQL sessions were stopped after recording. Build command: `CARGO_TARGET_DIR=<target> npm run tauri -- build --bundles app --config '{"bundle":{"active":true}}'` — no CSP override. GUI reproduction uses `run.py --metadata-audit --capture-only --keep-running`, then `capture_static_manifest.py <root> --recorder <record-window>` and `stop.py <root>/session`.
