# Battle / Capture / Reward v0.1 — implementation design

Server JDBC domain extends existing backend; Desktop remains presentation only. Existing native panels, behavior, movement, animation, assets, single instance and Tao remain unchanged.

Lock order: local player -> encounter -> battle (SELECT FOR UPDATE). This preserves the existing per-player encounter serialization and adds explicit battle locking. Concurrent attacks are distinct serialized turns; without a request token, identical network requests cannot be deduplicated. No automatic mutation retries on Desktop. Terminal requests never pay again.

V3 additive migration introduces battle/reward/collection plus PLAYER_DEFEATED encounter status. Battle CAPTURED/ESCAPED distinguish non-combat resolution from VICTORY/DEFEAT. No rewrite of V1/V2. Capture active success pays no victory reward. Defeat maps to PLAYER_DEFEATED. Ignore maps to ESCAPED. Battle ACTIVE suspends spawn expiration. VICTORY resets expires_at to a 60-second capture opportunity; timeout or failed post-victory capture resolves DEFEATED, no counterattack. Post-victory capture is one attempt; active failures consume a turn/counterattack. No arbitrary battle timeout in v0.1; explicit Ignore resolves abandoned active battles.

Alternative considered: marking encounter DEFEATED immediately on victory prevents capture and violates requested loop. Keeping ordinary spawn TTL in active battle would despawn PIP mid-turn. We instead expose expirationSuspended + battleId in encounter presentation, preserving non-null timestamps for old contracts.

Formulas stay in CombatRules. Reward insert and gold/EXP/bond/level updates share the victory transaction; UNIQUE(encounter_id) prevents repeat reward. Collection UPSERT shares capture resolution transaction. Level is derived from total EXP [0,100,300,600,1000], capped at 5, never evolves species.

Validation pending. Existing PR10 automated UI activation attribution remains MANUAL_REQUIRED; no new focus acceptance claim.

## Schema and ownership

`V3__battle_capture_reward.sql` adds `t_battle`, `t_reward`, `t_collection` and expands the encounter status CHECK. Existing V1/V2 are byte-for-byte unchanged. Battle snapshots both attacks/max HP at start, so future level changes never alter an in-flight battle. HP CHECKs enforce 0..max. Battle encounter UNIQUE, reward encounter UNIQUE and collection (player,monster) UNIQUE complement row locks. No data deletion/backfill or existing table rewrite.

Server alone selects stats, damage, random capture outcome, reward and progression. React renders DTOs, HP progress bars, response event text, rewards and collection. Rust retains presentation only. No damage prediction, offline mutation queue or new animation assets.

## Lifecycle

- Encounter ACTIVE without battle: original 60-second lazy expiration -> EXPIRED.
- Battle ACTIVE: encounter stays ACTIVE; spawn TTL suspended (including Desktop visual lease). No automatic combat timeout. Restart restores via encounter battleId + retry-safe Start/GET battle.
- Monster HP zero: battle VICTORY, encounter remains ACTIVE for 60 seconds, reward paid atomically once. `expiresAt` is reset to the capture-window deadline.
- Capture successful during ACTIVE battle: battle CAPTURED, encounter CAPTURED, collection increments, no victory reward.
- Capture successful after VICTORY: battle remains VICTORY (combat result retained), encounter CAPTURED, existing reward unchanged.
- Failed ACTIVE capture: one counterattack and turn increment. May retry explicitly while companion survives. Companion HP zero -> battle DEFEAT, encounter PLAYER_DEFEATED, no reward.
- Failed VICTORY capture: no counterattack, encounter DEFEATED, no further attempt. Window timeout also resolves DEFEATED through lazy expiration.
- Ignore: encounter ESCAPED; ACTIVE battle becomes ESCAPED; existing VICTORY remains its combat outcome. Close hides only the popup; it is distinct from Ignore.
- Terminal attack returns 409; resolved capture returns 409; neither rolls RNG nor changes balances. GET battle permits safe reconciliation after an ambiguous network result.

## Formulas

Companion max HP 100, attack `10 + level*2`. Monster max HP `20 + level*10`, attack `3 + level*2`. Player hits first, and a surviving monster counters. No random damage, critical, defense, elements or skills.

