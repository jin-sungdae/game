# Desktop Ground Coordinate bug fix

## Root cause와 수정 전 실측

수정 전 AppKit과 Rust는 모두 논리 point, bottom-left 원점, 위쪽 +Y였다. Retina 배율을 곱하거나 Y를 뒤집는 코드는 없었다. 따라서 좌표계 반전/배율 오류가 입증된 것은 아니다.

확인한 오류는 ground 제약이 없다는 점이다. World (x,y)를 NSPanel 좌측 하단으로 직접 전달했고, MOA/PIP 모두 96×104라고 가정했다. Spawn은 visibleFrame.minY+12였지만, drag clamp는 visibleFrame 아래 220pt 띠에서 자유로운 Y를 허용했다. MOA가 위로 이동한 뒤 그 높이를 유지하는 동안 PIP은 spawn 높이에 남았다. 이전 테스트는 이 동작을 허용했으며 실제 panel frame이나 공통 ground를 검사하지 않았다.

수정 전 실제 측정: primary frame=(0,0,2056,1329), visibleFrame=(0,0,2056,1290), scale=2. 기존 두 프로세스의 MOA bottom=116, PIP bottom=12였다. CGWindowList의 top-left 좌표는 이 화면에서 AppKit bottom=`1329−CG.y−height`로 해석했다. Runtime 코드에는 이 진단용 변환을 사용하지 않는다.

당시 primary visibleFrame.minY=0이므로 PIP bottom=12도 OS가 보고한 visibleFrame 안이었다. 따라서 사용자가 본 Dock 가림을 전부 원점 오류 때문이라고 단정하지 않는다. Auto-hide/다른 screen의 Dock/OS가 보고하지 않은 일시적 overlay는 별도의 한계다. 중복된 두 실행 역시 별도 문제이며 이번 변경에 Single Instance를 추가하지 않았다.

## 변경된 좌표 계약

- `NSScreen.screens.firstObject` primary 정책 유지. `frame ∩ visibleFrame`을 현재 usable desktop으로 읽는다. Dock bottom/left/right를 분기하거나 추정하지 않는다.
- Rust `Entity.x` = 전체 entity panel의 bottom-center X, `Entity.y` = ground Y (drag 중에는 현재 bottom Y).
- `groundY = usable.minY + LAYOUT.ground_margin`. 기본 8pt이며 Dock 높이 보정값이 아닌 시각적 여백이다.
- `Size.bounds(x,y)` = `(x−width/2, y, width, height)`.
- `Area.clamp`는 left/right/bottom/top 전체 bounds에 적용한다. `left≥minX+margin`, `right≤maxX−margin`, `bottom≥minY+ground_margin`, `top≤maxY−margin`.
- `LAYOUT.margin=8`, `ground_margin=8`, `menu_gap=6` 및 MOA/PIP/menu 크기는 `geometry.rs`에 한 번 정의한다. 현재 MOA/PIP 크기는 각각 96×104, menu는 160×140이다.
- GROUND entity는 idle/walk/spawn/roam/rest/reaction에서 동일 ground를 사용한다. Drag 중에는 전체 visible area 내에서 이동할 수 있고, release는 state 전이를 바꾸지 않은 채 공통 ground에 snap한다. 화면 변경에도 재계산한다.
- 드래그 중 공중 위치는 의도적인 예외다. 기존 220pt 세로 띠는 제거한다.
- 화면이 entity와 여백보다 작으면 배치 가능한 정수 frame 원점이 없는 것으로 판단하고 panel을 숨긴다. 크기를 줄이거나 bounds 밖으로 배치하면서 PASS라고 하지 않는다.

### Native frame 정수화

첫 수정 bundle 실측에서 NSPanel이 x=1909.631… 요청을 x=1909로 배치하는 현상을 확인했다. Simulation의 subpixel 이동을 바꾸지 않고 `Area.panel_bounds`에서 presentation 원점만 정수 logical point로 투영한다. 원점을 반올림한 뒤 허용 구간의 ceil(min)/floor(max)로 제한한다. 이는 Retina pixel 배율 보정이 아니다. 분수 visibleFrame에서도 예약 영역으로 반올림되어 넘어가지 않는다. 크기는 현재 정수 logical point master 값이다.

