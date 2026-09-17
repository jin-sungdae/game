# Technical Spike 01.1 — Never Steal Focus

**판정: CONDITIONAL GO.** startup activation 경로를 제거하는 기술적 수정과 대조 실험은 완료했다. 그러나 **동일 최종 번들의 20회 완료 및 실제 수동 입력 검증은 남아 있어 GO가 아니다.** 이전 Spike 01 NO-GO 기록은 문서 아래에 보존한다.

## 변경/비변경 범위

Tauri/Tao startup patch, pre-run Accessory, LSUIElement, 로컬 ad-hoc signing, opt-in focus observer와 테스트 도구만 변경했다. `native/panel.m`, MOA/PIP entities, behavior/state, React 컴포넌트는 기존 커밋과 동일하다. 이전 앱 재활성화, NSApp.deactivate, global keyboard hook, 전투/서버/DB는 추가하지 않았다.

## 원인과 대조 실험

stock Tao의 `AppState::launched`는 policy 적용 뒤 `activateIgnoringOtherApps`를 호출한다. Tauri setup은 그 뒤에 실행된다. `scripts/build_stock_control.py`로 **같은 현재 앱/진단 코드에 registry Tao + 공식 Accessory-before-run 설정만** 적용한 대조 실행 파일을 따로 만들었다.

그 실행은 **t=0.327초에 activation 1회**, key window 0회를 기록하며 foreground가 대조 앱 PID로 바뀌었다. 이는 non-key NSPanel만으로 application activation을 막을 수 없고, 정책 변경만으로 해당 호출이 없어지지 않는다는 실행 증거다. 대조 앱 종료 후 포커스를 복구하는 코드는 없다.

기존 Prohibited → Accessory 완화책의 별도 1회 실행은 재현되지 않았다. 단일 PASS로 간헐 문제를 해결했다고 판정하지 않는다. [대조/후보 원본 결과](evidence/focus-01.1/summary.json).

## 반복 launch 결과 — 표본을 합쳐 20회 완료로 표시하지 않음

macOS 26.5 (25F71), Apple Silicon. 모든 patch 후보 반복 실험의 초기 foreground는 VS Code(`com.microsoft.VSCode`).

| 실행 | 시도 | 유효 PASS | LUMA activation | LUMA key window | 중단 사유 |
|---|---:|---:|---:|---:|---|
| patch 적용 직접 executable 실행, LSUIElement 추가 전 | 19 | 18 | 0 | 0 | 19회째 Slack 전환 |
| 최종 signed agent `.app`, LaunchServices batch 1 | 16 | 15 | 0 | 0 | 16회째 Codex 전환 |
| 같은 최종 `.app`, batch 2 | 2 | 1 | 0 | 0 | 2회째 Codex 전환 |
| 같은 최종 `.app`, batch 3 | 1 | 0 | 0 | 0 | 1회째 Codex 전환 |

- patch 적용 후보들의 유효 실행은 누적 **34회**이며 activation/key window 0회다.
- **동일 최종 `.app`의 유효 실행은 16회다. 요청한 최종 20회 검증은 미완료다.** 이전 후보의 결과를 가져와 최종 20회 PASS라고 하지 않는다.
- 최종 `.app`은 `open -n -W`로 실행했다. `-g`, `-j`, activates=false 같은 비활성 launch 옵션을 사용하지 않았다.
- 각 최종 launch는 2초 관찰 후 정상 종료했고, 앱 readiness와 내부 exit audit도 확인했다. 직접 executable 후보는 3초였다. 장시간 타이핑 검증을 대체하지 않는다.
- 외부 foreground 변경은 모두 실패/간섭 표본으로 원본 JSON에 보존했다. LUMA activation 0이라는 이유로 그 표본의 foreground 유지 검증을 PASS로 바꾸지 않았다.
- UI 자동화 연결 오류/타임아웃과 실제 foreground가 다른 앱인 상태도 발생했다. 대기 시간 만료나 실행 실패는 성공 표본에 포함하지 않는다.

최종 관측 binary SHA-256: `d3cbb6a2ed8e2934ad75b54521e3c62413bc9a4f8e20b0f5fdabcbd8ae8cee48`.

## 검증기의 신뢰 범위

