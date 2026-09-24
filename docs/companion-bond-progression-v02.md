# Companion Bond Progression v0.2

## Implementation design (recorded before implementation)

Base: origin/main dc22de9, including PR #40. User-authorized separation: Battle EXP unchanged, Battle Bond0; explicit companion interaction Bond+1 per300 seconds; Berry+1 unchanged. Evolution thresholds3/5 and6/12 unchanged. Existing Bond/stage/history must never be reset or recomputed.

Current production sources inspected directly: BattleService.reward increments Bond1 with EXP/Gold; ItemService.use/BERRY_BOND increments1 and consumes inventory; Capture/Evolution/Discovery/bootstrap do not add Bond; CompanionController's classified click only triggers local Reacting. No persistent interaction reward/cooldown exists.

Minimal command: bodyless POST /api/v1/companions/active/interact. Reject client amount/timestamp/query fields. Server transaction locks existing player then active companion, reads PostgreSQL clock after lock, awards1 if last successful interaction is null or at least300 seconds old. Cooldown returns HTTP200 COOLDOWN with delta0. Both outcomes return authoritative bootstrap/evolution status and nextAvailableAt. No JVM mutex. No automatic client replay after uncertain POST failure.

Schema inspection: t_player_companion.updated_at is shared by battle, Berry and evolution; using it would incorrectly reset or bypass the relationship cooldown. No existing interaction history timestamp exists. Add V10 nullable last_bond_interaction_at only. Existing rows remain unchanged (null means first valid interaction available). Alternative separate history table is unnecessary for one per-companion cooldown. Existing migrations untouched; no destructive/backfill migration.

Desktop keeps the existing native click-vs-drag classifier and bounded backend worker. Only a completed click requests the command; ambient reactions/drag/hover do not. Bond changes only from acknowledged server bootstrap. Show a short in-panel Bond +1 message on success, silently handle cooldown, no new window/modal/focus activation. Server remains authoritative even for direct API callers; physical-human proof/auth is out of this local-backend scope.

PR #40 analysis is historical v0.1 evidence; preserve its reported data while clearly separating its historical assumptions from the new production analysis. Add current deterministic A/B/C/D/E pacing analysis and regression evidence here.

## Validation plan

Battle EXP/Gold/Personality/Capture unchanged; battle Bond0; interaction first/cooldown/expiry/concurrency/restart; Berry inventory/independence; natural battle-only vs relationship progression; old high Bond/NEBLA preservation; level6 Bond8/11 locked,12 available. Full Java/PostgreSQL, Rust, Desktop/content/assets/presentation, clippy/Tao and latest HEAD CI. Native focus/mouse/typing manual checks separately NOT_RUN until performed. No automatic merge.

## Before / After · Bond Sources

현재 production 코드를 직접 확인한 근거: `BattleService.reward`, `ItemService.use`, `EvolutionRepository.evolve`, `GameRepository`, `DiscoveryService`, `src-tauri/src/companion/mod.rs`. PR #40 문서에서 값을 추정하지 않았다.

| Source | Before | After | cooldown / limit / authority |
| --- | --- | --- | --- |
| Battle victory | EXP=monsterLevel×20, Gold=monsterLevel×10, Bond+1 | EXP/Gold 동일, Bond+0, 새 reward row bond_reward=0 | encounter당 보상1회, 서버 transaction·기존 unique reward. 과거 reward row는 보존 |
| Companion explicit click | client-only Reacting, persistent Bond0 | 유효 command당 Bond+1 | companion별 **300초**, DB clock·player→companion row lock, null이면 첫 회 즉시 |
| 자동 ambient reaction / cursor / drag | persistent Bond0 | 동일0 | 클릭 classifier 통과 의도만 command로 전달. Desktop은 Bond 계산/쓰기 안 함 |
| Bond Berry | +1, 30 Gold/개, inventory1개 소비 | 동일 | interaction cooldown과 독립, ACTIVE battle 사용 금지·stack99·overflow 거부 유지 |
| Capture | 추가 EXP/Bond/Gold0 | 동일 | 승리 후 capture도 추가 Bond 없음. 이전에 받은 보상은 그대로 유지 |
| Evolution | Bond 소모/추가0 | 동일 | stage/history만 변경, MOA→MOKORI Lv3/Bond5; MOKORI→NEBLA Lv6/Bond12 |
| Discovery / bootstrap / spawn / 기타 | 추가 Bond0 | 동일 | 별도 저장/조회/표현 경계 유지. passive/login reward 없음 |

