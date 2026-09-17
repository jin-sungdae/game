# Milestone 1 · Companion Engine v0.1

Technical Spike 01.1은 사용자 수동 검증까지 GO로 확정된 기반이다. 이번 변경은 그 위에 Companion 행동을 확장한다. Tauri 2.11.5, Tao 0.35.3 opt-in patch, LSUIElement/Accessory, native nonactivating NSPanel, WKWebView와 기존 33ms scheduler는 유지한다. 새로운 dependency, backend, 게임 성장/전투 시스템 또는 GitHub/Codex 자동화를 추가하지 않는다.

## 변경 파일과 책임

| 파일 | 변경 |
|---|---|
| `src-tauri/src/entities.rs` | `MoaState`를 7개 상태의 `CompanionState`로 확장 |
| `src-tauri/src/companion/mod.rs` | entity/state duration/target/seeded RNG/interaction을 소유하는 controller |
| `src-tauri/src/companion/transitions.rs` | event와 현재 상태를 입력받는 순수 전이 규칙 |
| `src-tauri/src/companion/config.rs` | personality 및 행동 tuning의 Local Master Configuration |
| `src-tauri/src/companion/selection.rs` | personality weight 계산과 누적 weighted selection |
| `src-tauri/src/companion/tests.rs` | 가상 시간과 seed를 사용하는 결정적 테스트 |
| `src-tauri/src/behaviors.rs` | MOA 처리를 controller에 위임, 기존 PIP lifecycle와 snapshot 유지 |
| `src-tauri/src/main.rs` | module 선언과 drag에 현재 simulation time 전달만 추가 |
| `src/types/entity.ts` | 직렬화 상태 union 동기화 |
| `src/style.css` | SITTING/LOOKING/SLEEPING 임시 CSS 표현 |
| `src/behaviors/README.md`, `README.md`, 이 문서 | 계층 및 검증 안내 |

React component는 변경하지 않았다. 기존 snapshot의 state/position/facing을 표현하고 mouse action만 IPC로 전달한다. authoritative Companion entity는 controller 내부에 있으며 World snapshot은 rendering용 복사본이다. `Option<DragGesture>`는 mouse offset과 이동량을 보관하며, 행동 상태는 boolean 조합이 아닌 `CompanionState`와 전이 규칙이 결정한다.

## 상태와 우선순위

| 상태 | 진입 / 종료 | 기본 행동 |
|---|---|---|
| IDLE | 초기, 행동 완료, drag release | 30–60초 후 다음 행동 선택 |
| WALKING | IDLE weighted decision | 현재 x ±180pt에서 clamped target 선택, 40pt/s, 최대 5초 |
| SITTING | IDLE weighted decision | 8–16초 정지 후 IDLE |
| LOOKING | IDLE decision 또는 IDLE/SITTING cursor 접근 | 3–6초 cursor의 좌/우 방향 추적 후 IDLE |
| SLEEPING | 충분한 quiet time 이후 IDLE decision | 20–40초 정지 후 IDLE, cursor 접근으로 깨지 않음 |
| DRAGGING | 기존 mouse press | 자동 전이·cursor·PIP reaction 중지, 실제 drag release 후 IDLE |
| REACTING | click 또는 PIP proximity, DRAGGING 제외 | 1.2초 후 IDLE, PIP 반응은 PIP 방향을 봄 |

전이는 `transitions::next`로만 결정한다. 한 tick에서 자동 전이는 최대 한 번이다. 실제 drag를 놓은 tick은 PIP도 반응을 보류하므로 IDLE snapshot이 유지되고 이후 tick부터 근접 반응이 가능하다. 기존 클릭은 이동량 5pt 미만인 press/release를 별도 click reaction으로 해석하므로 IDLE을 거쳐 REACTING이 된다. 드래그했다가 시작점으로 돌아와도 최대 이동량으로 구분하여 click으로 오인하지 않는다.