`scripts/launch_audit.m`은 독립 프로세스로 실행되며 launch 이전에 NSWorkspace activation notification observer를 설치한다. 10ms foreground PID polling도 병행한다. LUMA 자체에는 main의 첫 단계에서 NSApplicationDidBecomeActive와 NSWindowDidBecomeKey observer를 설치했다. 따라서 이전 33ms app.active polling보다 짧은 전이도 기록할 수 있다. LaunchServices가 main 이전에 활성화하는 경우는 외부 observer가, 내부 일시적 활성화는 내부 observer가 보완한다.

검증기는 현재 foreground를 읽기만 하고 목표 앱을 activate하지 않는다. 실행 중 한 번이라도 다른 앱으로 바뀌면 실패하고 중단한다. 이전 앱 복구/자동 재시도는 없다. ready/exit 로그 누락, timeout, 비정상 종료도 실패다. report에는 모든 attempt의 PID, 알림/샘플 시간과 결과가 남으며 키보드 내용은 기록하지 않는다.

초기 번들에는 서명 검증 오류가 있었고, LaunchServices stdout/stderr를 작업 폴더에 두었을 때 launchd spawn EPERM도 발생했다. 로컬 ad-hoc 서명을 설정하고 **절대 경로의 `/private/tmp` 로그**로 실제 실행을 확인했다. 실패한 launch는 위 표의 실제 실행 수에 포함하지 않았다. 보호 설정을 끄거나 우회하지 않았다.

## 실제 입력 테스트

| 단계 | 01.1 결과 |
|---|---|
| VS Code 임시 문서 입력 준비 | 수행. UI 도구 입력 자체에서 글자 누락이 보여 연속 타이핑의 증거로 쓰지 않음 |
| 다른 앱 연속 typing + LUMA launch | 수동 검증 미완료 |
| MOA walking 중 typing | 수동 검증 미완료 |
| MOA click / drag 후 typing 지속 | 수동 검증 미완료 |
| PIP spawn / click / interaction UI / Close 후 typing 지속 | 수동 검증 미완료 |

이전 Spike의 기능 검증을 이번 focus PASS로 재사용하지 않는다. UI 도구의 대상 앱 조작과 실제 전역 keyboard focus는 같지 않으며, 앱을 앞에 가져오는 동작이 섞이면 결과가 오염될 수 있다. 실제 마우스/키보드로 남은 항목을 수행해야 한다.

## 빌드/정적 검사

- `npm run build`, `tauri build --debug --bundles app`: 통과.
- `codesign --verify --deep --strict`: 통과. 로컬 ad-hoc 서명이며 notarization은 하지 않음.
- `cargo test --locked --offline`: 기존 상태 머신 6/6 통과.
- `cargo clippy --locked --offline --no-deps -- -D warnings`: 앱 검사 통과. vendored upstream의 기존 경고 18개는 별도 표시됨.
- `python3 scripts/check_tao_patch.py`: registry 소스 대비 허용된 3개 파일만 변경된 것을 확인.
- `cargo tree -i tao -e features`: 하나의 patched Tao 0.35.3에 feature가 적용됨을 확인.
- behavior/entity/React/native panel 변경 없음 확인.

## 재현과 남은 GO 조건

프로젝트 루트에서 빌드 후 실행한다. 먼저 Code/Chrome/IntelliJ의 임시 입력란에 포커스를 두고, 테스트 중 앱을 전환하지 않는다.

```sh
clang -fobjc-arc -framework AppKit scripts/launch_audit.m -o /private/tmp/luma-launch-audit
/private/tmp/luma-launch-audit \
  "$PWD/src-tauri/target/debug/bundle/macos/LUMA Spike.app" \
  20 5 /private/tmp/luma-focus-launches com.microsoft.VSCode
```

첫 120초는 지정 앱 foreground를 기다린다. 결과는 `/private/tmp/luma-focus-launches/report.json`과 개별 launch 로그에 남는다. foreground 식별자는 Chrome `com.google.Chrome`, IntelliJ `com.jetbrains.intellij`로도 바꿀 수 있다. 같은 output 폴더를 재사용하면 덮어쓰므로 새 경로로 실행한다.