COMMON capture chance = clamp(0.35 + (1 - hp/maxHp)*0.50, 0.05, 0.95). Server RandomSource draws an integer in [0,1,000,000); compares to the chance threshold. Full/half/zero HP chances are 35/60/85%. Unknown rarity is INVALID_STATE, never silently assigned a chance.

Victory Gold = monster level*10; total EXP += level*20; Bond +=1. Derived level thresholds 0/100/300/600/1000 cap at 5. Total EXP keeps accumulating. No evolution execution.

## Transactions and concurrency

All mutating operations serialize on LOCAL_PLAYER, then encounter, then battle. Explicit `SELECT ... FOR UPDATE` battle lock guards HP/turn/status. Existing encounter creation/expiration keeps its player-lock contract. Reward insert, player gold, companion EXP/Bond/level, combat state and capture-window deadline commit together. Any SQL failure rolls back the entire attack. GameFault validation errors may commit only preceding lazy expiration; mutation code does not throw GameFault after writes.

Two simultaneous attacks while still active consume two distinct sequential turns, not the same turn twice. Concurrent final blows yield one success and one terminal rejection. Requests have no idempotency key by contract; a new explicit user attack is a new turn. Desktop never automatically retries POST on transport failure. A timed-out attack may have committed: use Refresh before explicitly requesting another turn.

Capture success updates collection with PostgreSQL UPSERT and resolves the encounter in the same transaction. The next concurrent request observes resolution and returns CAPTURE_ALREADY_RESOLVED. Post-victory failure resolves immediately, guaranteeing one attempt even concurrently. First captured timestamp is preserved on UPSERT.

## HTTP contract

All routes use `/api/v1`. No mutation request accepts non-empty JSON fields or query parameters.

| Method | Path | Result |
|---|---|---|
| GET | `/game/bootstrap` | Latest player and companion progression |
| POST | `/encounters` | Existing encounter selection/reuse |
| GET | `/encounters/active` | Encounter or 204, with battleId and expirationSuspended |
| POST | `/encounters/{id}/battle` | Create once or return existing battle |
| GET | `/battles/{id}` | Authoritative battle and encounter status |
| POST | `/battles/{id}/attack` | Entire player/counter turn, events and reward |
| POST | `/battles/{id}/capture` | Success/chance, battle/encounter IDs/status, monster, collection, battle DTO |
| POST | `/encounters/{id}/ignore` | ESCAPED resolution |
| GET | `/collection` | firstCapturedAt ASC, monsterCode ASC |

Battle DTO: battleId, encounterId, turn, status, encounterStatus, companion {hp,maxHp}, monster {hp,maxHp}, events[], reward {gold,exp,bond} or null. Capture exposes chance, never the random roll. Collection DTO includes monsterCode/name, count and first/last timestamps. Reward on later GET is the persisted receipt, not another payment.

Error DTO `{code,message}`: ENCOUNTER_NOT_FOUND/BATTLE_NOT_FOUND (404); ENCOUNTER_EXPIRED, BATTLE_ALREADY_TERMINAL, CAPTURE_ALREADY_RESOLVED, INVALID_STATE (409); INVALID_REQUEST (400); GAME_UNAVAILABLE (503). No SQL/stack traces in custom responses. Desktop maps known codes to recoverable messages; malformed/unknown DTOs cannot replace presentation.

## Desktop and performance

One existing backend thread, one bounded command channel (capacity 1), bounded event channel (8). StartBattle/Attack/Capture/LoadCollection/Ignore/Refresh are explicit commands. Presentation busy guard rejects repeated clicks until completion/error. HTTP remains off AppKit, with existing 1-second connection/3-second request limits and 64KiB response cap. The same five-second reconciliation poll fetches battle only when the interaction popup is open. No additional timer loop or busy wait.

Existing interaction NSPanel is resized from 160x140 to 240x300 logical points for compact HP/buttons/result; its native class, focusability, nonactivating style and bounds clamp remain unchanged. Terminal result remains visible until Close, positioned near MOA when PIP despawns. No new panel/window is created. Server-backed PIP click starts/resumes battle; debug PIP is not an authoritative encounter. Bootstrap refresh follows explicit commands so World receives updated progression.

Added DB work is small locked SELECT/UPDATE transactions plus collection query on request. Local MVP player serialization intentionally favors correctness over throughput. No CPU/memory benchmark was performed; short runtime observation is not a benchmark.

## Local validation

