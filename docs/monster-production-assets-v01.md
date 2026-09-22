# Monster Production Asset Delivery v0.1

## Design before implementation

Extend the existing Monster Asset Registry, BaseAssetLoader, rendererSource and Python Asset Validator. Do not introduce an asset engine or merge Companion/Monster registries. Preserve PIP's path and legacy 0.8 gameplay wrapper scale. Add explicit delivery identities for the requested fifteen assets without mapping provisional Dex codes, activating monsters or modifying content DB/Collection UI.

All production PNGs remain user-delivered; this PR creates no production or placeholder PNGs. Binary parser fixtures are temporary test data only. Optional alpha validation accepts missing delivery, but validates every present file; explicit strict-alpha requires all fifteen bases independently of Companion frames.

The current Monster renderer has no animation scheduler. Extend its source selection contract to accept an optional same-monster, registered animation frame, validated through the existing image loader; an external existing animation producer owns timing. No new timer or engine. Animation failure falls through to the same monster base, then diagnostic. Visual scale is bounded and fitted inside the existing presentation envelope; PIP's existing scale is not multiplied twice.

Alternatives rejected: another registry/master in the database, copied Companion animation pipeline, placeholder art, and enabling missing content in gameplay. Human review applies before merge.

## Fifteen production delivery paths

Registry lookup uses uppercase codes; directory names are lowercase and case-sensitive. The fourteen new asset identities do not remap existing MONSTER_00x provisional Dex slots. Registering a delivery path does not enable encounters or claim that art exists. New entries use a neutral visualScale=1 and generic diagnostic name until reviewed content metadata is supplied; PIP retains its name and .8 scale.

| Code | Production path | visualScale |
|---|---|---|
| PIP | public/assets/monsters/pip/base.png | 0.8 |
| MELLO | public/assets/monsters/mello/base.png | 1 |
| MOSSY | public/assets/monsters/mossy/base.png | 1 |
| CHIRP | public/assets/monsters/chirp/base.png | 1 |
| BUBU | public/assets/monsters/bubu/base.png | 1 |
| PEBB | public/assets/monsters/pebb/base.png | 1 |
| PUFF | public/assets/monsters/puff/base.png | 1 |
| TIKKI | public/assets/monsters/tikki/base.png | 1 |
| MIMI | public/assets/monsters/mimi/base.png | 1 |
| WISP | public/assets/monsters/wisp/base.png | 1 |
| SHADE | public/assets/monsters/shade/base.png | 1 |
| EMBER | public/assets/monsters/ember/base.png | 1 |
| LUNET | public/assets/monsters/lunet/base.png | 1 |
| NOVA | public/assets/monsters/nova/base.png | 1 |
| NOCT | public/assets/monsters/noct/base.png | 1 |

Every image: 256×256, PNG, 8-bit non-interlaced RGBA, transparent pixels, bottom-center anchor, source RIGHT. Delivery directories can be created when supplying the original images; no blank art or placeholder PNGs are committed. PIP bytes/path remain unchanged.

## Validator and explicit delivery gate

- `npm run validate:alpha`: optional Alpha-only validation. Missing images are PENDING; any malformed supplied image is FAIL.
- `npm run validate:alpha:strict`: all fifteen canonical base files required. Runs independently of Companion frame/base completeness.
- `npm run validate:assets -- --allow-missing`: existing normal CI gate, now also validates optional Alpha delivery.
- For a staging checkout: `python3 scripts/validate_assets.py --strict-alpha --root /absolute/staging/root` (root contains registry and public/assets).

The existing PNG parser verifies signature, CRC/chunks, 256×256 dimensions, RGBA type/depth and bounded decompressed scanline length. Alpha delivery additionally reverses all five PNG filter types and rejects fully opaque RGBA. Checks also cover canonical paths, exactly fifteen Alpha codes, numeric finite scale 0.5–1.5, PIP .8 compatibility, duplicate JSON keys, wrong extensions/filenames, duplicate base copies and directory/file case mismatch. A file merely named .png cannot bypass format checks. Optional delivery never suppresses invalid supplied files. Existing strict-base retains its MOA/PIP requirement; Companion frame validation is unchanged.

Current checkout: optional-alpha PASS with fourteen PENDING; strict-alpha intentionally exits 1 with fourteen missing files. This is missing delivery, not a failing foundation. Tests execute the real strict CLI against a temporary root before/after all fifteen binary parser fixtures are supplied. No fixture is written under production public/assets.

## Runtime fallback and animation boundary