EXP threshold `50×L×(L−1)`, MAX_LEVEL20, 승리 EXP20/40/60·Gold10/20/30, damage/personality/capture 공식, Shop/Berry 효과, 진화 requirements는 변경하지 않았다.

## Interaction Cooldown / command contract

`POST /api/v1/companions/active/interact`는 bodyless 명시적 action이다. body/query의 timestamp/amount/species/ID 등을 받지 않으며, 서버가 local player1의 active companion을 결정한다. 활성 companion이 없으면 기존 오류 계약으로 실패한다. “유효”는 해당 요청 계약과 존재하는 active companion을 의미하며 물리적 인간 클릭 증명은 아니다. 인증/외부 네트워크 서비스는 기존 local-backend 범위 밖이다.

- HTTP200 `AWARDED`: `bondDelta=1`, serverTime, nextAvailableAt=serverTime+300s, authoritative bootstrap/evolution.
- HTTP200 `COOLDOWN`: `bondDelta=0`, 기존 last 성공 시각+300s, authoritative bootstrap/evolution. cooldown을 연장하지 않는다.
- first null → 즉시 +1; 1분 후 →0; last+300초 이상 →+1. 경계는 `now >= last+300`.
- 서버 clock은 player/companion row lock 획득 뒤 PostgreSQL에서 읽는다. 여러 JVM/HTTP 요청도 동일 DB lock으로 직렬화된다. JVM mutex/client timestamp를 사용하지 않는다.
- 성공한 interaction만 timestamp와 Bond를 한 transaction에서 갱신한다. overflow 실패는 timestamp/Bond를 바꾸지 않는다. Gold/EXP/stage/inventory를 변경하지 않는다.
- Berry/battle/evolution의 updated_at 갱신은 interaction timestamp를 건드리지 않는다. Interaction은 ACTIVE battle 중에도 허용되는 관계 command이며, Berry의 기존 battle 제한과 별개다.

V10 `last_bond_interaction_at timestamptz NULL` 하나만 추가했다. 기존 updated_at은 공유 필드여서 사용할 수 없었다. 새로운 테이블·index·backfill·기존 migration 수정은 없다. 기존 Bond5/12/30/75 및 NEBLA stage는 보존된다. DB clock이 뒤로 이동하면 안전하게 더 기다릴 수 있으며, client clock으로 이를 우회하지 않는다.

## Desktop UX / failure handling

기존 CompanionController의 mouse-down/up 및 최대 이동거리 classifier를 사용한다. drag-out-and-back도 click으로 처리하지 않으며, ambient reaction/hover는 command를 만들지 않는다. Rust World가 클릭 의도 하나를 소모해 기존 capacity1 worker에 전송한다. 서버 응답이 확인된 bootstrap/evolution만 반영한다. Bond +1은 기존 entity 패널 안에서3초간 보이는 pointer-events:none 텍스트다. 새 modal/window/native focus 변경 없음, cooldown은 조용히 처리한다.

local busy/queue failure/offline 때 Bond를 미리 지급하지 않는다. 실패 POST를 자동 재전송하거나 cooldown 종료 때 자동 클릭하지 않는다. 응답 유실 시 다음 명시적 interaction의 COOLDOWN 응답에도 실제 bootstrap이 포함되어 동기화된다. 다음 클릭 전까지 화면 Bond가 오래될 수 있다. 빠른 반복 클릭 중 pending 의도는 합쳐지거나 busy로 거절될 수 있으나 서버 cooldown이 최종 지급 기준이다. 이번 API는 일반 mutating-request idempotency key를 도입하지 않았으며, 5분 이후의 새 명시적 요청은 새로운 interaction이다.

Battle reward UI는 Bond0이면 `+0 Bond`를 표시하지 않는다. 과거에 저장된 reward Bond1 등은 기존처럼 표시 가능하다.

## Existing Save Compatibility / Evolution Gate

기존 Bond를 재계산하거나 감소시키지 않는다. 기존 NEBLA가 새로운 획득 규칙 때문에 downgrade되지 않는다. 과거 battle reward 기록 역시 수정하지 않는다. 신규/기존 사용자의 **향후 승리**에만 Bond0이 적용된다.

