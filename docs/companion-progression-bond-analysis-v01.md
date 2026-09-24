# Companion Progression & Bond Balance Analysis v0.1

분석 기준: `origin/main` **b1f1dd1** (PR #39 포함). Production gameplay changed: **NO**. Migration: **NONE**. Runtime 변경 없음. 아래 모델은 승인 제안이 아닌 비교용 가정이다.

## Current Rules / authority

경로는 repository root 기준이다. 배포 DB를 조회한 결과가 아니라 **현재 코드와 Flyway로 새로 생성한 DB의 계약**이다. 운영자가 DB master를 바꾼 환경에는 재계측이 필요하다.

| 계약 | 실제 값 / authority | source of truth |
| --- | --- | --- |
| Fresh MOA | Stage1, Lv1, EXP0, Bond0, Gold0 | `server/src/main/resources/db/migration/V2__local_master_seed.sql` |
| 승리 보상 | EXP=monsterLevel×20, Gold=monsterLevel×10 | `server/src/main/java/dev/luma/game/CombatRules.java`: `exp`, `gold` |
| 승리 Bond | +1/승리, encounter별 1회. 트랜잭션/row lock 및 reward uniqueness | `BattleService.java`: `attack`, `reward`; `V3__battle_capture_reward.sql` |
| 포획 | 승리 전 성공/실패 모두 추가 EXP/Bond/Gold=0. 승리 후 포획도 추가 0, 이미 받은 승리 보상 유지 | `BattleService.java`: `capture` |
| Level | threshold(L)=50×L×(L−1); MAX_LEVEL=20; 누적 EXP 보존 | `CombatRules.java`: `levelThreshold`, `level` |
| MOKORI | MOA Stage1 → Stage2, Lv≥3 AND Bond≥5 | `EvolutionRules.java`, `EvolutionService.java` |
| NEBLA | MOA Stage2 → Stage3, Lv≥6 AND Bond≥12 | 동일. Stage3에서 다음 활성 전이 없음 |
| 진화 수행 | 명시적 evolve 요청, 서버 재검증. EXP/Bond/Gold 소모 또는 보너스 없음 | `EvolutionRepository.java`: `evolve`; 이름은 `m_species_evolution` |
| Berry | +1 Bond/1개, 30 Gold | 효과 `ItemRules.BERRY_BOND`, 적용 `ItemService.use`; 가격은 runtime `game.m_item`, 초기값 V5 |
| Potion / Charm | Potion 30 HP 회복 / Charm 다음 포획 +0.10, chance 최대0.95 | `ItemRules`, `ItemService`; 초기 가격20 / 40 Gold |
| 몬스터 선택 | DB use_yn/weight + Content readiness 필터, species weight 선택 후 해당 min..max 균등 level 선택 | `GameRepository.monsters`, `MonsterContent.eligible`, `MonsterSelector.select` |

Java 경로의 축약 파일들은 모두 `server/src/main/java/dev/luma/game/` 아래에 있다. 가격 초기값의 정확한 파일은 `server/src/main/resources/db/migration/V5__inventory_items.sql`이다.

### Reward distribution

V2/V6/V7/V8의 **15종 모두 level 1..3**. Content `src/entities/monster-dex.json`과 master의 코드/rarity/weight가 일치한다. COMMON 7×100=700, UNCOMMON 4×50=200, RARE 3×20=60, SPECIAL 1×1=1, 전체 weight961. 모든 species에서 EXP20/40/60, Gold10/20/30이 각각 1/3이다. Rarity 자체에는 EXP/Gold 배율이 없다. Desktop 시간/배치 조건이 species를 제한해도 현재 각 species의 level 범위는 같다.

따라서 **모든 선택된 level을 승리한다는 조건** 아래 E[EXP/승]=40, E[Gold/승]=20. 이것은 사용자 행동 관측 평균이 아니다. 특정 level만 무시/포획하거나 전투를 중단하면 승리 표본의 분포가 달라진다. 현재 공격만 이어가는 전투는 Lv1 companion도 최대 monster Lv3을 5회 공격 이내에 이긴다(HP100, attack12; monster HP50, counter9×최대4=36). WAIT는 피해를 줄일 뿐이다. 반복 포획 실패 등 다른 행동은 이 전제를 만족하지 않는다.

## Method / reproducibility

`python3 scripts/analysis/progression_bond.py` → deterministic JSON.
`python3 scripts/analysis/progression_bond.py --markdown` → 아래 생성 표.
`python3 -m unittest discover -s tests/automation -v` → 계약 읽기, 동일 입력 재실행, JSON fixture/문서 동기화, 작은 상태공간 완전열거 검증.
`./server/gradlew -p server test --tests '*ProgressionBondAnalysisTest'` → 실제 Java domain과 Python 결과 교차 검증.

도구는 파일만 읽으며 DB 접속/수정, runtime import, binary packaging이 없다. Production 공식/seed shape를 명시적으로 확인하고 불일치하면 실패한다. 이는 일반 Java/SQL interpreter가 아닌 **이 main snapshot의 분석 어댑터**이므로 새 보상 경로/SQL UPDATE/권한 정책 추가 시 사람이 계약을 다시 검토해야 한다.

기대 도달 횟수는 40으로 나눠 반올림하지 않는다. EXP를20단위로 바꾸고 각 승리의 +1/+2/+3에 대해 Fraction 기반 first-passage DP를 계산한다. `E[T]=Σ n·P(T=n)`. Increment expectation은 `E[T_L]−E[T_(L−1)]`로 이전 승리의 초과 EXP를 보존한다. 정확히 이전 threshold에서 시작하는 별도 결과도 제공한다. 소수4자리 표기는 반올림이며 계산은 유리수다.

Timeline은 **고정 monster Lv2** 예시이며 확률 기대값이 아니다. 요구 조건 충족 즉시 사용자가 진화 요청을 한다고 가정한다. 실제 자동 진화는 없다. 이미 진화했다면 표의 YES는 조건/달성 여부이며 API의 현재 `AVAILABLE`을 뜻하지 않는다.

<!-- BEGIN GENERATED ANALYSIS -->

### Level Threshold Table

| Level | Cumulative EXP | Increment |
| --- | --- | --- |
| 1 | 0 | 0 |
| 2 | 100 | 100 |
| 3 | 300 | 200 |
| 4 | 600 | 300 |
| 5 | 1000 | 400 |
| 6 | 1500 | 500 |
| 7 | 2100 | 600 |
| 8 | 2800 | 700 |
| 9 | 3600 | 800 |
| 10 | 4500 | 900 |
| 11 | 5500 | 1000 |
| 12 | 6600 | 1100 |
| 13 | 7800 | 1200 |
| 14 | 9100 | 1300 |
| 15 | 10500 | 1400 |
| 16 | 12000 | 1500 |
| 17 | 13600 | 1600 |
| 18 | 15300 | 1700 |
| 19 | 17100 | 1800 |
| 20 | 19000 | 1900 |

### Timeline: fixed monster Lv2, no items, evolve immediately when eligible

Eligibility columns mean requirements met (including completed transitions), not an API action still available after evolution.

| Wins | Stage | Level | EXP | Bond | Gold | MOKORI met | NEBLA met |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | MOA | 1 | 0 | 0 | 0 | NO | NO |
| 1 | MOA | 1 | 40 | 1 | 20 | NO | NO |
| 5 | MOA | 2 | 200 | 5 | 100 | NO | NO |
| 10 | MOKORI | 3 | 400 | 10 | 200 | YES | NO |
| 15 | MOKORI | 4 | 600 | 15 | 300 | YES | NO |
| 20 | MOKORI | 4 | 800 | 20 | 400 | YES | NO |
| 25 | MOKORI | 5 | 1000 | 25 | 500 | YES | NO |
| 30 | MOKORI | 5 | 1200 | 30 | 600 | YES | NO |
| 40 | NEBLA | 6 | 1600 | 40 | 800 | YES | YES |
| 50 | NEBLA | 6 | 2000 | 50 | 1000 | YES | YES |
| 60 | NEBLA | 7 | 2400 | 60 | 1200 | YES | YES |
| 75 | NEBLA | 8 | 3000 | 75 | 1500 | YES | YES |
| 100 | NEBLA | 9 | 4000 | 100 | 2000 | YES | YES |

### Battle Count: uniform Lv1/2/3 victories

| Target | Fresh best | Fresh expected | Fresh worst | Expected increment (carry) | From exact prior threshold: best / expected / worst |
| --- | --- | --- | --- | --- | --- |
| 2 | 2 | 2.8272 | 5 | 2.8272 | 2 / 2.8272 / 5 |
| 3 | 5 | 7.8333 | 15 | 5.0062 | 4 / 5.3348 / 10 |
| 4 | 10 | 15.3333 | 30 | 7.5000 | 5 / 7.8333 / 15 |
| 5 | 17 | 25.3333 | 50 | 10.0000 | 7 / 10.3333 / 20 |
| 6 | 25 | 37.8333 | 75 | 12.5000 | 9 / 12.8333 / 25 |

### Gold Economy: no spending, first threshold crossing

| Milestone | Gold range | Potion quantity | Berry quantity | Charm quantity |
| --- | --- | --- | --- | --- |
| MOKORI | 150–170 | 7–8 | 5–5 | 3–4 |
| Lv5 | 500–520 | 25–26 | 16–17 | 12–13 |
| Lv6 / NEBLA | 750–770 | 37–38 | 25–25 | 18–19 |

### Scenario Comparison: 100 opportunities

| Scenario | Wins | Stage | Level | EXP | Bond | Gold | MOKORI opportunity | NEBLA opportunity (continued) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 100 | NEBLA | 9 | 3980 | 100 | 1990 | 8 | 38 |
| B | 0 | MOA | 1 | 0 | 0 | 0 | — | — |
| C | 50 | NEBLA | 6 | 1980 | 50 | 990 | 15 | 75 |
| D | 25 | MOKORI | 4 | 980 | 25 | 490 | 29 | 149 |

### Sensitivity Analysis: no Berry, independent hypothetical Bond rolls

| Model | E[Bond at Lv6] | E[wins MOKORI] | E[wins NEBLA] | P[Bond locked at Lv6] |
| --- | --- | --- | --- | --- |
| current | 37.8333 | 7.8333 | 37.8333 | 0.0000 |
| battle_bond_zero | 0.0000 | — | — | 1.0000 |
| p_0.25 | 9.4583 | 20.0250 | 49.1066 | 0.7772 |
| nebla_bond_40 | 37.8333 | 7.8333 | 40.2802 | 0.7532 |

<!-- END GENERATED ANALYSIS -->

## Battle Count / carry interpretation

MOA→MOKORI는 **5 / 7.8333 / 15승**(best / 기대 / worst), MOA→NEBLA는 **25 / 37.8333 / 75승**이다. 이미 Lv5라도 현재 EXP를 알아야 남은 승수를 계산할 수 있다.

- 정확히 Lv5 EXP1000: +500 필요 → **9 / 12.8333 / 25승**.
- Fresh에서 계속 monster Lv3만 승리: Lv5 진입 EXP1020, 남은480 → **8승**.
- 자연 Lv5 진입의 overshoot를 포함하는 평균 Lv5→6: **12.5승**. 진입 EXP는1000/1020/1040이라 가능한 최소8승/최대25승.
- 고정 monster Lv1/2/3의 연속 경로에서 구간 승수: 각각 `5,10,15,20,25` / `3,5,7,10,13` / `2,3,5,7,8`. 각 열은 Lv1→2,…,Lv5→6이다. 구간마다 best를 따로 취한 합은 하나의 실행 경로가 아닐 수 있다.

## Bond Growth / NEBLA Gate Analysis

| 경로 | Bond 증가 | 빈도 / 제한 | authority |
| --- | --- | --- | --- |
| Battle victory | +1 | encounter별 한 번. 재요청으로 재보상 불가. 별도 일일 cap 없음 | 서버 `BattleService.reward`, unique reward/잠금 |
| 패배 / 도주 / 만료 | 0 | EXP/Gold 보상도 없음 | BattleService / GameRepository.expire |
| Capture | 0 | 승리 전 포획은 승리 기회를 끝낸다. 승리 후 포획은 이미 얻은 +1을 보존 | BattleService.capture |
| Interaction / pet / drag | 0 persistent Bond | Desktop 표현/행동이며 Bond 증가 API 없음 | Rust companion behavior / 서버 write 경로 전체 검색 |
| Item: Berry | +1 | 1개 소비, ACTIVE battle 중 불가, 수량/Gold 필요. stack99, 별도 시간 cap 없음; integer overflow 거부 | ItemService.use, ItemRules, m_item |
| Evolution | 0 | 다음 stage와 history만 기록, Bond 소모 없음 | EvolutionRepository.evolve |
| Discovery / bootstrap / spawn / level up | 0 추가 | discovery는 별도 기록, bootstrap은 조회; level up은 승리 보상에 따른 재계산 | DiscoveryService / GameRepository / BattleService |
| 기타 | 현재 구현 없음 | quest/passive/login/시간 보상 없음. 테스트 SQL fixture는 플레이 경로 아님 | 서버 EXP/Bond write 검색 |

Fresh, no Berry 조건의 자연 Lv6 Bond는 **min25 / E37.8333 / max75**. 이 범위는 **Lv6 첫 도달 시점**이다. 이후 계속 싸우면 Lv6 구간에서도 증가한다. Berry를 허용하면 Bond를 더 높일 수 있으므로75는 전체 gameplay의 상한이 아니다. 첫 Lv6까지 획득한 Gold로만 Berry를 구매해 모두 쓴 경우 전역 최대는 **75+25=100**, 남은 Gold0이다(75승 경로 EXP1500/Gold750). 임의 지급 Gold/기존 inventory가 있으면 이 경계는 적용하지 않는다.

증명: 현재 EXP 증가 원천은 승리뿐이고 한 승리 EXP≤60, Bond≥1이다. EXP≥1500이면 승리≥ceil(1500/60)=25, 따라서 Bond≥25>12. 포획/무시/상호작용은 이 부등식을 깨지 않는다. 정상 Fresh 경로에서 **Lv6 AND Bond<12는 불가능**하다. Stage2 미진화 상태라면 먼저 MOKORI 요청을 해야 하지만 Bond 때문에 막히지는 않는다. MOKORI도 최소ceil(300/60)=5승이라 Bond5는 자동 충족한다.

따라서 현재 자연 progression에서 Bond12를 제거해도 NEBLA의 첫 eligibility 시점은 동일하다. 그러나 임의 초기 상태/legacy import/관리자 수정/future EXP 보상은 예외다. 기존 `ProgressionIntegrationTest.battleCrossesSixBerryUnlocksAndSevenRemainsReachable`의 Lv5 EXP1480 Bond10은 명시적인 SQL fixture이며 정상 도달 증거가 아니다. 이런 상태에서 Bond gate는 실제로 작동하므로 이번 분석을 근거로 삭제하지 않는다.

## Berry Analysis

Fresh 경로에서는 Lv3/Lv6 모두 level gate가 선행해 **진화 가속에 필요한 Berry=0**이다. 예를 들어 고정 Lv2 몬스터8승 후 EXP320/Lv3/Bond8/Gold160에서 Berry1개를 쓰면 Bond9/Gold130, MOKORI 시점은 바뀌지 않는다. 38승 후 EXP1520/Lv6/Bond38/Gold760에서 쓰면 Bond39/Gold730, NEBLA 시점도 동일하다. Berry는 EXP를 늘리지 않으므로 level 대기 시간을 줄이지 못한다. Stage3 이후도 현재 활성 다음 진화가 없고, Bond로 전투 능력이 증가하는 공식도 없다. 수치/역할 표현 외 현 production 진화 효용은 제한적이다.

반면 legacy/test 상태 MOKORI Lv6/Bond11/Gold30에서는 Berry1개로12, Gold0, 즉시 NEBLA eligible이다. 현재 Fresh 정상 경로가 아니라는 표시가 필수다. 다음 모델의 가정에서는 Berry의 실제 gate 해소 효용이 생길 수 있다.

## Gold Economy interpretation

획득 Gold=EXP/2. threshold는20배수이고 마지막 보상≤60이므로 첫 도달 EXP는 threshold+{0,20,40}; 이에 따라 표의 Gold 범위가 나온다. MOKORI **150–170**, Lv5 **500–520**, Lv6/NEBLA **750–770**. 진화에 가격은 없으며 NEBLA 진화를 늦추면 Gold가 더 늘 수 있다. 표는 즉시 진화 기준이다.

구매 수량은 **각 아이템 하나에 전액을 쓸 때**의 독립적 floor(Gold/price), 동시에 모두 구매 가능하다는 의미가 아니다. Berry 구매 후 사용 시 Gold−30/Bond+1, EXP 불변이다. Potion/Charm 지출 및 이미 소유한 수량을 반영하면 실제 잔액/추가구매 가능량은 더 작다. 현재 수량99 stack 제한에도 이 milestone의 개별 수량은 걸리지 않는다. 포획-only Fresh는 수입0이므로 첫 Berry/Charm도 자체 조달할 수 없다.

## Time Estimate: opportunity-only lower bounds

Authority: `src-tauri/src/spawn/mod.rs` `Config::default`, `Director::resolved/removed/cooldown/tick`; `server/.../GameRepository.create/expire`; `BattleService.attack/capture`.

Desktop Director의 **120–300초 cooldown이 spawn interval**이다. 별도120초를 더하는 구조가 아니다. Fresh empty reconciliation 후 cooldown 한 번, 각 server-confirmed terminal removal 후 다음 cooldown 한 번이다. 따라서 fresh automatic path N번 기회의 최소 대기 합은 **120N초**. 이미 첫 encounter가 제공된 시점부터 재면120(N−1)초다. 다음 표는 fresh 시작이다.

| 대상 | Best 승수 기준 최소 | 기대 승수에 최소 cooldown만 적용 | Worst 승수에 최소 cooldown만 적용 |
| --- | --- | --- | --- |
| MOKORI | 5×2=10분 | 7.8333×2=15.6667분 | 15×2=30분 |
| NEBLA | 25×2=50분 | 37.8333×2=75.6667분 | 75×2=150분 |
| 정확히 EXP1000에서 Lv6까지 (다음 기회부터) | 9×2=18분 | 12.8333×2=25.6667분 | 25×2=50분 |

이는 실제 완료시간 추정이 아니다. 첫 열은 가능한 reward/cooldown의 이론 하한이며, 다른 열은 지정 승수의 cooldown-only 기준값이다. 최소 cooldown 대신 최대300초를 대입하면 MOKORI 25–75분, NEBLA125–375분의 대기 합이지만 **실제 wall-clock 상한은 아니다**. 전투 조작, 요청 지연, 진화 확인, 조건 불일치/배치 실패, 시스템 비활성, 대기 중 사용자의 무시를 더해야 한다.

서버 encounter lease60초, 승리 시 포획 가능 lease60초 연장. ACTIVE battle은 expiry에서 제외된다. 승리 후 즉시 포획/ignore로 terminal 처리하면 lease60초 전체를 기다릴 필요는 없다. 무응답 만료를 택하면 추가 시간이 든다. 실패 backoff5/10/30초는 정상 보상 주기가 아니다. HTTP `GameService.createEncounter` 자체는 terminal 후120초 rate limit을 강제하지 않으므로 직접 API 테스트의 빠른75승을 Desktop 시간으로 해석하면 안 된다. 본 PR은 실제 유저 소요시간 측정을 하지 않았다.

## Scenario Comparison assumptions

표의100은 승리 수가 아니라 **encounter 기회 수**다. 성공적으로 진행한 승리의 monster level을 **1,2,3 반복**으로 고정하여 재현한다. 이는 가능한 통제 sequence이고 확률적 대표 sample이라고 주장하지 않는다. 아이템 사용/전투 중단 없음, 진화는 조건 충족 즉시 요청한다.

- **A Battle-heavy**: 모든 기회 W(승리), 이후 즉시 terminal 처리. 100기회=100승, MOKORI8번째/NEBLA38번째 기회. 최단 cooldown 합16분/76분.
- **B Capture-heavy**: 공격하지 않고 승리 전 Capture만 시도. 성공 또는 실패/패배/만료 중 무엇이든 승리가 없으므로100기회 후 EXP/Bond/Gold0, Lv1 MOA. 포획 성공률을100%로 가정한 것이 아니며 collection 수는 시뮬레이션하지 않는다. 진화 도달 불가. 반대로 **모두 승리한 뒤 포획**한다면 A와 progression이 완전히 같다.
- **C Mixed**: W,C 반복. 100기회=50승, MOKORI15번째/NEBLA75번째 기회, 최단30분/150분.
- **D Casual**: W,I,I,I 반복, I는 즉시 Ignore. 100기회=25승, Lv4 EXP980/Bond25/Gold490. MOKORI29번째, 계속하면 NEBLA149번째 기회, 최단58분/298분. 무응답 expiry를 의미하는 I라면 lease 대기가 추가된다.

## Sensitivity Analysis / Candidate Models

Production에는 적용하지 않았다. 비교의 level 분포는 독립 균등1..3이며 Berry가 없는 경우다. `p_0.25`는 **가상으로 승리마다 독립25% 확률 +1 Bond**; production RNG 정책이 아니다. `nebla_bond_40`은 현재 +1과 MOKORI5 유지, NEBLA만40으로 가정한다. 기대값을 단순히 threshold/평균으로 나누지 않고 다음 exact 식을 쓴다:

`E[max(T_exp,T_bond)] = requiredBond/p + Σ(n=0..maxExpWins−1) P(T_exp>n)·P(Binomial(n,p)≥requiredBond)`.

이는 EXP draw와 가상 Bond draw가 독립이고 필요한 Bond에 달하면 유지되는 경우다. `P[locked at Lv6]`는 first-passage 분포와 binomial CDF를 합성한다. Stage2 requirement가 더 작고 Lv3 threshold도 작으므로 즉시 진화 정책에서는 NEBLA 도달 이전에 Stage2가 가능하다.

| Candidate | 장점 / pacing | 단점 / 행동 유도 | Berry 효용 | 구현 복잡도 |
| --- | --- | --- | --- | --- |
| A: Battle Bond0, interaction/Berry Bond | Battle은 EXP 중심, 관계 행동과 분리. Berry 없고 현재 interaction 그대로면 MOKORI/NEBLA 영구 미도달 | 현재 persistent interaction Bond 경로가 없으므로 새 authority/anti-spam/빈도 규칙 설계 필요. 유료 아이템 강제처럼 느껴질 위험 | 현 가격 가정에서 MOKORI5개=150 Gold, NEBLA까지 누적12개=360. 자연 level threshold까지 번 Gold로 충당 가능해 추가 승리 없이 각각5–15/25–75승 도달 가능, 다른 구매 여력 감소 | 높음: 서버 interaction command, 저장/중복/상한/동시성. 이번 PR 승인 범위 밖 |
| B: Battle Bond p=25% | 평균 NEBLA49.1066승, level 도달 평균37.8333에서 관계 대기 추가 | Lv6에서77.72%가 Bond 미달; tail에 유한 최악 승수 없음. RNG 불운/반복 플레이 유도 | Lv6 기대 Bond9.4583. 평균값의12−9.4583을 개인 필요 Berry라고 해석하면 안 됨. 개별 부족분 max(0,12−actualBond)을30 Gold씩 해소 | 중간: reward RNG/idempotence/재시도 보존과 UI 설명 필요 |
| C: Battle +1 유지, NEBLA Bond40 | 평균40.2802승, 기존 계약과 유사 | Lv6에서75.32% 미달; 고레벨 적을 이길수록 EXP 대비 Bond가 낮아 빠른 성장에 역유인 가능. 같은 낮은 level 반복 유도 | 고정 Lv3 25승/Bond25 →15 Berry=450 Gold; 고정 Lv2 38승 →2개60 Gold; Lv1 75승은0개. Berry 없이 총40/40/75승 | 낮음~중간: requirement/설명/회귀/기존 save 정책. 값 선택은 별도 승인이 필요 |

Model A의 무아이템 경로와 Berry를 허용한 경로는 다른 시나리오다. Berry는1 Bond이므로 stage2에서 쓴5는 소모되는 Bond가 아니라 유지되고 NEBLA까지 추가7개면 된다. 현재 모델에서는 동일한 지출로 진화 시간을 줄이지 못한다. 어떤 후보도 여기서 추천 확정하거나 production에 반영하지 않는다.

## Migration / Compatibility Risks

- 이미 높은 Bond: **보존**, 새 cap으로 잘라내거나 reset 금지. 새로운 획득률은 장래 reward부터 적용할지 명시해야 한다. 과거 reward 재계산/회수 금지 원칙.
- 이미 NEBLA: 새 requirement 미충족이어도 stage/history 보존, downgrade/진화 취소 금지. 새 gate는 아직 수행하지 않은 전이에만 적용하는 후보 정책을 검토해야 한다.
- MOKORI Lv5: exp/bond/gold 유지. Bond rule0/확률화/threshold40은 기존에 예상했던 다음 진화를 늦출 수 있다. grandfathering/유예/보상은 별도 설계 결정이지 이 PR의 migration이 아니다.
- Legacy capped Lv5 with EXP≥1500: 기존 구현은 다음 승리에서 level을 재계산한다. arbitrary low Bond save는 Fresh invariant 밖이므로 Berry/guard 회귀를 계속 유지한다. bootstrap에서 자동 수정하지 않는다.
- Content/DB/보상 경로가 바뀌면 snapshot 분석 재실행 및 authority 검토 필요. 특히 새 capture EXP, passive EXP, species level>3, Gold 지급은 현재 gate/경제 증명을 바꾼다.
- 제안의 핵심 game design 승인, 운영 DB 확인, 실제 유저 retention/pacing 계측은 **HUMAN_REVIEW_REQUIRED / NOT_RUN**. Schema migration은 **NONE**.

## Validation boundary

추가 파일은 분석 스크립트, JSON fixture, Python/Java 테스트, 이 문서뿐이다. Battle/Personality/Capture/Inventory/Evolution/Progression/Discovery/Monster/Companion production source와 migration은 변경하지 않는다. 기존 전체 automated regression 및 최신 PR CI 결과는 PR에 기록한다. Native focus/mouse/typing의 실제 데스크톱 수동 회귀는 이번 분석 작업에서 **MANUAL_REQUIRED / NOT_RUN**이며 simulation으로 대체했다는 주장을 하지 않는다.

### Local automated evidence

- Java21 + isolated PostgreSQL16: **187 tests, 0 failures/errors/skips**, `test bootJar` PASS. Battle/Personality/Capture/Inventory/Evolution/Progression/Discovery/Monster를 포함한다.
- Rust: **142 PASS, 14 ignored** (opt-in live/platform tests NOT_RUN), clippy `--no-deps -- -D warnings`, app rustfmt PASS. Upstream Tao warnings는 기존 상태다.
- `npm ci`, build, animation/content/Dex/base 및 presentation regressions PASS; asset validator tests **30 PASS**; automation/analysis **16 PASS**.
- 일반 asset validation **0 errors, 27 NOT_SUPPLIED** (기존 미제공 animation/RUU/NOX); Alpha strict **0 errors, 0 missing**. Tao integrity PASS (기존 문서화된3파일 patch만 존재).
- Generated JSON/report 일치 및 실제 Java threshold/evolution/보상 교차 검증 PASS. Native 실사용/플레이 시간 계측은 NOT_RUN.