Use the existing local backend instructions in `game-backend-v01.md`. No new service/dependency/version upgrade is required. Server defaults 8081; verification used 18081 and dedicated PostgreSQL on 55439, database `luma_game_test`. Existing development/other user databases were untouched.

`./server/gradlew -p server test bootJar` uses real isolated PostgreSQL. New integration fixtures reset only *_test data. `liveValidation` is an explicit JavaExec test harness guarded to loopback *_test DB; fixed RNG lives only under src/test and is absent from bootJar. `LUMA_TEST_CAPTURE_MODE=failure` forces capture failure for deterministic failure/defeat validation; no production RNG override was added.

Live World tests (explicit --ignored execution with LUMA_LIVE_TEST_URL):
- Production RNG: encounter `3d5f5f1b-e6d8-4935-aaa8-31bfc70928d2`, battle `34ac43cb-63b5-4f30-af05-e0541c71c7d5`: victory, capture success, persisted Gold 10 / EXP 20 / Bond 1 / Level 1, collection 1, World despawn, Ignore scenario PASS.
- Test-only failure RNG: battle `c6967760-2bbe-4394-82d0-bf535f6a81c3`, 20 failed captures -> DEFEAT / PLAYER_DEFEATED; battle `f9677728-14a2-482d-88ea-8395f6f6fd05`, victory capture failure retains HP 90, no second reward/retry. PASS.
- Original live encounter-to-World test separately executed PASS.

These are actual HTTP/DB plus Rust World validations, not claims of physical mouse/typing validation.

## Known risks / human review

Physical mouse/typing focus, compact popup usability/visual fit, perceived responsiveness and actual Dock overlap remain MANUAL_REQUIRED. PR10 recorded application activation during tool-driven UI interaction with unresolved tool-vs-native attribution; this PR does not change focus/native policy and does not resolve that observation. Do not infer focus PASS from server/World tests or CI.

ACTIVE battles deliberately have no timeout; a user must reopen/Ignore an abandoned battle. Server and Desktop must be upgraded together because older clients do not honor expirationSuspended. Capture chance currently supports COMMON only. This remains unauthenticated loopback LOCAL_PLAYER MVP; no production security/online multiplayer claim. No offline queue, request-id deduplication, reward economy balancing or cloud deployment.

Final test/CI counts and native launch evidence are appended after verification. PR remains unmerged; human review required for domain lifecycle, additive schema and existing focus risk.

## Final local results

- AUTOMATED server: 34 PASS (22 BattleIntegration + 9 existing GameIntegration + 3 selector), actual PostgreSQL 17.10 with fresh V1/V2/V3, no H2. bootJar PASS.
- AUTOMATED Rust: 57 PASS; 3 explicit live tests separately executed PASS (normal test run marks these ignored because a dedicated live server is required).
- Animation 27 PASS, asset validator tests 12 PASS, policy 9 PASS; npm build, cargo clippy, Tao integrity PASS. Existing 18 upstream Tao warnings remain unchanged.
- PLATFORM_REQUIRED actual `tauri dev` launched with server on 18081 and bootstrap/PIP reconciliation. Non-interactive focus audit: PID 53265, Chrome foreground start/end, 31.27 seconds, activation=0/keyWindows=0, normal panel cleanup. This sample is not a mouse/typing test or 20-launch acceptance run.
- Environment-only initial failures: duplicated node_modules type directories fixed with npm ci; localhost fixture tests needed sandbox network permission and were rerun. No tests removed/relaxed.
- All validation servers and test containers are stopped after verification; existing LUMA development PostgreSQL volume and unrelated processes are preserved.
- New dependencies: none; Tauri/Tao and server dependency versions unchanged. Existing architecture retained; only popup size and API/presentation integration changed.

Changed areas: additive SQL V3; CombatRules/BattleDtos/BattleService/BattleController/GameFault plus existing encounter repository DTO/errors; test-only live harness and Gradle task; Rust backend DTO/commands/worker/presentation and World lease adapter; compact React popup/types/styles/menu size; server/Rust tests; AGENTS scope and this document. No PNG, animation timing, personality, movement controller, native panel or Tao patch edits.

Review correction iteration 1: reset only developer PIP presentation when spawning after a resolved server battle, preventing a debug PIP click from reusing an old authoritative battle. Added deterministic regression; native/engine architecture unchanged.
