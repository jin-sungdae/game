# Production Companion Asset Integration v0.1

## Registry and resolution

`src/entities/companions.json` is the shared character registry consumed by the
TypeScript resolver and offline validator. It preserves these master identities:

| Species | Name | Identity | Palette |
| --- | --- | --- | --- |
| moa | MOA | Nature / Balance | Cream + Green |
| ruu | RUU | Sky / Explorer | White + Blue |
| nox | NOX | Night / Mystic | Dark + Purple |

Each entry explicitly maps evolution stage `1` to its runtime `assetManifest` URL.
`resolveCompanion(species, evolutionStage)` returns species, evolutionStage, name
and assetManifest, or null for unknown species/unregistered stages. It does not
invent later-stage paths or silently substitute MOA artwork. AssetLoader consumes
this registry and returns its existing null/fallback result for unknown identities
without I/O. Missing manifests/frames remain cached failures, with no retry loop.

CompanionVisual now accepts species/evolutionStage props instead of embedding MOA
in asset resolution. Defaults remain moa/1, so the existing Rust MOA world and
behavior are unchanged. Names come from the registry. No selector, additional
Companion world entity, palette-driven character redesign or evolution gameplay
has been introduced. The existing CSS shape is diagnostic fallback, not a master
concept drawing of RUU/NOX.

## Repository and runtime paths

For each of `moa`, `ruu`, `nox`:

```
public/assets/creatures/<species>/stage01/
  manifest.json
  idle/   idle_00.png ... idle_05.png
  walk/   walk_00.png ... walk_07.png
  sit/    sit_00.png  ... sit_03.png
  look/   look_00.png ... look_03.png
  sleep/  sleep_00.png ... sleep_05.png
  react/  react_00.png ... react_05.png
```

The numbered PNGs above are the delivery contract, **not files currently supplied**.
Only manifests and empty directory markers are committed. Vite copies public
assets to `/assets/creatures/...` in the application bundle.

All three manifests use the existing schema: species, stage, canvas (256×256),
normalized anchor (0.5,1), display width 130, animations with frames,
frameDuration in milliseconds and loop. Counts are 6/8/4/4/6/6 = 34 per character,
102 total. Existing timing values 100/80/120/120/150/80 ms are retained; react is
non-looping. Source art faces RIGHT; the unchanged renderer flips LEFT at runtime.

## Validation commands and failure policy

```
npm run validate:assets
npm run validate:assets -- --allow-missing
npm run test:assets
npm run test:animation
```

Default validation is a strict production gate: exit 1 if required PNGs are absent.
It is expected to fail on the current pre-delivery repository. `--allow-missing`
validates all manifests/directories and permits only completely empty frame
folders, reporting NOT_SUPPLIED/PENDING per clip. It is not proof of production
readiness. Even in this mode, a partial clip, invalid filename or malformed PNG
fails. Current CI runs this scaffold mode plus deterministic validator tests.
Switch to strict mode for production acceptance after all assets are delivered.

The Python 3 standard-library script checks:

- Manifest identity, stage, required animation keys, frame counts, timing/loop,
  canvas, anchor and display size.
- Required directories; exact lowercase names/extensions and zero-based numbering.
- Missing/excess frames and duplicate numeric indices (e.g. `_0` plus `_00`).
- PNG signature/chunk CRC, 256×256 IHDR, RGBA alpha channel (color type 6),
  8-bit non-interlaced encoding, decompression length and scanline filter values.

The accepted delivery subset is explicitly 8-bit, non-interlaced RGBA PNG;
indexed PNG with tRNS and interlaced files must be exported as this format.
Alpha-channel presence does not prove meaningful transparency, art direction,
RIGHT-facing pose or aligned feet. Those remain human art checks. Exact duplicate
filenames cannot coexist in a directory; alternate names for the same numeric
index are detected. The tool does not ban visually identical frames, which may be
intentional. `.gitkeep` and `.DS_Store` are ignored.

## Production delivery

1. Obtain approved master-concept frames; do not invent or recolor characters.
2. Export each frame on an identical 256×256 transparent RGBA canvas with feet at
   bottom-center and source facing RIGHT. Keep padding/ground consistent.
3. Copy the 34 exact numbered files into each species' six stage01 folders.
4. Run strict `npm run validate:assets`, then build and restart the app (runtime
   failure caches last for the WebView lifetime).
5. Review real animation, alpha edges, left/right flip and ground alignment in
   macOS. Retain the existing focus/drag checks; automated file validation cannot
   substitute for production-art or native interaction validation.

## Future stages

To support an approved stage later, add its manifest/directories and an explicit
stage-to-manifest entry in that species registry. The resolver and renderer accept
species+evolutionStage without changing AnimationController. Stage02–05 assets,
registration and gameplay are intentionally not implemented in this PR. The current
validator applies the stage01/common 34-frame contract to registered assets; change
that contract explicitly if later-stage production specifications differ.

## Validation and scope

- Animation + registry/loader: 27 deterministic tests PASS (previous 20 retained).
- Asset validator: 12 deterministic tests PASS, including a complete 102-frame
  binary fixture in a temporary directory and missing/corrupt/invalid cases.
  These are parser fixtures, not character art; no PNG is added to the repository.
- Scaffold validation: 0 errors, 18 clips PENDING / 102 PNGs not supplied.
- Strict validation: expected FAIL while production PNGs are absent.
- npm build PASS; Rust 30 regression tests PASS; application clippy PASS; existing
  automation policy 8 tests PASS; Tao patch integrity PASS.
- No dependency/version changes. Python 3 is required for the offline tool.
- No edits to Rust, Companion behavior/personality, DesktopSafeArea/ground,
  Single Instance, Tao, native panels, focus or AnimationController timing.
- Actual production sprite/native-focus validation: NOT_RUN in this asset-free PR.