실제 production HTTP 검증 경로: Fresh MOA →75회 PIP Lv1 victory →Lv6/EXP1500/Bond0/Gold750, 여전히 MOA LOCKED. Interaction5회 →MOKORI AVAILABLE/진화. Interaction8회 →MOKORI Lv6/Bond8 LOCKED. Interaction11회 →Bond11 LOCKED. Berry1개 →Bond12 AVAILABLE →NEBLA, EXP1500 유지·Gold720. 이 integration test에서 빠른 시간 진행은 **cooldown timestamp만** 과거로 옮기는 fixture다. EXP/Bond/stage는 SQL로 만들지 않고 실제 reward/interaction/item/evolution 명령으로 도달한다. 이 검증은55분 실제 대기 측정이 아니다.

Berry 없이도 interaction12회로 gate를 충족한다. Interaction-only는 EXP가0이어서 level gate가 잠기며, Battle-only는 Bond0이어서 relationship gate가 잠긴다. 둘을 함께 진행하면 영구 잠금이 없다.

## Pacing Simulation A/B/C/D/E

`python3 scripts/analysis/bond_progression_v02.py`는 현재 production 상수/보상/requirement/가격을 확인하고 결정적 결과를 출력한다. Test-only, DB 접속/수정 없음. PR #40의 v0.1 문서·수치 fixture는 **HISTORICAL**로 보존하고, 그 도구는 frozen inputs를 재생한다. 이를 현재 production 분석으로 해석하지 않는다.

비교 가정: Fresh 시작, 고정 monster Lv3, 자동 기회 최단120초마다 승리(첫 승리 t=2분), 조작/통신/전투 시간0, interaction은 t=0부터5분마다 직접 수행, 진화는 즉시 요청. Berry는 level 조건이 충족되는 시점에 부족한 Bond만 Gold로 구매/사용한다. 모든 item 사용은 전투 terminal 후다. **이론상 빠른 통제 경로이며 실제 평균/상한이 아니다.** 실제 조작·스폰 조건/배치·실패·시간 미준수는 더 늦춘다.

| Scenario, 100분 시점 | Level / EXP | Bond | Gold | Stage | Berry 사용 | MOKORI 시각 | NEBLA 시각 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Battle only | 8 / 3000 | 0 | 1500 | MOA | 0 | 미도달 | 미도달 |
| B Interaction only | 1 / 0 | 21 | 0 | MOA | 0 | level 부족 | level 부족 |
| C Battle + normal interaction | 8 / 3000 | 21 | 1500 | NEBLA | 0 | 20분 | 55분 |
| D Battle + Berry | 8 / 3000 | 12 | 1140 | NEBLA | 누적12 | 10분 | 50분 |
| E Battle + interaction + Berry | 8 / 3000 | 23 | 1440 | NEBLA | 누적2 | 10분 | 50분 |

E는 t=10분 interaction3회 상태에서 부족한2개(60 Gold)를 사용한다. 그 Bond가 유지되므로 NEBLA에서 추가 Berry가 필요 없다. D는 MOKORI5개150 Gold, 이후7개210 Gold, 누적360 Gold. Bond는 진화 시 소비하지 않는다. C와 비교해 D/E는 MOKORI10분, NEBLA5분 빨라진다. Level 자체 도달 시점보다 진화를 앞당기지는 못한다.

### Interaction-only Bond pacing

첫 무료 interaction을 t=0에 수행하면 Bond5는 **20분**, Bond12는 **55분**. 시작 후 첫 interaction을5분 뒤로 미루면 각각25/60분이다. cooldown/requirements를 임의 재조정하지 않았다.

| 충분한 Gold/보유분으로 즉시 사용한 Berry 수 | Bond5까지 | Bond12까지 | 비용 |
| --- | --- | --- | --- |
| 0 | 20분 | 55분 | 0 |
| 1 | 15분 | 50분 | 30 Gold |
| 2 | 10분 | 45분 | 60 Gold |
| 4 | 즉시 (첫 interaction 포함) | 35분 | 120 Gold |
| 11 | 즉시 | 즉시 (첫 interaction 포함) | 330 Gold |