Sleep은 IDLE/SITTING/LOOKING을 합친 비이동 quiet time이 120초 이상일 때 선택 가능하다. WALKING 완료, drag, reaction, sleep 완료는 quiet time을 다시 시작한다. 따라서 매 120초마다 무조건 자는 방식이 아니다. 실제 sleep 중에는 이동하지 않지만, 디스플레이 work area가 변경되면 화면 밖 방지를 위한 기존 clamp는 적용한다.

## Personality와 행동 선택

`TraitScore`는 0–100만 허용한다. 로컬 master 값은 curiosity=80, bravery=40, affection=75, energy=50, mischief=30이며 런타임 감소·성장·저장 기능은 없다. 시간·거리·weight 계수는 모두 `MOA_BEHAVIOR`에서 조절한다.

각 기여분은 정수 나눗셈으로 내림한다. 다음 weight들의 합을 기준으로 seeded xorshift sample을 누적 구간에 배정한다.

| 행동 | 기본 공식 | MOA 기본 weight |
|---|---|---|
| WALKING | 10 + energy×50/100 + mischief×10/100 | 38 |
| SITTING | 10 + (100−energy)×35/100 + (100−bravery)×5/100 | 30 |
| LOOKING | 10 + curiosity×50/100 + affection×10/100 + cursor bonus | 57, cursor 근접 시 97 |
| SLEEPING | quiet 조건 충족 시 5 + (100−energy)×50/100, 미충족 시 0 | 30 또는 0 |

모든 weight가 0이면 IDLE 시간을 재설정한다. seed와 simulation time을 주입하므로 테스트에서 실제 대기나 확률적 성공 조건을 사용하지 않는다. Controller가 wall clock을 직접 읽지 않는다.

## Cursor Awareness와 native 경계

이미 scheduler가 읽는 `NSEvent.mouseLocation`을 동일 tick에서 전달한다. 새 event tap, global keyboard hook, Accessibility 권한, timer 또는 polling thread는 없다. 기존 AppKit 화면 좌표에서 Companion 중심과 cursor의 거리를 계산한다. 160pt 안이며 15초 cooldown이 끝나면 IDLE/SITTING에서 LOOKING으로 진입할 수 있다. 정기 행동 선택 때에도 근접 cursor는 LOOKING weight를 높인다. 이 즉시 접근 반응은 weighted decision과 별도인 명시적 event다.

이동과 drag는 기존 `Area::clamp`와 work area 하단 범위를 재사용한다. 화면 배치 변경과 음수 좌표를 테스트한다. 전체 화면 이동, display 간 이동 정책, pixel-level click-through, native window focus 정책은 확장하지 않는다.

## 검증 (2026-09-17)

| 검사 | 결과 |
|---|---|
| `cargo test --locked --offline --manifest-path src-tauri/Cargo.toml` | PASS: 17개, 실패 0 |
| `cargo clippy --locked --offline --manifest-path src-tauri/Cargo.toml --no-deps -- -D warnings` | PASS: app warning 없음, 기존 vendored Tao warning 18개 유지 |
| `npm run build` | PASS: TypeScript 및 Vite production build |
| `python3 scripts/check_tao_patch.py` | PASS: upstream 대비 기존 문서화된 3개 파일 차이만 존재 |

테스트는 IDLE→WALKING/SITTING/LOOKING/SLEEPING 각각, resting state 완료, sleep eligibility/정지, drag 중 자동 전이 금지, drag→IDLE, click reaction, PIP lifecycle/proximity→REACTING→IDLE, drag release와 PIP 우선순위, personality weight, cursor 방향/cooldown, work area 변경/음수 좌표/clamp, seed 재현성을 포함한다. 네 가지 IDLE 전이는 같은 테스트 함수에서 각 상태를 독립 controller로 검증한다.

최초 frontend 검사는 로컬 `node_modules` 중복 타입 폴더 때문에 실패했다. 기존 lockfile 그대로 `npm ci --ignore-scripts` 후 정상 빌드되었으며 dependency/lockfile 변경은 없다.

`cargo fmt -p luma-spike -- --check`, `git diff --check`와 기존 foundation unit tests 8/8도 PASS했다. macOS debug `.app` bundle 생성 및 ad-hoc 서명 PASS. 기존 native/Dependency/lockfile/CI 파일은 foundation base 대비 변경 없음.

