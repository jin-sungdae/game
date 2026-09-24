# Alpha Release Hardening v1

Functional baseline: origin/main `0d4d1d7` (Alpha vertical slice #42). Branch `chore/alpha-release-hardening-v1`. MOA/MOKORI/NEBLA, all15 production Monsters and all existing gameplay/economy/progression/persistence contracts are unchanged. No runtime feature, formula, asset, migration, dependency version or Tao patch changes.

Recommendation: **AUTOMATED_READY only when the command below finishes successfully; MANUAL_QA_REQUIRED regardless.** This is not a signed/notarized release candidate or permission to merge/distribute.

## Single automated entrypoint

```sh
npm ci
JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home \
PG_BIN=/opt/homebrew/opt/postgresql@16/bin \
npm run validate:alpha:release -- --output /tmp/luma-alpha-release-new-run
```

Requires macOS, Java21, PostgreSQL16 binaries, Rust/clang, Node/npm and available Gradle/npm dependencies. Output directory must be new. CARGO_TARGET_DIR may point to a normal local build cache. The command has no existing-DB option: it creates separate regression and journey databases in a temporary loopback cluster, runs the actual bootJar and compiled World, shuts down only its own services, and removes its cluster. It never takes production connection details as an input. Logs remain in the output directory. `release-result.json` binds the result to HEAD; record dirty-tree status separately if run before commit. Failures exit nonzero and cannot produce AUTOMATED_READY. Manual status is always MANUAL_QA_REQUIRED.

Existing tests are orchestrated rather than copied: production frontend build; animation/content projection sync; presentation; asset tests; allow-missing optional frames; strict-alpha; required18-base audit; automation policy; Tao integrity; Rust fmt/test/native link/clippy; compile existing launch/single-instance audit harnesses; server tests/bootJar; existing fresh→NEBLA journey and complete restart; offline discovery/interaction; new actual refused/read-timeout tests; real DB-loss/runtime503 and failed startup; whitespace.

The full macOS command is intentionally opt-in, not duplicated in every hosted CI job. Existing CI remains unchanged and runs the new Python policy/asset tests, renderer resolver test and Rust network test through its existing suites. It uses its existing PostgreSQL17 test service; local release smoke specifically requires PostgreSQL16. Native GUI acceptance remains outside CI.

## Gate scope

| Gate | Automated evidence | Boundary |
|---|---|---|
| Frontend | Existing production build, animation and presentation tests | Browser/native interactive QA separate |
| Content | Existing projection sync and all15 identities/961 boundaries | No new content activation |
| Server/Persistence | Isolated tests/bootJar plus new-save existing journey, restart equality and2 histories | Test World/calendar/cooldown clock injection; not wall-clock gameplay |
| Assets | Existing PNG CRC/decompression/RGBA checks plus transparency/nonempty alpha bounds for18 required bases | Optional NOT_SUPPLIED animations allowed; fallback preserved |
| Diagnostic fallback | Actual file dimensions + production BaseAssetLoader/rendererSource for18 paths; full PNG decode separately | Native WKWebView visual observation is manual |
| Network | Connection refused and actual3-second read timeout; stopped-server phase; worker backoff and bounded queue regression | Not a long-running OS/network soak |
| DB failure | Stop only temporary cluster: runtime503 GAME_UNAVAILABLE; fresh bootJar nonzero exit and clear connection error | Server remains alive to report runtime503; startup fails closed |
| Focus | Forbidden activation/key-window API tripwire; nonactivating panel invariants; Tao integrity | Textual guard is not proof of all possible indirect activation |
| Single instance | No-op plugin precedes setup; Rust/native link and existing audit harness compile | Actual second GUI launch is NOT_RUN |
| Performance | Runtime scheduling/network/logging call-site inventory; bounded queues and15-monster decision tests | No CPU/GPU/memory30-minute benchmark claim |
| Logging | Reviewed static call sites; sanitized Rust network errors/server503; disposable password canary absent from failed-startup log | Not a general-purpose secret scanner or guarantee for arbitrary third-party log configuration |

## Static audit rationale

`alpha_release_policy.py` records the reviewed existing runtime call sites in `docs/evidence/alpha-release-runtime-inventory.json`. Additions/removals of threads, channel creation, polling/RAF, selected HTTP calls or logging fail the baseline comparison. Single-instance ordering, queue capacities1/8 and timeouts1s/3s have explicit guards. Tests mutate focus, panel, second-World/thread, polling, queue and logging examples to prove rejection. This is conservative source-level change detection; semantic review is still necessary, and baseline updates require human review of the changed runtime. No production behavior is changed by this policy.

Logging inspection: Desktop backend reduces transport failures to fixed strings and rejects credentials/query fragments in its loopback URL; GameErrors logs exception class only and responds with sanitized503. World state/focus logs are transition-triggered, not unconditional per-tick logs. Optional audit/smoke logging is environment-gated. Existing framework startup diagnostics can expose local connection metadata/SQL context; do not publish raw logs without review. Default operational logs must never be configured to dump Authorization/passwords; the new canary check covers the exercised unavailable-DB startup path only.

## Manual gate / NOT_RUN

[Ordered macOS checklist](alpha-manual-qa-v1.md): typing focus during motion/spawn/rarity/evolution, click versus drag, battle/shop/items/capture, single/multi/negative-coordinate displays with Dock bottom/left/right and Menu Bar, species visuals/facing/anchors/profiles, Reduced Motion, both evolutions, actual5-minute Bond cooldown/Berry, app/server restart, second-instance GUI launch, network recovery and at least30-minute real desktop observation. All begin NOT_RUN. This PR does not run or certify these checks.

## Known limitations, defects and blockers

No gameplay integration defect has been identified; runtime logic and balance remain intact. The release work closes validation gaps, not invented product issues. A failed automated gate blocks AUTOMATED_READY. Pending manual QA blocks a full release-ready recommendation, even if every automated check passes. Signing/notarization, distribution packaging and long-run native telemetry are not certified here. Unknown monster/stage, invalid asset identity and rarity/content mismatch remain fail-closed through existing contract tests.

Classify actual issues using BLOCKER/HIGH/MEDIUM/LOW in the checklist. No synthetic issue is recorded as a discovered defect. Automated repair iteration limit remains3; protected-path human review applies to package.json command registration. No automatic merge.

## Recorded local execution (2026-09-24)

The first complete working-tree run from baseline `0d4d1d7` passed at `/tmp/luma-release-hardening-01` (pre-commit evidence, not a claim about a later SHA): frontend/content/presentation,32 asset tests,21 automation tests,147 Rust tests (16 opt-in ignored; the actual journey ran separately),196 server/PostgreSQL tests, fmt/clippy/native link, both native audit harness compiles, strict-alpha,18 required bases and Tao integrity. Fresh/persistence/offline phases passed. DB-loss returned503; unavailable-DB startup exited1 with a clear connection error and without the disposable password canary. The runner stopped its Spring/PostgreSQL processes.

The first random journey reached MOKORI in8 victories and NEBLA in38 victories, ending Lv6/EXP1520/Bond12/Gold400; these are observations, not new balance targets. Read `live/summary.json`, `history-before.json`, `history-after.json`, `db-failure.json` and `release-result.json` for each run. Final commit verification and CI evidence are reported in the PR, rather than silently attributing this pre-commit run to a future commit.

Automated scope: PASS. Native manual execution: NOT_RUN. Product defects found/fixed: none. Release validation gaps closed: required18-base gate, actual timeout/refused and DB-failure checks, static contract tripwires and a single reproducible entrypoint. Remaining full-release blocker: required manual QA has not been executed; no fabricated crash/data/focus issue is asserted.
