# Local Game Backend v0.1

## Architecture and ownership

Java 21 / Spring Boot 3.5.16 / Gradle 8.14.3 server lives in `server/`.
Spring Web exposes DTOs, Spring JDBC owns SQL, PostgreSQL persists game state and
Flyway manages the `game` schema. Jackson serializes DTO records. No JPA,
Hibernate, Redis, authentication framework or WebSocket is included.

Desktop keeps its existing Rust Companion/Movement controllers, asset/animation
pipeline and native panels. The new Rust backend worker fetches bootstrap at
startup, restores an existing active encounter and processes explicit encounter
requests. It never calls AppKit or focus APIs. Main-thread integration only applies
messages to the existing World and PIP presentation.

Server owns player/companion persistence, master selection, UUID, level, rarity,
spawn/expiry timestamps and ACTIVE/EXPIRED status. Desktop owns animation,
movement, proximity reaction and popup display. A local visual disappearance is
not a persisted status transition. Battle/Capture remain debug logs; no outcomes,
rewards, inventory, leveling or evolution execution are implemented.

## Schema and migrations

- `V1__game_schema.sql`: `m_species`, `m_species_evolution`, `t_player`,
  `t_player_companion`, `m_monster`, `t_encounter`, named PK/UK/FK constraints,
  checks and lookup/partial indexes. Timestamps use timestamptz.
- `V2__local_master_seed.sql`: MOA/RUU/NOX; MOA stages 1–5 are MOA, MOKORI,
  NEBLA, SYLVAON, AETHERIA. RUU/NOX only stage 1 because repository master
  documentation has no confirmed later names (TODO, no invented names).
- LOCAL_PLAYER: player_id 1, gold 0, one active MOA stage 1 / level 1 / exp 0 /
  bond 0. `uk_companion_one_active` enforces at most one active companion per
  player; bootstrap/create require exactly one at the application boundary.
- PIP: COMMON / GROUND / levels 1–3 / encounter_weight 100 / use_yn true.
- Encounter UUID PK, player/monster FKs, level/range/time/status checks.
  `uk_encounter_one_active` is unique on player_id WHERE status='ACTIVE'.
  Expiration and player-history indexes support lazy lifecycle queries.

Migrations are additive to this new game schema and do not modify external
application databases. Use a dedicated LUMA database. Never run tests against a
production/user database. Tests enforce a *_test database name before migration.

## API contracts

Default origin: `http://127.0.0.1:8081`. LOCAL_PLAYER is chosen by the server;
client cannot submit a player ID. APIs return DTOs, not database entities.

`GET /api/v1/game/bootstrap` → 200:

```json
{
  "player": {"playerId":1,"name":"LOCAL_PLAYER","gold":0},
  "activeCompanion": {
    "playerCompanionId":1,"species":"MOA","evolutionStage":1,
    "evolutionName":"MOA","level":1,"exp":0,"bond":0
  }
}
```

`POST /api/v1/encounters` accepts no fields (empty body or `{}`). Any submitted
fields/query parameters, including monster/rarity/level/UUID/expiry, return 400.
Creation and reuse both return 200 with the same contract:

```json
{
  "encounterId":"<server-generated UUID>",
  "monster":{"code":"PIP","name":"PIP","level":2,"rarity":"COMMON","movementProfile":"GROUND"},
  "spawnedAt":"<ISO-8601 UTC instant>",
  "expiresAt":"<spawnedAt + 60 seconds>"
}
```

`GET /api/v1/encounters/active` lazily expires the player's encounter and returns
200 with the same DTO or 204 when none is active. It never creates a new encounter.
This endpoint supports reconnect/restart and Desktop reconciliation.

Invalid master/player/active-companion data or DB failures return 503 with a
bounded `GAME_UNAVAILABLE` error DTO; SQL/credentials are not returned to clients.
Invalid requests use standard Spring HTTP errors. Disabled/zero-weight masters
are not selectable. The separate MonsterSelector receives an injectable
RandomSource, performs weighted selection and independently samples the inclusive
level range. It does not hard-code PIP as the result.

## Transaction and expiration

