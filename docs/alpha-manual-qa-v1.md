# Alpha v1 macOS Manual QA

All rows start **NOT_RUN / MANUAL_REQUIRED**. A tester must replace Result with PASS or FAIL and provide Evidence; absence of an observed event is NOT_RUN, never PASS. Automated gate results do not fill this sheet.

## Session preparation

Record: candidate commit SHA ___; app bundle/build hash ___; macOS version ___; hardware ___; display layout/resolution/scaling ___; Dock placement ___; Reduced Motion ___; tester/date ___; isolated save identifier ___; server log location ___; video/screenshot location ___. Use a disposable local save/database, never a user production DB. Save original display/accessibility settings and restore after QA. Do not commit credentials or unredacted personal desktop recordings.

1. Run `npm ci`, then the release command in [readiness](alpha-release-readiness-v1.md). Resolve automated failures before candidate QA.
2. Build the candidate using existing `npm run tauri build -- --bundles app` on macOS. Record actual output bundle path and build SHA. Signing/notarization/distribution acceptance is separate; this task does not certify it.
3. Start the existing bootJar against the tester-owned isolated PostgreSQL and point LUMA_GAME_SERVER_URL at its loopback address. Record ports and stop only those processes afterwards.
4. Use a fresh save for progression tests. Keep TextEdit or an IDE open with a disposable document. Enable screen recording only with the tester's consent. Record visible pointer, active application and timestamps.
5. Do not enable LUMA_SMOKE/LUMA_VISUAL_SMOKE for normal acceptance: their scripted behavior is not a full species selector or real player pacing. Existing `scripts/single_instance_audit.m` can be compiled by the release gate and run with an actual app bundle and a new output directory for the dedicated single-instance audit; see [single-instance contract](single-instance.md). Never substitute harness compile for GUI acceptance.

## Ordered checks

| ID | Precondition | Steps | Expected Result | Result (PASS/FAIL/NOT_RUN) | Evidence | Notes |
|---|---|---|---|---|---|---|
| QA-BOOT-01 | Fresh isolated save | Launch server/app; open status/Dex/inventory | MOA Stage1 Lv1 EXP0 Bond0 Gold0; empty inventory/collection; masked undiscovered slots | NOT_RUN | ___ | Record actual bootstrap and UI |
| QA-FOCUS-01 | TextEdit/IDE active | Continuously type while Companion and Monster move for2 minutes | Text remains in editor; no caret/focus loss | NOT_RUN | ___ | Existing manual-focus-test.md also applies |
| QA-FOCUS-02 | Next automatic spawn available | Type continuously across spawn | No activation/key-window change; uninterrupted typing | NOT_RUN | ___ | Record spawn timestamp |
| QA-FOCUS-03 | RARE/SPECIAL arrival observed | Repeat typing across each rarity arrival | Focus retained; no focus restoration workaround | NOT_RUN | ___ | Rare not observed stays NOT_RUN |
| QA-INPUT-01 | Companion idle, interaction ready | Click once, then several cooldown clicks | One interaction; no unintended drag; no menu/input lock | NOT_RUN | ___ | Record Bond before/after |
| QA-INPUT-02 | Companion visible | Drag/release; repeat tiny movement and deliberate drag near boundaries | Existing drag contract; no click award from actual drag; no stuck capture | NOT_RUN | ___ | Test both directions |
| QA-INPUT-03 | Active encounter | Open battle; Attack; use Potion after damage; capture with Charm | Correct buttons, HP and item count; no double consumption or unusable UI | NOT_RUN | ___ | Record battle/item IDs without credentials |
| QA-SHOP-01 | Earned Gold | Buy each item, rapidly double-click; attempt unaffordable purchase | Valid purchases transact once per accepted request; no negative Gold/items; busy UI guards work | NOT_RUN | ___ | Another funded request is a new purchase, not idempotent replay |
| QA-DISPLAY-01 | Single monitor; Dock bottom | Move/drag and observe automatic placements near all edges/Menu Bar | No clipping or unsafe placement; bottom anchor stable | NOT_RUN | ___ | Record visible/safe bounds |
| QA-DISPLAY-02 | Dock left then right | Repeat prior placement/drag checks after each Dock change | Dock/Menu Bar exclusions update; no entity inside unsafe area | NOT_RUN | ___ | Restore original Dock |
| QA-DISPLAY-03 | Multiple monitors | Move pointer/entities between displays; spawn on eligible display | Correct coordinate and safe-area selection, no duplication/clipping | NOT_RUN | ___ | Record arrangement/scaling |
| QA-DISPLAY-04 | Monitor left/below primary (negative coordinates) | Repeat movement, drag, spawn and edge behavior | Negative coordinates retained correctly; no jump to origin | NOT_RUN | ___ | If hardware unavailable retain NOT_RUN |
| QA-VISUAL-01 | Species checklist below | Observe each species in both facings and movement phases | Correct identity/scale/bottom anchor; no diagnostic shape or clipping | NOT_RUN | ___ | Fill all15 rows |
| QA-RARITY-01 | Each rarity observed | Observe COMMON/UNCOMMON/RARE/SPECIAL arrival | Correct presentation; no excessive flash or activation | NOT_RUN | ___ | Preserve rarity evidence separately |
| QA-RARITY-02 | Reduced Motion OFF then ON | Repeat representative arrival/movement/evolution | Reduced-motion policy respected; no visual/focus disruption | NOT_RUN | ___ | Restore system preference |
| QA-BOND-01 | Fresh interaction ready | Record Bond; click; click during cooldown; wait real5 minutes; click | +1, then0 without cooldown extension, then+1 | NOT_RUN | ___ | Record wall-clock times; no timestamp injection |
| QA-BOND-02 | Berry owned, interaction cooling | Use Berry; inspect inventory/Bond/cooldown | Berry−1, Bond+1 independently; cooldown not reset | NOT_RUN | ___ | Compare server/UI |
| QA-EVO-01 | MOA Lv3/Bond5; earned via play | Check AVAILABLE; evolve; observe Glow→Reveal | MOA until correct transition; MOKORI identity/asset/movement; one history | NOT_RUN | ___ | Do not SQL-edit progression |
| QA-FOCUS-04 | Evolution available, editor active | Type across both MOKORI and NEBLA Glow/Reveal | Editor stays active; no lost keystrokes | NOT_RUN | ___ | Companion click itself must not take keyboard focus |
| QA-EVO-02 | MOKORI Lv6/Bond11 | Confirm LOCKED; Berry/interaction→12; evolve | AVAILABLE then NEBLA; real stage03 PNG; stable anchor/motion; no diagnostic fallback | NOT_RUN | ___ | Capture Glow and Reveal frames |
| QA-RESTART-01 | Uncaptured discovered species | Quit app and server; restart both | DISCOVERED remains without invented capture | NOT_RUN | ___ | Record species before/after |
| QA-RESTART-02 | NEBLA and varied inventory/collection | Record Stage/Level/EXP/Bond/Gold/items/Dex; quit and restart both | All values identical; two evolution histories; no repeated evolution effect | NOT_RUN | ___ | Also check after app-only restart |
| QA-INSTANCE-01 | Candidate running | Open second app via LaunchServices and direct bundle executable | Secondary exits, no independent World/panels; primary uninterrupted and no activation | NOT_RUN | ___ | Existing audit executable may supplement observation |
| QA-NET-01 | App running, test server owned | Stop server; keep moving/clicking; restart server | No crash/spin/flood; local motion continues; bounded retry and recovery | NOT_RUN | ___ | Record request/log timestamps |
| QA-LONG-01 | Normal build and disposable save | Run at least30 wall-clock minutes; sample Activity Monitor and request logs at0/5/15/30min | No sustained memory growth, abnormal CPU, request spam, duplicated entities, stuck monsters, focus theft or artifacts | NOT_RUN | ___ | Record raw samples/workload; synthetic tick tests do not replace this |

