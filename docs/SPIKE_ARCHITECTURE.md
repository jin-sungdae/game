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

# Technical Spike 01.1 — startup focus 수정

위 Spike 01의 NO-GO 기록은 당시 결과다. 01.1은 entity/behavior를 변경하지 않고 startup 경계만 수정한다.

## 정확한 호출 순서

1. Tao `TaoAppDelegateParent`가 `applicationDidFinishLaunching:`을 수신한다.
2. `AppState::launched`가 `apply_activation_policy`를 호출한다.
3. stock Tao는 visible window에 대한 `window_activation_hack` (`makeKeyAndOrderFront`) 후 `NSApplication.activateIgnoringOtherApps(ignore)`를 실행한다. 기본 ignore는 true.
4. 그 후 `HANDLER.set_ready`, `StartCause::Init`가 전달된다.
5. Tauri runtime의 Ready 처리에서 사용자 `setup`이 실행된다.

즉 setup의 focusable/Accessory 설정은 단계 3의 application-level activation 요청을 제거할 수 없다. non-key NSPanel은 window-level key 자격을 제어할 뿐 이 application-level 호출과 별개다. 이전 Prohibited-before-run → Accessory-in-setup 전환은 제거했다.

## 채택한 수정

- `App::set_activation_policy(Accessory)`를 `Builder::build()` 후, `App::run()` **이전**에 한 번만 호출한다. 이 공식 API는 runtime의 Tao event loop policy에 전달되어 launch 처리 첫 단계에 적용된다.
- opt-in `macos-no-activate-on-launch` Tao feature로 위 두 startup activation 경로를 컴파일에서 제외한다. [범위/원본 hash/diff](tao-patch.md).
- `Info.plist`의 `LSUIElement=true`로 main 이전 LaunchServices에도 agent 앱임을 선언한다. runtime API 호출과 별도 경계다.
- 로컬 `.app`을 재현 가능하게 검증하도록 macOS ad-hoc signingIdentity `-`를 설정한다. notarized 배포 패키지는 아니다.
- `native/panel.m`, entity, behavior 및 React 컴포넌트는 그대로다. 새로운 `native/focus_audit.m`은 환경변수를 켰을 때만 동작하는 알림 observer다.

## 공식 API / upstream 조사 (2026-09-17)

Tao 자체 `set_activate_ignoring_other_apps`는 존재하지만 Tauri 2.11.5의 App/RuntimeInitArgs/runtime에는 노출되어 있지 않다. `App::wry_plugin`도 이미 만들어진 window target의 event callback이며, mutable startup EventLoop를 받는 공식 우회 경로가 아니다.

- [Tauri 요청 #15017](https://github.com/tauri-apps/tauri/issues/15017): 해당 Tao API 노출 요청, 조사 시 open.
- [Tao PR #1210](https://github.com/tauri-apps/tao/pull/1210): open / merged=false, head `bc16c5fd1c8f5dc86a949e10ccf67f4edead4cc3`. window.rs의 orderFront → orderBack 변경이며 AppState::launched의 activation 호출은 수정하지 않음.
- [Tao 0.37.0 startup 소스](https://github.com/tauri-apps/tao/blob/tao-v0.37.0/src/platform_impl/macos/app_state.rs): 2026-08-21 최신 Tao 릴리스에서도 같은 activation 호출 유지. 버전 변경만으로 이 원인을 제거할 수 없다는 것은 **소스 비교 결과**이며 0.37으로 LUMA 전체를 이식해서 실행했다는 뜻은 아니다.
- [Tauri 2.11.5 App API](https://docs.rs/tauri/2.11.5/tauri/struct.App.html#method.set_activation_policy)
- [Apple LSUIElement](https://developer.apple.com/documentation/bundleresources/information-property-list/lsuielement)

Tauri는 `=2.11.5`로 고정했다. Tao는 같은 `0.35.3`의 local patch이며, Wry 0.55.1 / tauri-runtime-wry 2.11.4는 변경하지 않았다. 전체 framework 교체는 하지 않는다.

## 최종 검증 후 architecture 유지

이번 최종 검증에서는 Tauri/Rust behavior/state, entity-sized native nonactivating NSPanel, WKWebView, startup opt-in patch를 변경하지 않았다. 검증 도구에 기존 smoke 실행 옵션과 foreground 대기 로그, 종료 원인 검사를 추가했다. artifact별 해시와 결과는 [최종 validation](validation.md), 실제 mouse/typing은 [수동 체크리스트](manual-focus-test.md)에서 관리한다. 자동 상태 전이 검증은 실제 DOM hit testing이나 사람의 입력 검증을 대신하지 않는다.
