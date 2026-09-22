# Monster Discovery Persistence v0.1

## Design before implementation

Base origin/main a113be1, inspected migrations V1–V8. Add V9 only: separate game.t_monster_discovery aggregate (unique player/monster) and an Encounter-ID receipt ledger. Do not change t_collection or old migrations. A PostgreSQL transaction uses the existing player FOR UPDATE lock, validates server-owned encounter/code/master, inserts the unique receipt, then upserts count/last_seen only for a newly acknowledged encounter. Preserve first timestamp. Lock order matches existing Capture; no JVM mutex. Terminal encounters may acknowledge late placement retries; server can verify ownership/identity, not pixels. Loopback client remains responsible for calling only after accepted World placement.

POST /api/v1/monsters/{code}/discoveries accepts only encounterId. Server resolves LOCAL_PLAYER/master and timestamps; reject unknown/disabled/unready/mismatched content or foreign encounters. GET /api/v1/dex returns30 slots with persisted UNDISCOVERED/DISCOVERED/CAPTURED precedence. Undiscovered slots omit code/name/assets; existing captures remain CAPTURED without discovery migration/backfill. Capture and discovery are independent.

World placement enqueues a bounded notification instead of marking session discovery. Existing backend worker handles it independently, with no new polling loop/thread and no gameplay busy/error/despawn effect. World tick schedules four attempts with5/15/30-second backoff; exhausted jobs park until explicit Dex refresh, capped32 pending encounters. Confirmed server responses/GET alone update discovery. Queue is volatile before acknowledgement; a restart restores committed state. Capture evidence merges monotonically so late discovery or stale snapshots cannot downgrade CAPTURED.

Reuse the existing Collection/Dex UI and Collection API compatibility; load persistent Dex through its refresh path. No Behavior/Movement/asset/weight/formula/Inventory/Evolution changes. Alternatives rejected: counting every retry corrupts counts; adding discovery to t_collection conflates domains; DTO receipt is not placement evidence; localStorage/JVM locking is not server persistence.

Validate constraints, rollback, duplicate/concurrent requests, all15 identities, disabled/invalid policy, capture race and masking. Run real isolated PostgreSQL + Spring + compiled World WISP placement/ack, stop/restart Spring and reconstruct World without capture, confirm persisted DISCOVERED, then a new encounter/capture→CAPTURED. Preserve native focus/UI manual boundary. Architecture approval and merge remain human decisions; no auto merge.

## Implemented contract

- V9 adds only the aggregate and receipt tables. Aggregate has player/master FKs, unique `(player_id, monster_id)`, positive count, timestamp ordering checks and a monster FK index. Receipt has an Encounter FK and primary key. No backfill or Collection rewrite.
- POST body: `{"encounterId":"<server encounter UUID>"}`. Unknown fields/query parameters are rejected. Unknown code returns 404; disabled/unready or mismatched/foreign encounter returns 409. Invalid enabled master metadata fails closed through the existing content validator. A late acknowledgement of a terminal encounter remains valid.
- GET `/api/v1/dex`: 30 entries, `dexNo`, `state`, `rarity`, counters/timestamps. Known entries include `monsterCode`, `monsterName`, `assetIdentity`, `baseAsset`. UNDISCOVERED omits all identity/name/asset fields. CAPTURED takes precedence regardless of discovery history. The existing `/api/v1/collection` remains unchanged.
- Desktop queues only after `place_server_monster` accepts placement. One in-flight discovery, at most 32 pending jobs, four network attempts per refresh cycle. Queue contention does not consume a network attempt and waits five seconds. No new timer/thread. Failure does not set gameplay busy/error or despawn the entity. Boot/explicit Dex refresh fetch persisted data; explicit successful refresh also releases parked retries.
- Receipt insert and aggregate upsert execute under the same PostgreSQL player lock/transaction as the existing Capture lock order. Duplicate receipt is a no-op, including timestamps. Different Encounter IDs increment one aggregate. GET joins Discovery/Collection in one statement; client confirmed Capture evidence is monotonic even before the first complete Dex snapshot.

## Automated and live evidence