## Species visual worksheet

There is no general production GUI selector for all15 species. Use actual server encounters; existing deterministic World tests cover all15 but do not count as visual observation. Do not activate unapproved content, edit production weights or invent a debug command. If a rare species is not seen, retain NOT_RUN and schedule a tester-owned controlled fixture session through the existing test infrastructure; explicitly label fixture evidence.

For every row record: asset, scale, bottom-center anchor, RIGHT source/both facings, movement, clipping, display/Dock setup. Across the full sheet include GROUND/JUMP/FLYING/FLOATING/STATIC/EDGE/FREE_2D and BOTTOM/TOP/NEAR_DOCK/LOWER_CORNER/FREE_AREA/EDGE constraints from the current content registry.

| ID / species | Precondition | Steps | Expected Result | Result | Evidence | Notes |
|---|---|---|---|---|---|---|
| QA-SPEC-PIP | Encounter PIP | Observe both facings/movement | Correct registered visual/profile; no clipping | NOT_RUN | ___ | ___ |
| QA-SPEC-MELLO | Encounter MELLO | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-MOSSY | Encounter MOSSY | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-CHIRP | Encounter CHIRP | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-BUBU | Encounter BUBU | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-PEBB | Encounter PEBB | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-PUFF | Encounter PUFF | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-TIKKI | Encounter TIKKI | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-MIMI | Encounter MIMI | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-WISP | Encounter WISP | Same procedure | Same contract | NOT_RUN | ___ | ___ |
| QA-SPEC-SHADE | NIGHT encounter | Observe appearance and motion | Correct NIGHT/FLOATING contract | NOT_RUN | ___ | Time recorded |
| QA-SPEC-EMBER | Encounter EMBER | Same procedure | Correct registered visual/profile | NOT_RUN | ___ | ___ |
| QA-SPEC-LUNET | NIGHT encounter | Same procedure | Correct NIGHT contract | NOT_RUN | ___ | Time recorded |
| QA-SPEC-NOVA | Encounter NOVA | Same procedure | Correct registered visual/profile | NOT_RUN | ___ | ___ |
| QA-SPEC-NOCT | SPECIAL/NIGHT encounter | Observe EDGE placement and arrival | Correct SPECIAL/NIGHT/EDGE; focus retained | NOT_RUN | ___ | Rare observation may need separate session |

## Issue classification and sign-off

| Severity | Criteria | Release handling |
|---|---|---|
| BLOCKER | Data corruption, crash, focus theft, duplicate economy mutation, lost evolution state, unusable UI, credential disclosure | Stop release; preserve evidence; repair and rerun related gates |
| HIGH | Frequent blocked gameplay/restart inconsistency or required species/asset inaccessible with no practical workaround | Hold candidate until resolved or explicit human decision |
| MEDIUM | Limited visual/layout or recoverable interaction issue with usable workaround | Record affected environments; human disposition required |
| LOW | Cosmetic/text issue without gameplay, focus or data impact | Track and decide explicitly |

These are classification examples, not discovered issues. Issue record: ID ___ / severity ___ / candidate SHA ___ / exact steps ___ / expected vs actual ___ / evidence ___ / owner ___ / disposition ___. Sign-off: automated evidence ___; unresolved issues ___; all required manual rows completed ___; reviewer/date ___; decision ___. No automatic merge or release approval.
