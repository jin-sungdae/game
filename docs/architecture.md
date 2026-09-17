# LUMA Technical Spike 01 — Window 결정

목표는 macOS에서 작업 중인 앱의 키보드 포커스를 유지하며 작은 companion과 상호작용할 수 있는지 확인하는 것이다. 서버, DB, 로그인, 전투/포획 로직은 없다.

## 검토

| 방식 | 클릭 통과 | 포커스 | 비용/결정 |
|---|---|---|---|
| Fullscreen transparent Tauri window | CSS pointer-events는 같은 WebView 내 hit test일 뿐 다른 앱으로 통과하지 않음. setIgnoreCursorEvents는 창 전체 단위 | 넓은 창의 이벤트 수신과 활성화 위험 | 채택하지 않음. 실제 fullscreen 프로토타입을 실행해 비교한 것은 아니며 API 구조/공개 이슈 조사에 따른 제외 |
| Entity-sized Tauri NSWindow | 창 바깥은 OS가 원래 앱에 전달 | focusable(false)만으로 macOS 비활성화를 보장하기 어려운 공개 이슈 | 기본 NSWindow만 사용하는 방식도 보류 |
| Entity-sized native nonactivating NSPanel + Tauri WKWebView | 창 바깥은 OS가 원래 앱에 전달, 창 안은 interactive | NSPanel nonactivatingPanel, canBecomeKeyWindow/MainWindow=NO | 선택. MOA/PIP 96×104 pt, 메뉴 160×140 pt |

## 네이티브 경계

Tauri는 세 개의 숨겨진 host window 및 WebView/IPC 수명을 관리한다. Objective-C AppKit bridge는 실제 NSPanel을 생성하고 host의 contentView를 panel로 옮겨 소유한다. Rust의 main-thread tick에서 panel의 위치/표시를 제어한다. host는 다시 표시하지 않는다. Objective-C는 AppKit을 연결하는 데만 사용하며 게임/행동 로직은 Rust에 있다. 추가 NSPanel 플러그인, object_setClass, swizzling, focus 복구, global keyboard hook은 사용하지 않는다.

이 contentView 재부모화는 Tauri의 공식 window API 추상화 바깥이다. 그래서 native panel에 Tauri getCurrentWindow().setPosition(), drag, resize API를 사용하면 안 된다. 이 Spike의 명시적인 macOS 전용 통합 지점이며, Tauri/Wry 업데이트 시 IPC·첫 클릭·view 수명 회귀 테스트가 필요하다. Cargo.lock/package-lock.json을 유지한다.

NSFloatingWindowLevel은 일반 창 위에 둔다. 보안 UI, 잠금 화면, 독점 fullscreen 위를 보장하지 않는다. CanJoinAllSpaces/FullScreenAuxiliary를 설정했지만 Spaces/Stage Manager/별도 디스플레이 fullscreen은 별도 검증 항목이다.

## 클릭 통과의 정확한 범위

- entity 창 바깥: fullscreen 입력 차단 창이 존재하지 않아 원래 앱으로 직접 전달된다.
- entity 창 안: **96×104 직사각형 전체가 입력 영역**이다. glyph 외곽의 투명한 작은 여백도 차단된다.
- 메뉴: 별도 160×140 창. 메뉴를 닫으면 orderOut하므로 사라진 메뉴 영역이 클릭을 차단하지 않는다.
- 픽셀/DOM 단위 click-through는 구현하지 않았다. 커서 polling으로 ignoresMouseEvents를 토글하면 경계에서 첫 클릭을 잃는 race가 생길 수 있으므로 사용하지 않는다. 이 제한을 지원하는 것처럼 표시하지 않는다.

## 행동/좌표/수명

- entities.rs: 명시적 MOA/PIP enum, entity, work area.
- behaviors.rs: 순수 상태 전이, 주입된 시간/seed, random interval 30–60초, 이동·거리 계산. 외부 state machine 라이브러리 없음.
- main.rs: 단일 33ms scheduler. main-thread dispatch는 최대 하나만 대기. React에 state/facing/menu 변화만 emit.
- overlay.rs / native/panel.m: AppKit main-thread API, 창 표시/좌표, 전역 마우스 위치와 왼쪽 버튼 상태. 키보드 내용은 읽지 않음.
- stores/: 모든 WebView가 동일 Rust snapshot 구독. React 컴포넌트는 timer/random/state transition을 소유하지 않음.
- Dock/메뉴 바를 제외하는 NSScreen.visibleFrame을 사용. AppKit의 좌하단 원점 논리 point를 끝까지 유지해 Retina physical pixel 혼용을 피함.
- 기본 디스플레이 NSScreen.screens.firstObject만 사용. visibleFrame 하단 220pt band 안에서 entity 전체 크기를 clamp. Dock/화면 구성 변화는 tick마다 재평가. Auto-hide Dock은 OS가 visibleFrame에 보고하는 영역만 따른다.
- MOA drag는 네이티브 cursor delta로 수행하고 release를 OS 상태로 확인. 창 밖 release에도 종료. 5pt 미만 이동이면 click reaction. 이동 중 drag가 우선한다.
- PIP은 우측 work-area 경계 안쪽에서 fade in하며 좌측 이동한다. 화면 밖 spawn은 boundary 요구와 충돌하므로 하지 않는다. 근접 130pt에서 ENGAGED/REACTING, 160pt 밖에서 재개하는 hysteresis.
- 종료는 메뉴바 LUMA → Quit LUMA. Tauri app exit가 scheduler stop과 panel/status-item 정리를 수행한다.

## 공식 자료/공개 upstream 조사 (2026-09-17)

- [Tauri window API: focusable / ignore cursor events](https://tauri.app/reference/javascript/api/namespacewindow/)
- [Tauri WebviewWindowBuilder](https://docs.rs/tauri/latest/tauri/webview/struct.WebviewWindowBuilder.html)
- [Tauri macOS focusable=false 이슈 #14102](https://github.com/tauri-apps/tauri/issues/14102)
- [Tao 비활성 창 수정 PR #1210 — 조사 시 Open](https://github.com/tauri-apps/tao/pull/1210)
- [Apple NSPanel nonactivatingPanel](https://developer.apple.com/documentation/appkit/nswindow/stylemask-swift.struct/nonactivatingpanel)
- [Apple ignoresMouseEvents](https://developer.apple.com/documentation/appkit/nswindow/ignoresmouseevents)
- [Apple NSScreen.visibleFrame](https://developer.apple.com/documentation/appkit/nsscreen/visibleframe)

## 시작 시 활성화 검증에서 발견한 문제

Tao 0.35.3의 `AppState::launched`는 NSApplication activateIgnoringOtherApps를 호출한다. 첫 실행 로그에서 startup activation을 확인했다. event loop 실행 전에 Prohibited, setup에서 Accessory로 바꾸는 완화책을 시도했지만 **최종 재실행에서 시작 활성화가 재현되어 신뢰 가능한 해결책이 아니다. Never Steal Focus는 미충족**이다. 이전 앱에 focus를 되돌리는 hack은 사용하지 않았다. Tao 시작 경로와 Finder/로그인 자동 실행 등 launch 경로를 추가 조사해야 한다.
