# PR #46 — local animation metadata / CSP analysis and proposal

Status: **PROPOSAL ONLY / HUMAN_APPROVAL_REQUIRED**. Analyzed implementation: `63c11025e5379f7eb48e94f569c5c89401db3466`. This follow-up changes documentation only. PR #46 stays Draft and must not merge. Artwork registration is a separate unresolved issue: wait for replacement assets; do not modify/regenerate the supplied six PNGs. No production timing is selected.

## Root cause

1. `src/entities/companions.json` stores canonical manifest URL strings. `resolveCompanion()` returns that string. `pilotDefinition()` selects MOA Stage1 and passes the URL through `PilotAssets` to `AssetLoader.loadRegistered()`.
2. `src/animation/loader.ts:6` implements `AssetIO.json` as `fetch(url)` followed by `response.json()`. No server-authored metadata, remote animation catalog, freshness requirement, or runtime mutation requires that fetch. It is the chosen IO implementation, not a requirement of the animation engine.
3. The JSON files are under `public/assets/.../manifest.json`. Vite copies public resources into dist; Tauri embeds frontendDist into the release application. They are static bundled data. Five manifest files currently exist: MOA Stage1/2, RUU Stage1, NOX Stage1, PIP. MOA Stage3 has a registry slot but no supplied animation manifest. Other Alpha monsters also must not be assumed to have animation metadata.
4. The macOS application opens `WebviewUrl::App(index.html?entity=...)`. The installed Tauri2.11.5 source (`manager/webview.rs`) resolves local App URLs against `tauri://localhost` on this platform. Thus the root-relative metadata URL targets the application asset origin, not the game backend. This is a script fetch through a local custom protocol; calling it an external HTTP request would be inaccurate.
5. `src-tauri/tauri.conf.json` explicitly sets `connect-src ipc: http://ipc.localhost http://localhost:1420 ws://localhost:1420`. None covers the production `tauri://localhost` asset origin. Explicit connect-src takes precedence over default-src: `default-src 'self'` does **not** add self to connect-src. The localhost1420 entry explains why development-origin testing may not reveal this production mismatch.
6. CSP rejects the manifest fetch. `AssetLoader` catches metadata errors and caches null; `PilotAssets` returns null; `CharacterRenderer` chooses MOA's own base.png. A rejection can therefore appear as ordinary missing-art fallback without a distinct error reason. Base images use Image/img loads, not fetch: the absent img-src falls back to default-src self, so the base can still display.

Evidence boundary: the previous unchanged-CSP release app displayed base in native AX; QA release bundles allowing same-origin connect-src displayed all six supplied frames. The source path and controlled configuration result identify the mismatch. No browser `securitypolicyviolation` event or exact WebKit console exception was captured; do not invent that diagnostic. Previous videos are QA-configured production-renderer evidence, not proof that the default configuration is fixed. Existing evidence: [timing report](evidence/moa-idle/README.md), [build override](../scripts/gui_qa/build_moa_timings.py), [loader](../src/animation/loader.ts), [CSP](../src-tauri/tauri.conf.json).

## Options

| Dimension | A — production connect-src self | B — build-time metadata registry, remove fetch |
|---|---|---|
| Security | Allows script connection interfaces to the application's entire origin, not just animation JSON. Self is bounded and is not equivalent to wildcard or permission for arbitrary remote origins, but it expands the current policy. Platform custom-scheme behavior needs native verification. | Leaves CSP unchanged; exact registered keys resolve immutable bundled objects. No metadata fetch, arbitrary URL, remote manifest or runtime external dependency. Build inputs still require validation; this is not a substitute for safe data handling. |
| Complexity | Small config diff; current loader/caching remains. Runtime fetch failures and CSP/platform differences remain. | One small deterministic generator, generated JSON/TS map, and a local JSON resolver. Adds stale-output checks, but removes runtime metadata IO/failure paths. No new package is required. |
| Existing architecture impact | Changes security configuration; no engine change. | Changes the metadata IO boundary only. Retain AssetIO test injection, loadRegistered signature, parseManifest identity checks, complete-clip image decoding/cache, frame URLs, own-base fallback, resolver and shared clock. No new engine or Rust authority. |
| Asset scalability | Per-WebView lazy manifest fetch/cache; all content still ships in the bundle and changes still require application rebuild. | Small metadata included in JS module per WebView; frame PNGs remain external bundled images and load on demand. Generated map avoids manual synchronization. Future huge catalogs may require measurement;18 characters do not justify remote metadata. |
| 18-character expansion | More registered local fetches as characters opt in; no benefit from remote/update capabilities under current requirements. | Keys cover the15 Alpha monsters and3 companion stages as metadata is supplied; retain existing RUU/NOX entries for compatibility. Missing NOT_SUPPLIED entries are omitted, not invented. Presence of metadata never activates gameplay or clips. Character count still does not increase RAF loops per WebView. |
| Release inventory impact | Current fetch call site remains. The source scanner does not scan tauri.conf.json: a passing inventory would not mean CSP was unchanged or approved. Explicit security-policy review required. | Removes exactly the existing loader fetch line from the network inventory; checker detects removals as well as additions. Requires explicit approval of that narrow inventory delta and a real before/after source scan. No RAF/worker/timer/backend inventory change. |

**Recommend B: a generated, statically imported metadata registry.** A is technically viable but not necessary to read static local animation data. B is slightly more build tooling and a simpler runtime/security model for this repository.

