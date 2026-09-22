# Monster Dex Foundation v0.1

> Historical proposal below describes PR #19. The table is the current catalog; [Monster Content Integration](monster-content-v01.md) supersedes provisional Alpha names, diversity assumptions, rarity references and authority/readiness rules. The thirty Dex numbers and projection contract remain.

## Architecture proposal before implementation

Base: origin/main c482fec. Isolated branch: feature/monster-dex-foundation-v01.

Add a validated Monster content registry alongside the existing Monster asset registry, independent of Companion definitions. Thirty provisional design slots describe identity, rarity, archetype, existing movement wire names, behavior, spawn metadata, capture direction and asset identity. Only PIP remains enabled. No runtime selector or formula changes.

Reason: the current one-entry asset map cannot describe future content or undiscovered Dex presentation. Keep server-owned gameplay values authoritative; client content is a design/presentation contract, never a source of encounter or capture decisions.

Alternatives: database columns/seeds are deferred to avoid parallel Flyway conflicts; merging Monster and Companion registries is rejected because the domains have different lifecycles; a new movement/AI engine is outside scope. Reuse existing MovementProfile values without routing content into movement execution.

Human review is required for this architecture proposal and eventual merge. Implementation is explicitly requested by the user; no automatic architecture approval or merge is performed.

## Authority and extensibility

`src/entities/monster-dex.json` is the versioned content plan, parsed by `monsterDex.ts`. Add reviewed string values to the lists and parser tests when extending archetypes/behavior/spawn vocabulary; unknown strings fail closed, never silently map to another type. Archetype is visual metadata, not combat class. Movement uses the seven existing Rust serde names; no movement dispatch or engine is changed. Behavior and spawn conditions do not execute AI, inspect apps, track focus, or consult OS activity.

`m_monster` owns production code/name/rarity/movement/encounter weight/use_yn and level ranges. The PIP record mirrors COMMON/GROUND/100/enabled. `CombatRules` owns capture probability: COMMON full-health reference 0.35 plus the existing HP term. `baseCaptureRate` is nullable design/reference metadata, never passed into combat; all provisional values remain null, weight 0, enabled false. No formula or balance change is made. Capture Direction TBD means design approval is outstanding, not a configured difficulty.

Display name is null for provisional slots; working names and provisional codes are editable design handles, not permanent DB master identities. Dex numbers are stable planning positions. PIP identity is COMMON / BEAST / GROUND. Its CURIOUS/BOTTOM/ANY_TIME tags describe content only and do not override existing behavior.

Future server selection contract: query enabled master records, then join a reviewed server-side content version by confirmed code, validate supported rarity and positive encounterWeight, evaluate spawn conditions using explicitly provided context, and weight eligible candidates in the existing transaction boundary. Undefined context excludes conditional candidates; empty candidates must follow a separately approved policy. This PR does not implement that join, change MonsterSelector, or activate these slots. Rarity alone must never authorize unsupported CombatRules values. DB metadata expansion is optional future work requiring a separate migration proposal, coordinated Flyway version, and human review.

## Assets and presentation

`monsters.json` remains the production asset map; `resolveMonster` preserves PIP's exact path and returns a null base for known slots without production art, or null for unknown codes (including prototype keys). Both paths use the existing diagnostic renderer. Optional animationClips can later point below the same assetRoot. No PNG is added or modified.

Asset convention: `/assets/monsters/{lowercase assetIdentity}/base.png`, 256×256 RGBA transparent, bottom-center anchor, source RIGHT. The PIP identity is `pip`. Visual scale bounds are 0.5–1.5 content metadata; PIP 0.8 documents its existing `.gp-pip` scale. This PR does not multiply that scale into the current renderer. Future Dex rendering must apply scale once within its own fitted bounds.

`src/presentation/monsterDex.ts` projects server-supplied discovery/capture evidence into UNDISCOVERED / DISCOVERED / CAPTURED; capture takes precedence. Collection codes may supply capturedCodes. The current backend does not persist discovery history, so callers must not infer discovery from the catalog or pretend history exists. Disabled slots are excluded from public Dex lists. Undiscovered entries expose `???`, null base asset and a SILHOUETTE intent; no silhouette PNG or new UI is created. Provisional working names are never public names. Diagnostic rendering on image-load failure remains the existing loader's responsibility.

## Thirty design slots

All names/themes except PIP are provisional and require visual design approval. Alpha marks 15 candidates for future work, not activation: all twelve silhouette families, all seven movement profiles and spawn profiles, and all five rarities are represented. Rarity distribution is COMMON 8 / UNCOMMON 7 / RARE 6 / EPIC 5 / SPECIAL 4.

