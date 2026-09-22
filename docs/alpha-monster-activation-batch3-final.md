# Alpha Monster Gameplay Activation — Batch 3 Final v0.1

## Proposal before implementation

Base origin/main4885cbe includes Batch2 #29 and preparation #30. Inspected migration history V1–V7: this branch owns additive V8 only. Use the five reviewed #30 master rows exactly (levels1–3, use_yn=true): SHADE/UNCOMMON/EDGE/50; EMBER/RARE/FREE_2D/20; LUNET/RARE/FLOATING/20; NOVA/RARE/FREE_2D/20; NOCT/SPECIAL/EDGE/1. Names equal codes. Strict-alpha must pass all15 before validation.

Reuse existing Content, Spawn/Encounter, CalendarClock, MovementController, CombatRules, Inventory and Collection. Add five deliveries to the existing byte-exact runtime asset lists and stage only their three readiness flags for validation. Commit activation only after all five production HTTP + Desktop World vertical slices pass. No new engine, formula, art or native change. Keep NIGHT22:00 inclusive to06:00 exclusive; daytime selection resolves the same authoritative encounter without replacement spam. SPECIAL and NIGHT remain independent; EPIC remains fail-closed.

Final pool: COMMON7*100 + UNCOMMON4*50 + RARE3*20 + SPECIAL1 =961. Verify every weighted boundary and exact DB/content identity plus reviewed1–3 level range. The existing master gate needs a narrow reviewed Alpha level-range check because it currently permits arbitrary valid DB ranges; use_yn=false remains excluded by the existing repository query. Do not add content/schema fields or selection logic.

Alternatives rejected: retaining prep provider/master bypasses would not prove production selection; flag-only changes skip live acceptance; desktop probabilities or replacement movement/capture engines violate authority and scope. Retain preparation tests by promoting their fixtures to real production provider/assets and HTTP selection. Preserve disabled/provisional rejection using actual remaining provisional slots or explicit in-memory readiness test inputs.

Separate loopback *_test PostgreSQL databases and test-only deterministic Spring RNG will exercise production POST→placement→movement→same-ID restore→battle/hit→capture/Charm→collection→despawn/cooldown for all5, plus existing10 regression. Native visible focus/input, physical monitors/Dock and human visual/gameplay acceptance remain MANUAL_REQUIRED. Gameplay/architecture review and merge are human decisions; no automatic merge.