Fresh interaction-only의 Gold는0이므로 이 단축 표는 전투 등으로 Gold를 확보했거나 기존 Berry를 소유한 조건이다. 실제 진화는 별도로 Lv3/Lv6가 필요하다. 일반식 `max(0,targetBond−berries−1)×5분`; Berry 효과+1과 가격30은 그대로다.

## Regression / evidence

- Battle/Progression tests: 승리 EXP/Gold 증가와 Bond0, legacy Bond 보존. 기존 실제75승 테스트는 Level6/Bond0 잠김을 확인하도록 갱신했고, 별도 관계 progression 테스트로 두 진화 성공을 유지했다.
- CompanionBondIntegrationTest: 최초/1분 cooldown/300초 만료,12개 동시 HTTP 요청 총+1·동일 nextAvailableAt, client fields 거부, overflow rollback, high Bond5/12/30/75·NEBLA 보존, 자연 Lv6/Bond8·11·12 gate.
- Berry: 실제 전투 Gold로 구매, 한 개 보유 상태의 두 동시 사용에서 성공1/거부1, 수량0·Bond1회 증가·interaction timestamp 불변. 일반 HTTP 재시도 key 도입이 아니라 기존 inventory transaction exactly-once 소비 경계를 유지한다.
- CompanionBondRestartTest: 실제 Spring HTTP context를 닫고 새 context로 재시작. interaction75→76, Berry76→77, 재시작 후77/NEBLA/Gold0/소비된 inventory와 cooldown 유지.
- Rust: click vs drag/ambient 의도, HTTP DTO validation, 승인 전 Bond 불변, cooldown silent·피드백 만료, 기존 World/worker 흐름 회귀. 기존 NEBLA live harness는 승리에서 Bond를 가정하지 않고 실제 Berry12개로 진화하도록 갱신했다.
- 기존 Battle Personality/Capture/Inventory/Evolution/Discovery/Monster/Spawn/Collection regression 유지. focus/native geometry/Tao patch 변경 없음.

## Known Risks / MANUAL_REQUIRED

5분마다 interaction을 수행해야 한다는 전제로 Bond12에55분이 걸린다. 사용자 행동 데이터는 측정하지 않았으며, 부담이 크더라도 이번 PR에서 cooldown/requirement를 바꾸지 않는다. 기존 high-Bond 사용자와 신규 사용자의 pacing 차이는 의도적으로 보존한다. 금전 지출 없는 interaction 경로가 있으므로 Berry는 필수가 아니다.

Local unauthenticated backend의 직접 API 호출도 cooldown 조건을 만족하면 interaction으로 인정한다. 부정 사용 방지 인증/인간 증명은 추가하지 않았다. Native 실사용 클릭/드래그, focus·typing 및 시각적 배치의 수동 검증은 **MANUAL_REQUIRED / NOT_RUN**이고, 자동 tests/실제 HTTP worker 검증과 구분한다. 자동 merge 금지; 최종 상태는 READY_FOR_HUMAN_REVIEW다.

### Executed local checks

- Java21/PostgreSQL16: **196 tests PASS,0 failures/errors/skips**, bootJar PASS. Spring context shutdown/start test 포함.
- Rust deterministic/native link: **146 PASS**. 기존 opt-in14개는 NOT_RUN; 새 opt-in worker test는 별도로 실제 배포 JAR에 **fresh / 새 JVM restored 두 실행 PASS**. 일반 CI에서는 새 test까지15개가 opt-in ignored다.
- Rust clippy `--no-deps -- -D warnings` / rustfmt PASS. 기존 upstream Tao warnings만 남는다.
- npm ci/build, animation/Monster Content/Dex/base, presentation, asset tests30, automation18 PASS. Alpha strict0 missing PASS; 일반 validator0 errors/기존27 NOT_SUPPLIED, Tao integrity PASS.
- 실제 서버 프로세스 restart: dedicated luma_bond_v02_live_test DB, loopback18112. Worker fresh 단계 interaction Bond0→1, 승리3회에서 Bond1 유지, Berry→2; JVM 종료 후 새 프로세스의 worker가 Bond2와 COOLDOWN을 확인. 일반 사용자 DB를 사용하지 않았다.
- 금지된 CombatRules/EvolutionRules/ItemRules/ItemService/Monster Content/Tao diff 없음. 최신 GitHub CI는 PR 본문에 HEAD와 함께 기록한다.
