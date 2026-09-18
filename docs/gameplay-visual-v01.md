# Gameplay Visual Integration v0.1

Presentation-only extension of PR11. Cozy cream/green MOA and smaller cream/brown diagnostic PIP; no new PNG or character design. Keep existing 240x300 interaction NSPanel and all native focus flags.

Before implementation: events[] currently contains names only. Client-derived damage would violate server authority. Add optional presentationEvents [{type,damage}] to Battle DTO, computed on the server from the existing resolved HP decrease. Preserve original events[], formulas, locking, lifecycle, schema and migrations. Alternative of estimating damage or copying CombatRules into Desktop is rejected.

A separate Rust presentation controller consumes authoritative DTOs immediately, deduplicates transient responses, and schedules a bounded cue queue on the existing 33ms world tick. Rendering receives phase/damage/reward/level feedback only. No per-damage window/timer, HTTP on AppKit, or authoritative HP interpolation. Motion is CSS on an inner visual wrapper, independent of sprite animation/world position/anchor.

Implementation and validation pending. Physical mouse/typing focus remains MANUAL_REQUIRED; PR10 tool-driven activation attribution is not resolved by this feature. No automatic merge.

## Visual principles and layers

The same 240x300 interaction panel now uses warm cream surfaces, muted green accents, compact HP meters and quiet secondary actions. Numeric HP and the words normal/warning/critical supplement color: >50% normal, 25–50% warning, <25% critical. Only CSS width transitions; authoritative HP values apply immediately.

MOA keeps the existing diagnostic shape in cream/green. PIP uses the same diagnostic renderer at 80% scale with cream/brown accents. Neither is production artwork. No PNG, font, library or new window was added.

`src/presentation/gameplay.css` owns gp-prefixed selectors/keyframes. Independent pose/impulse/visual wrappers preserve bottom-center alignment, facing flip and the existing asset renderer's lifetime. Transient effects never remount CompanionVisual or replace AnimationController timing. Production attack/hit/defeat/capture clips can later replace the named effect slots in presentation/model.ts; this PR neither invents clips nor changes manifests.

## Presentation state and event sequence

`src-tauri/src/presentation` is separate from authoritative Battle status and CompanionState. IDLE, REQUESTING, PLAYER_ATTACK, MONSTER_HIT, MONSTER_ATTACK, PLAYER_HIT, VICTORY, CAPTURING, CAPTURE_SUCCESS, CAPTURE_FAIL, REWARD, LEVEL_UP and ERROR form a transient cue timeline. It runs on the existing world tick; there is no separate timer per effect or number. Queue capacity is 24; oldest pending cues may be dropped under excessive input rather than accumulating unbounded latency. Explicit new requests supersede stale attack effects, while pending reward/level cues are retained across capture. Server snapshots never wait for the queue.

Battle ID/turn deduplication prevents GET/restore snapshots and repeated responses from replaying damage/rewards. Older server contracts without presentationEvents never cause locally guessed damage. Typed events from current server carry actual clamped HP decrease, including a final 6-damage hit when only 6 HP remains. Existing string events are retained for compatibility. Capture failure counterattack carries only MONSTER_ATTACK damage. GET returns no transient events.

Attack impulse: 140ms. Hit feedback: 160ms. Damage number: 650ms. Ordered player impulse -> monster hit/number -> counter impulse -> player hit/number. CSS transforms never write world coordinates or change native frames.

VICTORY snapshot immediately marks PIP defeated; cue playback adds feedback and a 2.5-second reward toast from the server receipt. Confirmed bootstrap level increases for the same companion create a 2-second level-up cue; initial bootstrap never fabricates a level-up. No evolution effects.

## Capture sequence

Explicit capture request shows a small ring/pulse while awaiting the bounded worker. Only authoritative response starts success/failure presentation. Success pulses/shrinks for 400ms; existing server resolution and despawn remove PIP. Failure shakes briefly; any server-provided counterattack follows. No guessed chance is shown before response; afterward the panel labels it **Last server capture chance**, not a prediction for the next attempt. Eligibility/buttons follow authoritative battle/encounter status.

Debug PIP remains unable to start a server battle. Existing request loading guard, terminal errors, Refresh and no automatic POST retries are retained. UI errors remain recoverable; HP is never optimistically decremented.