| Dex No | Code | Working Name | Rarity | Archetype | Movement | Behavior | Spawn Profile | Spawn Condition | Capture Direction | Visual Theme | Production Status | Alpha |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PIP | PIP | COMMON | BEAST | GROUND | PLAYFUL | NEAR_DOCK | ANY_TIME | server rarity default | small grounded beast | PRODUCTION | candidate |
| 2 | MELLO | MELLO | COMMON | SLIME | JUMP | CURIOUS | BOTTOM | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 3 | MOSSY | MOSSY | COMMON | PLANT | GROUND | SLEEPY | LOWER_CORNER | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 4 | CHIRP | CHIRP | COMMON | BIRD | FLYING | CURIOUS | TOP | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 5 | MONSTER_005 | Button beetle | COMMON | INSECT | EDGE | CURIOUS | EDGE | DAY | TBD | round shell and antennae | PROVISIONAL | — |
| 6 | BUBU | BUBU | COMMON | AQUATIC | JUMP | PLAYFUL | BOTTOM | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 7 | PEBB | PEBB | COMMON | ROCK | GROUND | PASSIVE | NEAR_DOCK | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 8 | PUFF | PUFF | COMMON | SPIRIT | FLOATING | CURIOUS | FREE_AREA | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 9 | MONSTER_009 | Lantern wisp | UNCOMMON | SPIRIT | FLOATING | TIMID | FLOATING_AREA | NIGHT | TBD | hollow flame | PROVISIONAL | — |
| 10 | TIKKI | TIKKI | UNCOMMON | MECHANICAL | GROUND | CURIOUS | BOTTOM | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 11 | MONSTER_011 | Clock crawler | UNCOMMON | MECHANICAL | GROUND | CURIOUS | BOTTOM | FOCUS_SESSION | TBD | gears and short legs | PROVISIONAL | — |
| 12 | MONSTER_012 | Orbit mote | UNCOMMON | COSMIC | FLOATING | PASSIVE | FLOATING_AREA | NIGHT | TBD | ringed sphere | PROVISIONAL | — |
| 13 | MIMI | MIMI | UNCOMMON | MIMIC | STATIC | TRICKSTER | EDGE | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 14 | WISP | WISP | UNCOMMON | SPIRIT | FLOATING | TIMID | FREE_AREA | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 15 | SHADE | SHADE | UNCOMMON | SHADOW | EDGE | TRICKSTER | EDGE | NIGHT | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 16 | EMBER | EMBER | RARE | FIRE | FREE_2D | AGGRESSIVE | FREE_AREA | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 17 | MONSTER_017 | Arch golem | RARE | ROCK | STATIC | SLEEPY | NEAR_DESKTOP_EDGE | ANY_TIME | TBD | stone arch | PROVISIONAL | — |
| 18 | MONSTER_018 | Storm crest | RARE | BIRD | FLYING | AGGRESSIVE | TOP | DAY | TBD | forked crest | PROVISIONAL | — |
| 19 | LUNET | LUNET | RARE | MOON | FLOATING | TIMID | FREE_AREA | NIGHT | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 20 | MONSTER_020 | Long ear | RARE | BEAST | GROUND | TIMID | BOTTOM | NIGHT | TBD | upright ears | PROVISIONAL | — |
| 21 | NOVA | NOVA | RARE | COSMIC | FREE_2D | CURIOUS | FREE_AREA | ANY_TIME | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 22 | MONSTER_022 | Veil spirit | EPIC | SPIRIT | FLOATING | SLEEPY | FLOATING_AREA | NIGHT | TBD | layered veil | PROVISIONAL | — |
| 23 | MONSTER_023 | Ink vortex | EPIC | SHADOW | FREE_2D | TRICKSTER | FREE_AREA | NIGHT | TBD | spiral ink | PROVISIONAL | — |
| 24 | MONSTER_024 | Comet sail | EPIC | COSMIC | FLYING | CURIOUS | TOP | NIGHT | TBD | crescent sail | PROVISIONAL | — |
| 25 | MONSTER_025 | Thorn crown | EPIC | PLANT | STATIC | AGGRESSIVE | NEAR_DOCK | DAY | TBD | radial petals | PROVISIONAL | — |
| 26 | MONSTER_026 | Crystal wedge | EPIC | ROCK | JUMP | AGGRESSIVE | BOTTOM | ANY_TIME | TBD | angular wedge | PROVISIONAL | — |
| 27 | MONSTER_027 | Eclipse halo | SPECIAL | COSMIC | FLOATING | PASSIVE | FLOATING_AREA | SPECIAL_EVENT | TBD | concentric halo | PROVISIONAL | — |
| 28 | NOCT | NOCT | SPECIAL | NIGHT | EDGE | TIMID | EDGE | NIGHT | server rarity default | Production visual design pending | PROVISIONAL | candidate |
| 29 | MONSTER_029 | Aurora ribbon | SPECIAL | AQUATIC | FREE_2D | PLAYFUL | FREE_AREA | SPECIAL_EVENT | TBD | flowing fins | PROVISIONAL | — |
| 30 | MONSTER_030 | Satellite seed | SPECIAL | MECHANICAL | EDGE | CURIOUS | NEAR_DESKTOP_EDGE | SPECIAL_EVENT | TBD | antenna disk | PROVISIONAL | — |

## Validation and review boundary

The existing `npm run test:animation` CI entry now also runs 11 Monster Dex contract tests (no new package dependency or workflow edit). Local AUTOMATED PASS: TypeScript/Vite build; 47 animation/base/Dex tests; 27 presentation/evolution tests; 16 asset tests; 9 automation-policy tests; Tao patch integrity; whitespace check. Asset validation with `--allow-missing` reports zero errors and the existing 26 unprovided optional assets, not production asset completion.

Remote head-bound CI must additionally pass desktop-static, macos-native (Rust deterministic regressions, native link, clippy and focus harness compile), server-java (isolated PostgreSQL Encounter/Battle/Capture/Reward/Collection/Evolution tests), and review-result. Check the PR for the actual final SHA results. Native real desktop launch, focus during typing/clicking, visual acceptance and single-instance interaction are MANUAL_REQUIRED / NOT_RUN; a hosted runner compile is not runtime proof.

No changes to server, migrations, production PNGs, Companion, Rust state/movement/native windows, battle/capture/evolution formulas, or Inventory. At implementation review, Inventory branch changes no files in this PR; expected textual merge conflicts: none at that snapshot. Parallel future edits may change this assessment. Known risks: provisional visual designs and capture tuning remain unapproved; discovery persistence and server-side conditional selection are intentionally future work; content scale is not yet consumed by a Dex UI. Architecture/visual approval and merge remain human decisions.