Create and active lookup each use a single Spring transaction:

1. `SELECT ... FROM game.t_player WHERE player_id=1 FOR UPDATE`.
2. Read `clock_timestamp()` **after** obtaining the row lock (not transaction
   start time, which could be stale after lock waiting).
3. UPDATE ACTIVE rows with expires_at <= sampled time to EXPIRED, setting
   resolved_at/updated_at.
4. Return an existing ACTIVE, or for POST select a master/level, generate UUID,
   insert with a 60-second TTL and return its DTO.
5. Commit. A retry returns the existing ACTIVE UUID until it expires.

The player-row lock serializes concurrent requests even when no encounter exists;
locking a missing encounter row alone would not do that. PostgreSQL's partial
unique index independently rejects duplicate ACTIVE rows, including direct SQL.
Default READ COMMITTED observes the previous request's committed encounter after
waiting. No JVM-only mutex, scheduler or distributed lock is used. Transaction
failure rolls back all changes; a subsequent active lookup can perform expiration.

Statuses DEFEATED/CAPTURED/ESCAPED exist only as schema foundation. APIs implement
ACTIVE and EXPIRED only. Unqueried expired rows remain ACTIVE in storage until the
next lookup/create by design; the index deliberately does not depend on `now()`.

## Desktop integration and failure policy

`LUMA_GAME_SERVER_URL` defaults to the local origin above. For this unauthenticated
MVP, the client permits only loopback HTTP origins, disables proxies and redirects,
limits responses to 64 KiB, and uses 1-second connect / 3-second request timeouts.
No frontend CORS/CSP permission expansion or HTTP call from React is needed.

- Startup bootstrap is parsed and stored on World. The seeded active MOA remains
  the existing local Companion; remote species switching is not introduced.
- MOA right-click now queues a server Encounter request. No selection fields are
  sent. The callback is nonblocking; the request channel has capacity one.
- Existing menu actions are explicitly labelled `Debug: Spawn PIP` / `Debug:
  Despawn PIP`; existing LUMA_SMOKE is the developer-only lifecycle path.
- Server PIP + GROUND maps to the existing single PIP entity/panel. Repeated UUIDs
  preserve position/state; a changed UUID replaces the one presentation. Unknown
  monster/profile is logged and safely skipped.
- Existing PIP roaming/proximity/popup behavior is reused. Debug despawn cannot
  resolve a server-owned encounter. Close only closes its popup.
- Worker polls active status every 5 seconds and retries failed bootstrap. Failures
  are logged on transition, not every frame; local Companion keeps running. No
  fabricated offline encounter or offline persistence write is performed.
- Server timestamps determine the presentation lease. Remaining time is calculated
  when the main thread consumes the response, then uses its existing monotonic
  tick. Stale queued replies cannot receive a fresh TTL. On expiry/204, reuse the
  existing despawn animation. Server alone writes EXPIRED. Local/system clock
  skew may affect the visual deadline; this is a same-host MVP assumption.
- At most eight pending worker events; no network call holds a World lock or runs
  on AppKit's main thread. No new focus/activation behavior is introduced.

No server authentication is intentionally implemented. Bind is loopback only;
the server rejects browser Origin headers and non-loopback Host names to reduce
web-origin access. This is not isolation from other local processes. Do not expose
this service/DB to a LAN or cloud as an authenticated game server.

## Local execution

Requirements: Java 21, Python 3 for existing asset tests, Node/npm, Rust and a
PostgreSQL instance. Docker is optional and only runs the database.