## Static-data alternatives considered

- **Hand-written static JSON imports/map:** feasible; TypeScript already enables resolveJsonModule and imports companion/monster registries. Small initial code but a manually maintained map can drift as assets expand. Moving manifests under src would also require updating existing Python validators and delivery tooling.
- **Move metadata authority into TypeScript/current asset registry:** feasible but duplicates or replaces existing artist-facing canonical manifests and mixes delivery definitions with clip timing. Unnecessary scope for this fix.
- **Vite eager glob/virtual module:** feasible with suitable source-module inputs, but introduces Vite-specific behavior into tests currently compiled with plain tsc/CommonJS. Lazy imports would add runtime module loading. Do not confuse a `?url` import (just a URL) with importing parsed metadata.
- **Generate a JSON module under src from existing public manifests:** preferred. Public manifests stay the canonical source; build tooling reads them from disk and emits data objects. Runtime imports the generated source module, not an asset URL. This preserves current files/validators and works with the existing JSON module and tsc test setup. Vite's public directory is primarily a copy-as-is URL facility, not the proposed runtime metadata module boundary.

## Proposed implementation after approval

1. Add `scripts/sync_animation_manifests.py` with deterministic sorted output and `--check`, following the existing `sync_monster_content.py` projection pattern. No dependencies beyond the standard library.
2. Read only companion registry stage paths and canonical monster assetRoot manifest paths. Validate exact root-relative paths, registry membership, identity/stage, schema, filename/case collisions and containment within public; reject traversal, external schemes and escaping symlinks. Read metadata only, never transform PNGs. Do not scan arbitrary docs/source ZIP manifests into the runtime map.
3. Emit `src/animation/generated-manifests.json`, keyed by existing canonical manifest URL. Generated output is not hand-edited and cannot become a second content authority. NOT_SUPPLIED missing manifests remain absent; a declared production clip without valid metadata fails the delivery/build gate. Validate existing supplied metadata even if that clip is not activated.
4. Statically import the generated map in the current loader's JSON IO implementation. Exact own-key lookup returns a promise of bundled data; unknown keys reject to the existing null/fallback path. Never retry via fetch/XHR/IPC/filesystem APIs. Preserve `parseManifest(species,stage)` and keep metadata read-only so cached shared objects cannot acquire mutated QA timings.
5. Remove the loader's fetch implementation entirely, not merely hide it behind a branch. Keep Image-based PNG decoding and same-character fallback unchanged. No per-frame IO, timers, clock ownership changes, backend calls, contentReady/enabled changes, or other animation opt-ins.
6. Wire generation/checking to builds and CI: explicit sync updates the checked-in generated projection; prebuild/test/CI `--check` rejects stale output. The development workflow must regenerate after manifest edits. All direct build/test entry points used by Tauri and CI must be covered, not only an interactive npm command.
7. Adapt timing QA to regenerate metadata for each candidate build and restore both canonical manifest and generated output in finally. Remove the QA connect-src self override entirely for new validation. Keep old recordings unchanged as historical evidence of their original configuration. No production timing decision is implied.
8. With explicit approval, record the exact network inventory delta: remove only the `src/animation/loader.ts` fetch entry/line. Do not disable the checker, retain a dead fetch for CI, or overwrite the baseline wholesale. Shared clock/RAF, other network call sites, backend workers, timers, focus and Tao remain byte/contract preserved as applicable.

This is a proposed loader-boundary architecture change and proposed inventory subtraction, **not authorization to implement either**. Production CSP stays unchanged even if B is approved. The prior shared-clock inventory approval does not cover this network delta.

## Acceptance plan — NOT_RUN for proposed implementation

- Generator determinism and stale-output failure; known/missing/unknown identities; malformed metadata; duplicate/case/path escape rejection. Preserve optional versus required delivery behavior and legacy registry entries.
- Resolver succeeds for registered metadata with fetch stubbed to throw; unknown/external keys never issue IO. Complete-clip size checks, missing frame fallback, MOA/PIP own bases, Reduced Motion and IDLE-only opt-in regressions remain.
- Inspect output JS and source inventory to confirm **zero animation metadata fetch sites**. No hidden equivalent networking API. Only reviewed inventory subtraction allowed.
- Build an ordinary release .app using unchanged production CSP, with no QA CSP override. Verify real IDLE frame playback and absence of manifest CSP violations/requests through diagnostic evidence. Functional loader verification is distinct from visual acceptance; artwork remains blocked until replacement arrives.
- Repeat full release gate, native focus/single-instance and relevant actual GUI regression after implementation. Current analysis does not claim a fixed default bundle or rerun those runtime checks.
- PR #46 remains Draft until replacement artwork and human visual approval; neither successful metadata loading nor CI approves art or timing. No automatic merge.

## Primary references

- [CSP connect-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/connect-src): script fetch control and default-src fallback semantics.
- [Vite public assets](https://vite.dev/guide/assets.html#the-public-directory): public files copied as-is and addressed by root URLs.
- [Vite JSON imports](https://vite.dev/guide/features.html#json): importing JSON as module data; eager versus lazy module discussion nearby.
- [Tauri CSP](https://v2.tauri.app/security/csp/): resource policy and separate IPC connect-src examples.

Current checkout uses Vite6.4.x/Tauri2.11.5; the repository code, compiler configuration and installed pinned Tauri source are the version-specific evidence. Latest online documentation is supporting context, not evidence that a proposed implementation was tested.