## Placement, motion and focus

The panel prefers the opposite horizontal side of its entity relative to the safe-area midpoint, then passes through the existing full-bounds clamp and integer panel projection. Panel size, entity window sizes, DesktopSafeArea, Dock policy and native NSPanel class/style remain unchanged. Negative monitor coordinates and edge positions are tested.

`prefers-reduced-motion: reduce` centrally disables shake, translations, pulse/ring, appearance animations and HP transitions. Static damage numbers, numerical HP, result text and the same authoritative states remain. No focus/activate/makeKey/bringToFront calls were introduced. No keyboard hooks or permission changes.

## Actual local validation

Dedicated PostgreSQL `luma_game_test` on 55439 and Java 21 Spring Boot on 18081; existing user/development databases untouched. V1/V2/V3 unchanged. The existing test-only RNG harness provides deterministic success/failure; no production RNG override.

AUTOMATED:
- Server 37 tests PASS: all previous 34 plus resolved/clamped damage ordering, capture counter-only damage, and no damage after victory capture failure.
- Rust 66 tests PASS: all previous 57 plus 9 presentation tests covering queue order/dedup/bounds, immutable authoritative HP, fallback event contract, capture, reward, level and error behavior.
- Presentation UI 4 PASS; Animation 27 PASS; Asset validator tests 12 PASS; Policy 9 PASS. npm build / cargo clippy / Tao integrity PASS; existing vendor warnings unchanged.
- All four explicit live tests executed sequentially, PASS. They exercise HTTP/PostgreSQL/World/controller with both prior game regressions and the new visual sequence.

PLATFORM_REQUIRED (executed):
- Built and launched the real debug .app. MOA cream/green fallback was visually observed. Tool-driven MOA right-click created a real encounter.
- The UI tool exposes only the MOA native window, so it could not directly select the PIP/interaction window. To validate the native pipeline, an opt-in `LUMA_VISUAL_SMOKE=1` debug-only driver submits the same bounded backend commands, opens the existing popup, lets cue timelines complete, loads collection and exits normally. It is absent from release builds and adds no window or timer. Use only with the isolated test server. Its explicit PASS log is required; process exit alone is not proof of success.
- Actual debug smoke logged PlayerAttack -> MonsterHit(12) -> MonsterAttack -> PlayerHit(5), final hit(6), Victory -> Reward -> Capturing -> CaptureSuccess -> PIP removal, PASS.
- Real accumulated rewards (no SQL EXP edits) moved EXP 80->100 / Level 1->2. Native log showed Reward -> LevelUp. Result: Gold 50, EXP 100, Bond 5, Level 2.
- Failure-mode native smoke logged CaptureFail and completed the existing DEFEATED lifecycle, PASS.
- Non-interactive smoke focus audits: activation=0, keyWindows=0, normal panel cleanup. One completed level-up sample lasted 40.46 seconds.

MANUAL_REQUIRED / NOT_VERIFIED:
- Final physical mouse/typing focus, perceived timing, popup visual fit/readability and actual Dock overlap. Native smoke proves commands, phases, emitted snapshots and native lifetime, not human perception of each CSS frame.
- Tool-driven right-click/menu interaction again recorded one application activation and zero key windows (PID 63991). Its tool-vs-native attribution remains unresolved as in PR10. Do NOT describe the entire Never Steal Focus acceptance as PASS or infer resolution from non-interactive smoke.

## Known risks and cleanup

Current explicit commands may supersede pending attack feedback while preserving server state. Very late/stalled main-thread delivery can lengthen presentation timing; the queue remains bounded. Optional future production clip slots are not yet assets. Old backend versions omit damage presentation rather than guessing. Reduced-motion CSS is tested structurally; physical OS-preference observation remains manual.

Local node_modules repeatedly contained duplicate `react 2` / `react-dom 2` directories and caused one bundle build failure. npm ci restored the lockfile installation; no source workaround. An older bundle launched after that failed build was stopped and excluded from final visual evidence; successful latest builds were used for smoke runs.

No new dependencies, schema, formula, transaction/locking, collection, level, encounter, native panel or Tao implementation changes. BattleService changes are response-only presentation assembly from already-resolved values. All isolated validation processes/containers are stopped afterward; user processes, files and LUMA development volume preserved. No automatic merge.