Native 진단에는 continuous world와 projected expected frame, 실제 NSPanel.frame을 모두 기록하므로 반올림 차이가 숨겨지지 않는다. fractional screen minY에서는 world ground와 actual bottom에 1pt 미만의 안쪽 정수화 차이가 있을 수 있으나 모든 entity가 같은 projected ground를 사용한다.

### Rendering anchor

WKWebView는 기존처럼 native panel을 채운다. CSS entity container는 별도의 96×104 고정 크기 대신 부모 bounds의 100%를 사용하고 flex-end로 하단 정렬한다. Local anchor는 `(width/2,height)` (CSS +Y 아래쪽)이며 AppKit world bottom-center와 대응한다. 여기서 entity bounds는 임시 그림과 이름/상태 label을 포함하는 전체 panel이다. 정식 sprite의 발 위치/투명 alpha trim은 이번 범위가 아니다. 상태 animation은 유지하고 overflow는 기존처럼 window 안에서 clip한다.

## 보호한 게임/desktop 로직

Companion 전이 규칙, Personality/master behavior weight, RNG/시간 정책, cursor 감지 반경/cooldown, PIP lifecycle/speed/proximity 임계값은 변경하지 않았다. Cursor 거리/방향 계산의 X에서 옛 좌측 원점의 반 폭을 제거하여 같은 공간상의 중심을 사용한다. PIP menu도 새 anchor에서 기존 gap만큼 위에 놓고 전체 bounds를 제한한다.

Tauri version, Cargo/npm dependency, Tao patch, LSUIElement/Accessory, NSPanel class/window level/nonactivating 설정, key window 정책과 focus audit는 변경하지 않았다. `panel.m` 변경은 usable rect 교집합과 opt-in 수치 진단뿐이다. 이전 dev startup activation 관찰을 이 PR에서 해결했다고 주장하지 않는다.

## 변경 파일

| 파일 | 내용 |
|---|---|
| `src-tauri/src/geometry.rs` | Size, layout configuration, anchor/bounds/ground/clamp/projection와 테스트 |
| `src-tauri/src/entities.rs` | entity별 native size, 기존 Area를 geometry로 이동 |
| `src-tauri/src/companion/mod.rs` | 새 anchor의 clamp/target/drag release와 cursor 중심 변환 |
| `src-tauri/src/companion/tests.rs` | 기존 기대 좌표 갱신 및 양끝 target 테스트 |
| `src-tauri/src/behaviors.rs` | 공통 ground를 사용하는 PIP 배치, MOA/PIP 통합 테스트 |
| `src-tauri/src/main.rs` | 공유 크기 사용, entity/menu panel 배치 연결 |
| `src-tauri/src/overlay.rs` | world→panel 변환, fits에 따른 visibility, 진단 FFI |
| `src-tauri/native/panel.m` | screen bounds 교집합, 실제 frame 진단 |
| `src/style.css` | native 크기 사용 및 bottom rendering anchor |
| 이 문서, README, evidence | 원인/수치/검증 기록 |

## 테스트와 실제 검증

Deterministic tests: 기존 17개를 유지하며 새 anchor의 기대 좌표만 갱신했다. 신규 테스트는 bottom/left/right Dock의 visibleFrame, negative X/Y, 다른 폭/높이, 네 방향 경계, 불가능한 viewport, fractional 경계/정수 native projection, 서로 다른 크기의 MOA/PIP ground 정렬, 상단 drag와 release 및 monitor 변경, 양끝 movement target을 검증한다.

macOS 검증 결과와 최종 artifact SHA-256은 `evidence/ground-coordinate/summary.json`, 실제 로그는 같은 폴더의 `runtime.log`에 기록한다. 실행은 기존 PIP smoke를 사용하며 수동 click/drag 및 Dock 설정을 바꾼 실험을 대신하지 않는다.