수동 입력 시나리오를 기록하려면 count 1 / seconds 120으로 실행한다. 실제 키보드로 계속 입력하고, 마우스로 MOA click/drag → MOA 우클릭 PIP spawn → PIP click → interaction UI → Close를 실행한다. walking은 기존 30–60초 interval을 그대로 기다린다. 각 단계에서 입력이 계속 원래 앱으로 가는지 확인한다. 입력 텍스트/비밀정보를 로그로 보내지 않는다.

GO 조건은 같은 최종 bundle의 20회 launch에서 activation/key 전이/foreground 변경이 모두 0이며, 위 실제 입력 시나리오도 모두 통과하는 것이다. 현재는 기술적 수정은 확인됐지만 이 조건을 완료하지 못해 CONDITIONAL GO다. macOS 다른 버전, Spaces/Stage Manager, Finder/로그인 자동 실행 등의 경로도 추가 회귀 위험이다.

---

# Spike 01 검증 결과 — 과거 기록

검증일 2026-09-17. macOS 26.5 (25F71), Apple Silicon, Node 18.20.7, Rust 1.98.1, Tauri 2.11.5 / Tao 0.35.3 / Wry 0.55.1, Vite 6.4.3. lockfile 기준. 실제 native debug 번들을 실행했다.

**판정: 조건부 NO-GO. 최종 실행에서 시작 직후 앱 활성화가 재현되어 Never Steal Focus는 미충족이다. 게임 개발 단계로 넘어가기 전에 해결해야 한다.**

| 항목 | 결과 / 증거 |
|---|---|
| TypeScript / Vite | `npm run build` 통과 |
| macOS Rust/ObjC 빌드 | `tauri build --debug --bundles app` 통과, `.app` 생성 |
| 정적 검사 | `cargo clippy -- -D warnings` 통과 |
| 상태 머신 테스트 | 6/6 통과: interval, walk cycle, click reaction, drag clamp/release, PIP lifecycle/proximity, area change/sleep |
| Transparent window | 실제 패널 생성 및 MOA 렌더링 확인. 네이티브 `opaque=0`, clearColor. 캡처 도구는 개별 창을 배경에 합성하므로 다른 앱이 투명 여백 뒤에 보이는 최종 합성 화면은 별도 수동 확인 필요 |
| Always on top | 세 패널의 실제 level=3 (NSFloatingWindowLevel) 확인. 여러 앱/Spaces 전체 조합의 시각 회귀 검증은 미완료 |
| 자동 동작의 focus | 시작 Prohibited / setup Accessory 완화책은 일부 실행에서만 효과가 있었음. 최종 실행 t=0.16초에 active=1, t=0.61초에 0 재현 → 시작 포커스 **실패**. 애니메이션 자체의 활성화는 관찰하지 못함. keyAllowed=0, mainAllowed=0 확인 |
| 클릭 중 focus | UI 자동화가 앱을 앞에 올리므로 오염된 관측. Chrome/IntelliJ/VS Code의 연속 타이핑과 수동 클릭/drag를 병행한 최종 검증은 **미완료**. 키보드 입력 내용은 수집하지 않음 |
| Click-through | fullscreen 창 없음. entity 밖 입력은 OS 기본 전달 구조. 작은 entity 직사각형의 투명 여백은 통과하지 않음. 아래 앱의 특정 버튼에 실제 클릭이 전달되는 종단 검증은 **미완료** |
| MOA click | 실제 WebView 클릭 후 AX 트리에 `MOA REACTING` 확인 |
| MOA drag | boundary/release 자동 테스트 통과. 최종 실행 UI drag 입력 후 좌표 (1776,82) → (1823.2,111.3) 변경 확인. 극단 경계/창 밖 release 실기 검증 필요 |
| MOA movement | 실제 AX 트리 `MOA WALKING` → `MOA IDLE` 확인. 30–60초 interval 범위 1,000회 자동 검증 |
| Work area boundary | negative origin / Dock offset / 화면 변경 clamp 테스트 통과. 실제 NSScreen.visibleFrame 사용. Dock 위치 변경/auto-hide/다중 디스플레이 실기 검증은 미완료 |
| PIP spawn | MOA 우클릭 후 실제 `PIP ENGAGED` AX 확인. smoke에서 SPAWNING → ROAMING 확인 |
| Proximity | smoke에서 ROAMING → ENGAGED와 MOA REACTING, 방향 변경 확인 |
| PIP interaction UI | React UI/IPC 구현. smoke에서 메뉴 표시/숨김 상태 및 native placement 경로 실행. 실제 Battle/Capture 버튼 클릭 로그까지의 종단 검증은 **미완료** |
| 정상 종료 | smoke에서 app.exit(0), exit code 0, cleanup 로그 확인. 최종 실행에서는 앱 메뉴 Quit LUMA Spike를 실제 클릭하여 exit code 0과 정리 로그도 확인 |
| CPU / Memory | 아래 30초 관측값. 장시간 누수/에너지 검증 아님 |

