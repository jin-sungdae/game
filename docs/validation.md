# Spike 01 검증 결과

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