MonsterVisual uses the existing BaseAssetLoader/useBaseAsset and rendererSource: a successfully decoded, same-monster registered animation frame → that monster's successfully decoded base → existing diagnostic renderer. Unknown codes resolve to diagnostic without trying PIP or Companion art. Missing, invalid-dimension or decode-failed bases are cached as unavailable for the session. Reload after delivering a previously missing file.

The optional `animationFrame` input contains monsterCode, clip and url. `animationClips` entries, when supplied in a future reviewed registry change, name a clip directory under the same monster assetRoot (for example `/assets/monsters/mello/idle`). Only canonical numbered PNG filenames in that registered directory are accepted. Frames use the same image-size loader and source priority; image onError invalidates the animation frame and exposes the same base. No animation clips are activated in this PR. Timing and frame production remain outside this delivery foundation; no scheduler, RAF, interval or new animation engine was added.

## Scale, anchor and facing

`monsterAssetContract` defines the shared format/anchor/facing/scale bounds. Monster scale is applied to the intended 82-point base display size then capped to the measured container and existing 82-point motion-safe envelope. Thus scale >1 may be clamped, rather than enlarging the native panel. PIP retains its existing `.gp-pip` .8 wrapper and uses an internal multiplier of 1; no double scaling. Invalid/nonfinite scale falls back safely to 1 while delivery validation rejects invalid metadata. Diagnostic styling is unchanged.

Both animation and base use the same fitted size. Existing flex bottom alignment and transform-origin 50% 100% preserve the bottom-center anchor. RIGHT uses scaleX(1); LEFT uses scaleX(-1). Metadata scale is not a world/entity size, collision bound or Monster stat. Actual art's feet and facing cannot be inferred reliably from PNG metadata: visual approval remains MANUAL_REQUIRED. No production image is regenerated, resized, cropped or recolored.

## Validation and parallel work

Local AUTOMATED PASS: TypeScript/Vite build; 52 animation/base/Dex/delivery tests; 40 presentation/evolution/item tests; 22 Python asset tests; 9 automation tests; 93 Rust tests, fmt and clippy; Tao patch integrity; whitespace check. Seven optional Rust live fixtures are NOT_RUN. Normal asset validation passes with forty existing/new optional missing assets. Explicit strict-alpha fails as expected until fourteen deliveries arrive; complete temporary fixtures PASS.

PLATFORM_REQUIRED / MANUAL_REQUIRED: real desktop focus, typing/mouse, single instance, visual positioning and delivered-art appearance NOT_RUN. CI native compile and server integration results are recorded on the PR's final SHA, not inferred from local tests.

Base: origin/main dfe8345 (includes Spawn #20). Parallel Collection UI #21 has no overlapping files at inspection. Parallel Monster Content #23 overlaps scripts/test-animation.sh and tests/animation/monster-dex.cjs; preserve both test additions and the updated PIP asset expectation when integrating. No Monster Content DB, Collection UI, Rust, native window, migration, Companion pipeline or production PNG change. Architecture and merge remain human decisions.


## PR #23 main integration

Integrated origin/main e829615 into the existing PR #22 branch. Resolved test-animation.sh by retaining both asset tests and content projection/content tests. The expanded Dex contract, rarity projections, contentReady/productionStatus checks and PIP NEAR_DOCK content definition remain from main without source changes. All fifteen Alpha codes and lowercase asset identities now match the asset registry exactly; remaining provisional slots retain diagnostic-only resolution.

Updated pre-delivery test assumptions: baseAsset is a canonical URL candidate, not proof that a PNG exists. Dex BASE is a presentation intent; actual decode failure still uses the same-monster diagnostic fallback. No Collection UI or content definition was modified. A regression test loads successful image fixtures for all fifteen codes and proves contentReady/enabled/productionStatus remain unchanged: only PIP is PRODUCTION, ready and enabled. Content and asset scales are checked for equality.

This supersedes the earlier pre-integration note about unmapped provisional identities. Both Monster Content and Asset test suites run, including server rarity projection consistency. No PNG was created or changed. Optional alpha remains PASS; strict-alpha must continue to fail with exactly fourteen missing deliveries.

Post-integration local AUTOMATED PASS: 58 animation/base/Dex/content/asset tests, 40 presentation tests, 22 validator tests, 9 automation tests; 93 Rust tests (7 optional live fixtures NOT_RUN), cargo clippy/fmt, npm build, Tao integrity. Java 21 full test + bootJar passed against a newly initialized isolated PostgreSQL instance, then the temporary database was stopped and removed. Final CI evidence is attached to the latest PR commit.