## 성능 관측

`python3 scripts/measure.py 46836 46844 46847 46848 46851 46852 --seconds 30`

- debug native process 1개 + 해당 실행 직후 생성된 WebKit GPU/Networking/WebContent helper 5개.
- macOS WebKit helper의 PPID는 1이므로 PPID만으로 tree를 합산하지 않았다. 실행 시점의 PID 생성 전후 차이로 대상을 식별했다. 전체 머신 WebKit 프로세스를 합한 값이 아니다.
- MOA/PIP 동작 확인 후의 혼합 관측. idle/walking/메뉴별로 분리한 통제 벤치마크는 아니다.
- CPU 평균 **1.74%**, 최대 **3.0%** (각 프로세스 `ps %cpu` 합계; OS의 감쇠 평균이며 정밀 interval CPU time 차분이 아님).
- RSS 평균 **178.4 MiB**, 최대 **183.6 MiB**. 공유 페이지가 프로세스 사이에 중복 집계될 수 있으며 physical footprint 값이 아니다.
- 진단 로그 추가와 초기 spawn 간격 조정 전 build에서 측정했다. release 빌드 성능을 대표하지 않는다.
- 원본: `artifacts/performance-debug.json` (로컬 생성물, gitignore). 런타임 로그/빌드 로그도 `artifacts/`.

## 남은 수동 검증 절차

1. Chrome 입력란에서 2분 이상 계속 입력하며 MOA 걷기 2회 이상 관찰. 같은 절차를 IntelliJ와 VS Code의 임시 문서에 반복한다. 앱 전환, caret 이동, 누락 입력이 없어야 한다.
2. 입력란 포커스를 유지한 상태로 MOA click/drag, PIP spawn/click/Battle/Capture/Close를 수행한다. 뒤 앱에 곧바로 이어서 타이핑되는지 확인한다. UI 자동화의 앱 활성화 동작을 제외한 실제 마우스로 실시한다.
3. MOA 사각형 밖에 있는 뒤 앱의 버튼은 클릭되어야 하고, MOA 안에서는 reaction/drag가 일어나야 한다. 투명 모서리에서 뒤 앱 클릭이 막히는 것은 현재 문서화된 제한이다.
4. MOA를 화면 네 변, Dock 방향, 하단 band 위쪽으로 drag하고 release한다. entity 전체가 visibleFrame 하단 220pt 안에 있어야 한다.
5. Dock 좌/우/하단, auto-hide, Retina 배율, 잠자기 복귀, 모니터 연결 해제, Spaces/Stage Manager를 각각 확인한다. 현재 기본 디스플레이만 지원한다.
6. PIP 50회 spawn/despawn 후 release 빌드로 30분 측정. WebKit helper RSS/physical footprint와 CPU/wakeups 추이를 확인한다.

## 다음 단계

가장 먼저 Tao/NSApplication 시작 활성화 문제를 해결하고 반복 launch 및 타이핑 병행 실기 검증을 완료한다. native view 재부모화의 수명 회귀 테스트도 필요하다. 통과 전 게임 시스템으로 범위를 확장하지 않는다. 이후 필요할 때만 panel integration을 정식 Tauri 플러그인 경계로 정리하고, multi-monitor 정책과 투명 여백 축소를 검토한다. 픽셀 단위 click-through를 polling hack으로 추가하지 않는다.

최종 재현은 `artifacts/final-runtime.log`에 기록했다. 시작 활성화와 UI 도구에 의한 활성화(t=7.35초)를 구분했다.