On the validated Mac Java 21 already exists at `/opt/homebrew/opt/openjdk@21`;
set JAVA_HOME in the shell (system default Java was not changed):

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@21
# First run only: create an ignored local credential file without overwriting one.
test -e server/.env || (umask 077; printf 'LUMA_DB_PASSWORD=%s\n' "$(openssl rand -hex 24)" > server/.env)
set -a
. server/.env
set +a
docker compose --env-file server/.env -f server/compose.yml up -d
./server/gradlew -p server bootRun
```

The compose database is `luma_game`, user `luma`, port 55432, with a dedicated
named volume. Retain the original local password for that volume. Passwords are
not committed. A supplied PostgreSQL instead uses LUMA_DB_URL (JDBC URL),
LUMA_DB_USER and LUMA_DB_PASSWORD. Existing databases are never discovered/reused
automatically. Flyway applies migrations on server startup.

In another terminal:

```sh
npm ci
export LUMA_GAME_SERVER_URL=http://127.0.0.1:8081
npm run tauri -- dev
```

If 8081 is occupied, leave that process alone: set LUMA_SERVER_PORT=18081 for
Spring Boot and LUMA_GAME_SERVER_URL=http://127.0.0.1:18081 for Desktop. No backend
is required to continue local Companion behavior.

Build the distributable server with `./server/gradlew -p server bootJar`; run
`java -jar server/build/libs/luma-game-server-0.1.0.jar` with the same environment.
The application is a local Java process, not forced into Docker.

## Tests and validation

Server `./server/gradlew -p server test` requires a dedicated *_test PostgreSQL.
Configure LUMA_TEST_DB_URL, LUMA_TEST_DB_USER, LUMA_TEST_DB_PASSWORD. Default test
URL is jdbc:postgresql://127.0.0.1:55439/luma_game_test. Tests modify only that
explicit test database; CI provisions a disposable PostgreSQL with generated
credentials and runs Java 21 tests/bootJar. No H2 substitution or skipped DB tests.

- Server: 12 PASS — weighted boundaries, seeded replay, invalid masters;
  bootstrap/seed/evolution/player/active companion; TTL/create/reuse; lazy GET/POST
  expiry/replacement; two concurrent HTTP POSTs; direct DB uniqueness/FK
  violations; invalid DB state; rejected client selection fields; browser Origin.
- Desktop Rust: 50 PASS (43 existing + 7 API/mapping tests). One live integration
  test is explicitly ignored in the normal suite and run separately below.
- Live vertical slice: 1 PASS against actual Spring Boot and PostgreSQL 17.10:
  bootstrap → POST/retry → active GET → Rust World PIP spawn/roam/visual expiration.
  Run with `LUMA_LIVE_TEST_URL=http://127.0.0.1:18081 cargo test --manifest-path
  src-tauri/Cargo.toml live_postgres_server_to_desktop_world_vertical_slice -- --ignored`.
- Animation/registry 27 PASS; asset validator 12 PASS; policy regression 9 PASS.
  Scaffold asset validation: 18 PENDING clips, unchanged/no PNGs added.
- npm build, application clippy, Rust formatting, Tao integrity, bootJar: PASS.
- Actual NSPanel mouse/typing/focus validation and CPU/memory benchmark: NOT_RUN.
  The live integration test verifies HTTP/DB/World behavior, not native rendering.

The local validation server used port 18081 because 8081 already had another
process. It used only a newly created isolated test database; existing apps/DBs
were left untouched. The temporary test server/container are stopped after tests.

## Dependencies and known risks

Server versions and wrapper are pinned; Gradle distribution checksum is included.
Rust adds direct reqwest/chrono/uuid/serde_json usage at already locked versions
and activates HTTP blocking/DTO features; Tauri 2.11.5, Tao and native architecture
are unchanged. No new npm dependency. AGENTS scope is updated for this explicitly
requested backend milestone; protected changes still require human review.

The background worker adds bounded I/O, a thread and small DTO caches; real
resource measurements are pending. Server JDBC pool max is six. Local restart
restores the same ACTIVE encounter via GET; API retries are idempotent only within
its ACTIVE lifetime. There is no idempotency key covering an already expired
encounter, offline encounter queue, multi-player identity, rate limit, authenticated
client or cloud deployment in v0.1. Master changes after spawn can affect joined
code/name/profile; rarity/level/timestamps are persisted encounter snapshots.

References: [Spring Boot 3.5 requirements](https://docs.spring.io/spring-boot/3.5/system-requirements.html),
[PostgreSQL row locks](https://www.postgresql.org/docs/17/explicit-locking.html),
[partial indexes](https://www.postgresql.org/docs/17/indexes-partial.html).