동일 bundle에서 기존 `scripts/launch_audit.m`를 사용한 실행 증거: [report.json](evidence/companion-v01/report.json), [smoke.log](evidence/companion-v01/smoke.log), [normal.log](evidence/companion-v01/normal.log). 실행 binary SHA-256은 report에 기록했다.

| Native 검증 | 결과 |
|---|---|
| 기존 PIP smoke, Codex foreground, 1회 | PASS: activation 0, key window 0, foreground 변경 0, 정상 종료 |
| spawn→roaming→proximity reaction→menu open→close→despawn | 자동 action/state log 확인, PASS; 실제 mouse click 검사는 아님 |
| 세 panel native 속성 | `opaque=0 level=3 keyAllowed=0 mainAllowed=0` 확인 |
| 추가 normal 70초 실행, 1회 | **focus harness FAIL**: 71.42초에 Codex→ChatGPT 전환 기록. LUMA activation 0, key window 0, exit code 0. 전환 원인은 확인하지 못했으며 실패를 제외하거나 PASS로 재분류하지 않음 |
| normal 실행 행동 | 34.19초 SITTING, 48.42초 IDLE 확인 |
| 실제 typing/click/drag 및 새 자세 시각 검증 | **MANUAL_REQUIRED**; 이번 bundle에서는 미수행 |

첫 audit 준비는 foreground bundle ID를 `com.openai.chat`로 예상했지만 실제 `com.openai.codex`여서 실행 전 대기 단계에서 중단했다. 실제 실행 두 건은 모두 위 증거에 포함한다. 이번 작업은 20/50회 startup 재인증이 아니며 Spike 01.1의 수동 GO 결과를 새 bundle 수동 검사로 재사용하지 않는다. 따라서 구현은 review 가능하지만 새 bundle의 포괄적 focus 회귀 PASS는 선언하지 않는다.

## 알려진 문제와 비용

- 임시 CSS 자세만 제공한다. 정식 sprite animation과 asset system은 범위 밖이다.
- Personality 공식은 초기 tuning이며 사용자별 실제 행동 빈도/수면 빈도는 아직 조정하지 않았다. 배포 후 설정 UI나 DB는 없다.
- 기존 33ms tick당 거리 계산과 고정 크기 snapshot 복사가 추가된다. weighted selection은 행동 선택 시에만 수행하며 추가 timer/thread/collection은 없다.
- LOOKING 중 cursor가 좌/우를 빠르게 오가면 direction snapshot 변경과 rendering이 기존 tick 빈도까지 증가할 수 있다. 새 장기 CPU/RSS benchmark는 필요하며, Spike 측정값을 이번 버전 측정값으로 주장하지 않는다.
- 기존 native focus·click-through 제약과 Tao vendor 유지보수 위험은 [Architecture](ARCHITECTURE.md), [Tao patch](tao-patch.md)에 그대로 적용된다.

## 실행과 다음 단계

`npm ci` 후 `npm run tauri -- dev`, 또는 `npm run tauri -- build --debug --bundles app`로 실행한다. 오른쪽 아래 MOA를 클릭/drag하고 우클릭으로 PIP을 생성한다. Battle/Capture는 기존 debug log만 남긴다. 새 행동은 정기 결정과 cursor 접근으로 확인한다.

다음 단계는 [manual focus test](manual-focus-test.md)를 새 bundle에서 수행하고, LOOKING/SITTING/SLEEPING 표현 및 빈도를 관찰하여 master tuning을 조정하는 것이다. 자동 Codex 재작업/Cloud automation은 보류 상태를 유지한다.

## Git 범위

브랜치는 `feature/companion-engine-v01`, base는 검증된 foundation `chore/development-foundation`의 `6c92fc9`다. Foundation이 아직 main에 병합되지 않아 PR도 foundation 대상으로 구성한다. Foundation 병합 후 main 대상으로 재지정할 수 있다. PR #3은 변경하지 않으며 이 PR도 자동으로 merge하지 않는다.