Local macOS automated validation: Java/PostgreSQL 137 tests; Rust 140 passed / 13 explicitly ignored live/platform fixtures. The new ignored live test was separately executed twice against a real Spring server and isolated PostgreSQL. Existing Animation/Content/Asset/PIP and Presentation tests pass; asset tests 27, automation tests 9. `npm run build`, `test bootJar`, `cargo clippy --no-deps -- -D warnings`, formatting, diff check and Tao integrity pass. Existing upstream Tao warnings remain; Tao still differs in exactly its three documented files. Optional and strict Alpha validation both pass: all 15 production assets already exist on this base.

Real WISP vertical slice, 2026-09-22:

1. Fresh `luma_discovery_live_test` on isolated PostgreSQL port 55483; Spring port 18097, test-only `LUMA_TEST_DISCOVERY=1` selects WISP without production RNG changes.
2. Compiled Desktop World places encounter `5430cd2c-eb54-4bfb-ae5e-2dc1a3f33f56` at `(880,434)`. POST commits discovery. Duplicate acknowledgement leaves count 1. Collection has 0 rows. First/last timestamp `2026-09-22T08:04:13.825638Z`.
3. Terminate Spring PID 74168, start a new Spring process PID 74384 against the same DB, run the Rust test in another process with a fresh World. GET restores WISP DISCOVERED, count 1, capture count 0, with no entity required for Dex hydration.
4. New encounter `e8c1ebb3-8f29-4cbd-8df2-f4b7821e0723` places at `(246,128)`. Rediscovery gives count 2, preserves first timestamp and advances last to `2026-09-22T08:05:22.987798Z`. Actual Battle/Attack/Capture APIs produce CAPTURED/count 1. A delayed DISCOVERED response cannot downgrade client Capture evidence.

Reproduce with a fresh loopback `_test` database and test-only `./server/gradlew -p server liveValidation`. Set `LUMA_TEST_DISCOVERY=1`, `LUMA_DB_URL`, `LUMA_DB_USER`, `LUMA_DB_PASSWORD`, `LUMA_SERVER_PORT`. Run `cargo test --manifest-path src-tauri/Cargo.toml live_discovery_restart_slice -- --ignored --nocapture` with `LUMA_LIVE_TEST_URL` and `LUMA_DISCOVERY_STAGE=before`; actually stop/start Spring against that same DB, then repeat with stage `after`. RNG switch exists only in test sources and is absent from bootJar.

Additional regression covers duplicate/concurrent distinct acknowledgements, DB transaction rollback including receipt, unknown/disabled/mismatched identity and forged fields, all15 asset identities, undiscovered JSON masking, old captures without discovery, concurrent real BattleService Capture vs Discovery, stale client snapshots, bounded retry/capacity and placement-before-ack behavior. Existing spawn tests now assert pending commands instead of optimistic discovered state.

## Boundaries and known risks

The live slice executes the actual compiled World/HTTP/SQL path; it is not an interactive NSPanel launch or a visual screenshot check. Native foreground typing, mouse, drag, menu, Never Steal Focus and visual Dex checks remain MANUAL_REQUIRED. Hosted macOS compile is not a manual focus audit.

Unacknowledged queue entries are volatile: a Desktop exit before server commit can lose them; a still-active encounter can be reconciled and placed again on restart. A full 32-entry offline queue does not enqueue additional encounters. Four failures park an entry until successful explicit Dex refresh. A committed response lost in transport is safely retried by encounter identity. Server verifies encounter ownership and canonical master, but cannot independently prove on-screen pixels; this remains the existing trusted local Desktop boundary. This is not multi-account/cloud authentication.

Parallel overlap: `main.rs`, `behaviors.rs`, backend worker and Collection projection are shared integration points. No Behavior AI/Movement/weights/formulas/assets/Inventory/Evolution implementation changes. V9 was next after V8 at base a113be1; any parallel migration added before merge requires human coordination. Automatic repair iterations used: 3 (test UUID feature compatibility, stale presentation wiring assertion, FK-ordered test cleanup). No further automatic repair is authorized under the repository limit if another failure occurs. PR remains unmerged; architecture/integration human review is required.