### 최종 결과 (2026-09-17)

- Rust **23/23 PASS**, 기존 foundation **8/8 PASS**, app fmt/clippy, TypeScript/Vite build, ad-hoc debug bundle build, Tao patch integrity, `git diff --check` PASS.
- Native 최종 PID **96391**, 10초 기존 smoke, geometry sample **17개 모두 PASS**: 전체 bounds 포함, projected frame=actual frame, reserved OS 영역 교차 면적 **0**, MOA/PIP bottom=ground.
- `screen.frame = (x=0,y=0,w=2056,h=1329)`, `visibleFrame = (0,0,2056,1290)`, `computedGroundLine=8`.
- MOA world `(1824,8)` → actual panel `(1776,8,96,104)`.
- PIP spawn 중 첫 sample world `(1998.23029585,8)` → projected/actual panel `(1950,8,96,104)`.
- 기존 PIP spawn/roam/proximity reaction/menu open/close/despawn/정상 종료 로그 확인. Focus audit activation **0**, key window **0**, 시작/종료 foreground 모두 DataGrip. 별도 연속 foreground observer는 실행하지 않았으므로 중간 외부 앱 전환 0을 인증하지 않는다.
- 로컬 `node_modules`에 중복 타입 폴더가 재생성되어 frontend build가 일시 실패했다. 동일 lockfile로 `npm ci` 후 최종 build PASS. Dependency/configuration 변경으로 우회하지 않았다.

최종 측정은 [summary.json](evidence/ground-coordinate/summary.json)과 [runtime.log](evidence/ground-coordinate/runtime.log), 정수화 전 발견은 [pre-projection.log](evidence/ground-coordinate/pre-projection.log)에 보존했다.

```sh
npm ci
npm run tauri -- build --debug --bundles app
open -n -W --stdout /tmp/luma-ground.log --stderr /tmp/luma-ground.log \
  --env LUMA_GEOMETRY_AUDIT=1 --env LUMA_FOCUS_AUDIT=1 --env LUMA_SMOKE=1 \
  'src-tauri/target/debug/bundle/macos/LUMA Spike.app'
```

`LUMA_GEOMETRY_AUDIT=1`은 최대 entity당 초당 1회 screen.frame, screen.visibleFrame, computedGroundLine, world position, expected/actual panel frame, fits 및 reserved intersection area를 출력한다. 기본 실행에서는 꺼져 있고 timer/thread/권한을 추가하지 않는다. 정수화 전 최초 측정 로그도 evidence에 별도로 보존한다.

## Known risks / 수동 확인

- Native 실제 검증은 현재 macOS/현재 primary arrangement에서만 수행한다. Left/right Dock과 음수 모니터 좌표는 deterministic fixture 검증이며 OS 설정을 임의로 바꾸지 않았다.
- Dock auto-hide가 일시적으로 보이는 영역을 visibleFrame이 예약하지 않으면, frame/visibleFrame만으로 그 가림을 예측할 수 없다. 이 PR은 OS가 보고한 usable bounds를 보장한다. Dock 높이를 추정하는 magic margin, Dock 설정 변경, accessibility hook을 넣지 않았다. [Apple visibleFrame 문서](https://developer.apple.com/documentation/appkit/nsscreen/visibleframe).
- 임시 sprite의 label 포함 bounds를 anchor로 삼는다. 발 위치/alpha bounds 보정, 다른 OS의 fractional panel size는 후속 검증 대상이다.
- 자동 smoke의 measured bounds PASS는 사용자의 모든 Dock/Spaces 상태에서 가림이 사라졌다는 수동 인증이 아니다. 수정 bundle에서 bottom/left/right Dock, drag down/up/release, 화면 재배치를 직접 확인한다.
- 기존 두 프로세스는 중복 실행 현상이며 새 코드로 추정하지 않는다. 최종 증거는 로그 PID와 artifact로 식별한다. Single Instance는 별도 안정화 작업이다.
