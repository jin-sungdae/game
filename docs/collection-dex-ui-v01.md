# Collection Dex UI v0.1

## Architecture decision before implementation

Base: latest origin/main dfe8345. Reuse the existing nonactivating interaction NSPanel and its compact fixed bounds for a scrollable 30-slot Dex. Add DEX entries in the Companion and Encounter surfaces; do not create another native window. Generic Monster Content and Spawn Director files remain untouched.

Use the existing Collection GET and Monster Dex registry plus its dexEntry projection. A dedicated presentation snapshot distinguishes unloaded, loading, empty success and failed refresh; server Collection records alone authorize capture/count/timestamp. Existing server Encounter responses provide session-only discovery evidence; no persistent discovery API exists. Captured always implies discovered. No speculative desktop capture decisions, DB migration or registry enablement.

Alternative: a new Dex NSPanel would add native lifecycle/focus risk without improving this small scope. Persistent discovery needs a future server contract and is deferred. Architecture and actual desktop focus/visual acceptance require human review; no automatic merge.

## UI and data flow

The same 240×300 interaction surface opens via DEX on Companion Evolution or Encounter. Header, full-catalog counters, six rarity buttons and Refresh stay above an internally scrollable list. Thirty numbered slots include all 15 Alpha candidates and all provisional content, independent of enabled/spawn eligibility. Filters never change the /30 denominator. No search, sort, native select popup, new window, activation call or panel resize.

`collection_dex.rs` holds a read-only snapshot: records=None means not loaded, Some(empty) means server-confirmed empty. The existing serialized backend LoadCollection command calls GET /api/v1/collection. DEX opens/refreshes explicitly; no added polling loop. Queue/network errors release busy state. Failed refresh retains the last complete snapshot with a visible stale warning; initial failure shows unknown counters (—), never a confirmed zero.

Server Encounter events add deduplicated session discovery evidence. Debug spawn does not. Captures are projected only from server Collection records; successful capture responses update an already loaded snapshot by code without dropping other records or locally incrementing counts. Single capture responses cannot initialize an incomplete Collection list. Capture implies discovery. Because main has no persistent discovery endpoint, uncaptured discovery resets on restart, explicitly stated in the UI. Existing backend supports PIP only; future confirmed server/catalog integration may expose more content without this PR activating anything.

The UI uses Monster Dex `dexEntry` for masking and state precedence, iterating all definitions rather than its enabled-only helper. Its public slot projection omits monsterCode, workingName and assetIdentity. Undiscovered slots pass null to the asset loader and expose only number, ??? and a generic CSS silhouette. Rarity is available to the filter; undiscovered cards do not reveal names or actual image paths. Captured PIP uses the unchanged production base PNG. Missing/decode-invalid images use the same static diagnostic shape; no PNG generation. Capture count and firstCapturedAt come from the server, with an unambiguous timestamp shown in a time element. Content bundles remain public local data; masking is a UI presentation guarantee, not encryption of bundled metadata.

## Focus policy

Reuse the existing nonactivating NSPanel, canBecomeKeyWindow=NO / canBecomeMainWindow=NO, hidden nonfocusable Tauri host, WKWebView, single-instance handling and Tao startup patch. No changes to native files, overlay bridge, geometry or focus policy. Rarity uses ordinary click buttons and list scrolling; no keyboard search, autofocus or focus restoration. Closing follows the existing action('close') path. Browser DOM focus testing is not proof of native Never Steal Focus.

## Validation

AUTOMATED local PASS: TypeScript/Vite build; 49 presentation/UI tests (9 new Dex groups); 47 animation/base/Dex tests; 16 asset tests; 9 automation tests; Tao integrity; whitespace; Rust 96 passed / 7 ignored; Clippy --no-deps -D warnings. The ignored live fixtures are NOT_RUN locally. Existing optional asset validation reports 0 errors / 26 NOT_SUPPLIED, not production completion. One test-only repair corrected case sensitivity of React SSR dateTime output; no implementation repair was needed.

BROWSER FIXTURE PASS: actual 240×300 component render with PIP capture 7 and first timestamp; discovered-only PIP; initial error/unknown counters; EPIC and SPECIAL filter clicks; scrolling to No.030 with controls retained. This uses synthetic presentation props and the real PIP asset, not a live server/native panel claim. Temporary preview files are excluded from the PR.

CI must verify the final SHA with desktop-static, macos-native, server-java (including Inventory/Collection integration) and review-result. See the PR's final check links and schema-compliant review artifact. PLATFORM_REQUIRED / MANUAL_REQUIRED NOT_RUN: actual desktop typing while opening/filtering/scrolling/closing Dex, NSPanel focus audit, multi-monitor positioning, single-instance launch and visual acceptance on the target display.

## Changed files and parallel work

New UI/model/style/test: src/components/CollectionDex.tsx, src/presentation/collectionDex.ts, src/presentation/collectionDex.css, tests/presentation/collection-dex.cjs. New Rust snapshot/tests: src-tauri/src/collection_dex.rs. Small wiring changes: src-tauri/src/main.rs, src-tauri/src/behaviors.rs, src/types/entity.ts, src/main.tsx, src/components/Interaction.tsx, src/components/EvolutionInteraction.tsx and scripts/test-presentation.sh, plus this document.

No changes to server, migrations, Inventory implementation, Monster Dex/Content registry files, Spawn Director module, production assets, native window files or dependencies. Based only on origin/main dfe8345 (already containing merged PR #20); no feature-branch dependency or cherry-pick. PR #22 and #23 were docs-only at initial overlap inspection; later parallel commits may introduce overlap in shared main.rs/behaviors.rs/types wiring. Check final PR file lists before merge.

Known risks: discovery history is session-only; data can change outside this client until explicit refresh; a missing image remains cached as diagnostic for the session; compact text inherits the small existing surface. Architecture, native focus validation and merge are human review decisions.
