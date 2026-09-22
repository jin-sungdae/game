# Alpha Monster Remaining Asset Delivery v0.1

Base: origin/main 0187277 (includes Batch 1 activation PR #26). Ten approved files copied byte-for-byte; no image generation, crop, resize, recolor, metadata rewrite or panel change. Source/destination SHA-256 match for all ten supplied files. Existing five bytes are unchanged.

## Fifteen-asset measurement

All fifteen: 256×256, PNG, RGBA, transparent, canonical registry paths. Bounds below are the alpha>0 bounding box [left, top, right-exclusive, bottom-exclusive], measured from decoded source pixels. Rendered sizes are calculated from the existing 82pt canvas and current scale: PIP retains its .8 outer wrapper (65.6pt canvas), others use 82pt. This is a static pixel/geometry measurement, not a new native screenshot measurement.

The unchanged renderer anchors the canvas bottom-center at (48,104) inside the 96×104 panel. Canvas fits for both RIGHT and mirrored LEFT; all visible bounds are inside it. Resting geometry has no clipping. Source RIGHT is the approved delivery convention, visually reviewed from the supplied images; PNG cannot encode semantic facing or feet position. Existing bottom-center CSS/registry contract is preserved. Transparent source padding is intentionally retained. Motion/attack effects in WKWebView remain MANUAL_REQUIRED.

| Monster | Alpha visible bounds (px) | Rendered visible size (pt) | Static clipping | contentReady | productionStatus | enabled |
|---|---|---|---|---|---|---|
| PIP | [12, 41, 244, 248] | 59.45 × 53.04 | none | true | PRODUCTION | true |
| MELLO | [15, 24, 241, 242] | 72.39 × 69.83 | none | true | PRODUCTION | true |
| MOSSY | [14, 26, 240, 252] | 72.39 × 72.39 | none | true | PRODUCTION | true |
| CHIRP | [14, 73, 242, 252] | 73.03 × 57.34 | none | true | PRODUCTION | true |
| BUBU | [24, 32, 235, 245] | 67.59 × 68.23 | none | true | PRODUCTION | true |
| PEBB | [19, 47, 242, 252] | 71.43 × 65.66 | none | false | PROVISIONAL | false |
| PUFF | [20, 44, 242, 251] | 71.11 × 66.30 | none | false | PROVISIONAL | false |
| TIKKI | [27, 30, 242, 247] | 68.87 × 69.51 | none | false | PROVISIONAL | false |
| MIMI | [21, 40, 234, 249] | 68.23 × 66.95 | none | false | PROVISIONAL | false |
| WISP | [18, 24, 240, 251] | 71.11 × 72.71 | none | false | PROVISIONAL | false |
| SHADE | [22, 29, 242, 243] | 70.47 × 68.55 | none | false | PROVISIONAL | false |
| EMBER | [21, 24, 238, 252] | 69.51 × 73.03 | none | false | PROVISIONAL | false |
| LUNET | [17, 24, 234, 248] | 69.51 × 71.75 | none | false | PROVISIONAL | false |
| NOVA | [17, 49, 242, 246] | 72.07 × 63.10 | none | false | PROVISIONAL | false |
| NOCT | [14, 35, 242, 244] | 73.03 × 66.95 | none | false | PROVISIONAL | false |

## SHA-256

| Monster | Repository SHA-256 | Source comparison |
|---|---|---|
| PIP | `f0e63d1349854c4539f07e402eecd70a7cfcfc789442d9243b5e20e4304487dd` | unchanged from main |
| MELLO | `818efb32f7e5a19efcbb87342eb07b55047cd99e15d02dd30f47bca03c85a831` | unchanged from main |
| MOSSY | `6555280c8dc76d8b93ddd348cae1fbf7b27e282bd0bb6bfbec235dcc874afdb1` | unchanged from main |
| CHIRP | `8629ba2cf4f22f3e0946f7d3e030869ce5f38f5a06f2f65ca9af77c14bfba83e` | unchanged from main |
| BUBU | `979f8a38cc19cc5d3425aebe65142c559466b9ad32d3406f60646dfa1ba6eed4` | unchanged from main |
| PEBB | `52069d2ed348e74d7387ccf07df7c725c2b82400016b6576dd1f28c6cf023ca4` | MATCH supplied source |
| PUFF | `8e4414e08d8e1a89a10eff7af0275b72b63eddda3d563d44abd7299c1887984d` | MATCH supplied source |
| TIKKI | `d234b8bc08e62802d1fe684176208ecd91a798d57d959f2ec9153699a6db8a81` | MATCH supplied source |
| MIMI | `b6476e6e585ef6075c131d1fa227304f39a738e87044e71694f3fdee12c41479` | MATCH supplied source |
| WISP | `9423d6524797e82349ab9f0bf40a4f8be5dacb3683276c0645516c52388e1b3d` | MATCH supplied source |
| SHADE | `3d2c8330486a197e30d8dc54d2f1b11de2458f982cb00f74ef73c06d4fc72974` | MATCH supplied source |
| EMBER | `a2ea1e16f29e383c6ad29505d8d6ce65750fa11a8216cfb0fde470b5e2cb9f66` | MATCH supplied source |
| LUNET | `eeba6eeec884e042b32f151f26b5e881a2dd0d3db65a5ba0ef13bf6153765640` | MATCH supplied source |
| NOVA | `0fd29358f313abafd9286357d57d43aac1114661c2b7f40e75596dd9b744b2a6` | MATCH supplied source |
| NOCT | `c808c729d22318b7cb544682ce629d2b35eda07f4d199c288b6210ab4c3ba75a` | MATCH supplied source |

## Readiness review

Asset availability is now 15/15. The current MonsterDefinition contract permits contentReady=true / PRODUCTION with enabled=false when confirmed metadata is ready; image validation alone is not broader gameplay approval (docs/monster-content-v01.md). For PEBB/PUFF/TIKKI/MIMI/WISP the approved bytes remove the asset blocker, but this delivery does not validate production routing, DB masters, encounter/battle/capture and restart vertical slices. Keep contentReady=false / PROVISIONAL / enabled=false pending that separate review. No readiness or gameplay field is changed in this PR.

SHADE retains NIGHT/EDGE; EMBER retains RARE/FREE_2D; LUNET retains RARE/NIGHT/FLOATING; NOVA retains RARE/FREE_2D; NOCT retains SPECIAL/NIGHT/EDGE. Their advanced spawn/rarity validation remains outstanding, and all remain disabled. Asset Registry, content definitions, server, migrations, native panels and engines are byte-identical to main. Existing PIP/MELLO/MOSSY/CHIRP/BUBU activation is preserved.

## Verification and limits

Both npm run validate:alpha and npm run validate:alpha:strict pass with zero errors and zero missing files. Added immutable remaining-delivery SHA tests and a real-repository strict-alpha completeness assertion using the existing validator. Full frontend, asset, automation, Rust/native and Java/PostgreSQL regressions run in the SHA-bound PR CI; final results are recorded in the PR.

Known risks: source orientation is an approved artistic convention rather than machine-detectable PNG metadata; transparent padding changes apparent ground contact. Native focus/input, single-instance, multi-monitor and dynamic clipping are MANUAL_REQUIRED / NOT_RUN in this asset delivery. No new gameplay activation or DB changes. No automatic merge.
