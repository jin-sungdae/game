# Alpha Monster Asset Delivery — Batch 1

Base: origin/main 6ba7593. Branch: feature/alpha-monster-assets-batch1. No dependency on or merge of the separate Spawn × Encounter integration branch.

## Original production delivery

User-approved files were copied byte-for-byte to existing canonical destinations; no regeneration, crop, resize, recolor or placeholder. All four are 256×256, PNG, 8-bit RGBA, non-interlaced with alpha extrema 0..255. The existing validator passes each supplied file. SHA-256 matches original and destination:

| Source | Destination | SHA-256 |
|---|---|---|
| mello_base.png | public/assets/monsters/mello/base.png | 818efb32f7e5a19efcbb87342eb07b55047cd99e15d02dd30f47bca03c85a831 |
| mossy_base.png | public/assets/monsters/mossy/base.png | 6555280c8dc76d8b93ddd348cae1fbf7b27e282bd0bb6bfbec235dcc874afdb1 |
| chirp_base.png | public/assets/monsters/chirp/base.png | 8629ba2cf4f22f3e0946f7d3e030869ce5f38f5a06f2f65ca9af77c14bfba83e |
| bubu_base.png | public/assets/monsters/bubu/base.png | 979f8a38cc19cc5d3425aebe65142c559466b9ad32d3406f60646dfa1ba6eed4 |

Registry and metadata require no edits. MELLO/MOSSY/CHIRP/BUBU resolve their own bases; PIP remains byte-identical to main. Missing PEBB still renders diagnostic, never another monster's base. Animation → same monster base → diagnostic priority is unchanged.

## Measured renderer bounds and facing

Read-only pixel measurement uses nonzero alpha (A > 0), bounds [left, top, right-exclusive, bottom-exclusive]. Real React MonsterVisual/BaseSprite and current CSS were mounted in a temporary Chrome headless harness with a 96×104 logical-pixel host, existing .gp-pose/.gp-impulse/.gp-visual wrappers and padding, no native window changes. PIP retains .gp-pip scale(.8); new monsters use current metadata scale 1. Reduced-motion/resting pose avoids transient animation sampling. Waited for images and ResizeObserver layout before DOM/canvas measurement. This is browser renderer evidence, not a native WKWebView gameplay run.

| Monster | Source visible bounds | Source visible size | Rendered full canvas | Rendered visible size | Transparent bottom gap rendered | Clipping |
|---|---|---|---|---|---|---|
| PIP | [12,41,244,248] | 232×207 | 65.60×65.60 | 59.45×53.04 | 2.05 | none |
| MELLO | [15,24,241,242] | 226×218 | 82×82 | 72.39×69.83 | 4.48 | none |
| MOSSY | [14,26,240,252] | 226×226 | 82×82 | 72.39×72.39 | 1.28 | none |
| CHIRP | [14,73,242,252] | 228×179 | 82×82 | 73.03×57.34 | 1.28 | none |
| BUBU | [24,32,235,245] | 211×213 | 82×82 | 67.59×68.23 | 3.52 | none |

For all five assets and both facings, canvas bottom-center is exactly (48,104) in the host. RIGHT uses matrix(1,0,0,1,0,0); LEFT uses matrix(-1,0,0,1,0,0). Mirroring asymmetric art may move its visible-alpha center within the canvas, but never moves the world anchor. The supplied original is treated as source RIGHT as approved; no pixel flip is saved. Visual screenshot inspection confirmed intact silhouettes and no clipping in the resting harness. Painted feet are not the same as canvas anchor: original transparent padding is intentionally preserved.

Recommendations: retain current native bounds and scale=1 for these deliveries. No measured clipping requires a change. New assets appear larger than PIP because PIP retains its legacy .8 wrapper; if visual size parity or exact painted-ground contact is desired, review presentation metadata separately. Do not crop or move supplied artwork to remove the measured padding. Native movement/attack/launch acceptance remains a separate manual run.

## Movement, combat and activation boundaries

| Monster | Preserved content identity | Existing pure movement test | Activation blocker |
|---|---|---|---|
| MELLO | COMMON / SLIME / JUMP / CURIOUS / BOTTOM | PASS | Desktop Encounter and entity routing remain PIP/GROUND-only; non-PIP server master and end-to-end approval outstanding |
| MOSSY | COMMON / PLANT / GROUND / SLEEPY / LOWER_CORNER | PASS | Dex adapter does not map LOWER_CORNER despite placement foundation having the zone; also PIP-only routing |
| CHIRP | COMMON / BIRD / FLYING / CURIOUS / TOP | PASS | FLYING exists in the pure MovementController but production Monster routing remains PIP/GROUND-only |
| BUBU | COMMON / AQUATIC / JUMP / PLAYFUL / BOTTOM | PASS | Same non-PIP/JUMP encounter and entity integration blocker as MELLO |

The new Rust regression reads each actual profile/zone from content, runs its existing controller in a negative-origin safe area with unchanged 96×104 entity bounds, checks containment/finite completion, and asserts enabled=false. It does not bypass server authority or claim a live spawn/battle integration.

Server BattleService uses shared level formulas; CombatRules capture supports COMMON (all four are COMMON). This alone does not authorize release: repository candidates require approved DB master metadata/use_yn plus enabled/contentReady/PRODUCTION; current desktop DTO guard accepts only PIP/GROUND. There is no non-PIP vertical-slice evidence in this asset PR. No combat formula or server master is added.

For all four, contentReady=false, productionStatus=PROVISIONAL, enabled=false are unchanged. Asset delivery is now validated; content readiness transition remains a separate review under docs/monster-content-v01.md, followed by explicitly authorized gameplay activation. The existing contract permits ready-but-disabled content, but this PR does not infer that broader readiness solely from PNG delivery. PIP alone stays ready/PRODUCTION/enabled. LOWER_CORNER and FLYING are not relabeled.

## Tests and limits

Local AUTOMATED PASS: npm build; 58 animation/base/Dex/content/asset tests; 49 presentation tests; 25 Python asset tests; 9 automation tests; 97 Rust tests, cargo fmt/clippy, Tao integrity. Seven optional live Rust fixtures are NOT_RUN. Added immutable source-hash/image/content tests and the pure movement compatibility test. A stale Collection regression fixture on main used MONSTER_002 (now confirmed MELLO); changed only that test fixture to the still-provisional MONSTER_005 / Dex slot 5. No Collection UI or behavior changed.

validate:alpha PASS with exactly ten unrelated missing deliveries. strict-alpha intentionally exits 1 with the same ten missing; no delivered file or PIP is missing. Existing optional frame/base gate also passes. CI performs server/PostgreSQL tests, native compile and all existing regression gates; final head-bound result is recorded in the PR.

PLATFORM_REQUIRED / MANUAL_REQUIRED: native WKWebView, real focus/input/single-instance, real non-PIP movement/combat and visual timing acceptance NOT_RUN. Browser static bounds and pure MovementController tests do not prove those paths. No assets, gameplay, architecture, UI or native implementation outside this delivery was changed. Human review and merge remain with the user.
