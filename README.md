# Project LUMA · Technical Spike 01

macOS에서 작업 앱을 방해하지 않는 Ambient Desktop Creature UX 검증용. **게임 구현이 아니라 native overlay 실험**이다.

현재 Technical Spike 01.1은 **GO**입니다. 동일 bundle의 Codex foreground 50/50 자동 검사와 사용자의 실제 macOS launch/MOA interaction focus 유지 확인을 근거로 확정했습니다. [검증 기록](docs/validation.md).

개발 기반: [규칙](AGENTS.md), [설계](docs/GAME_DESIGN.md), [Architecture](docs/ARCHITECTURE.md), [Review](docs/REVIEW_RULES.md), [Workflow](docs/DEVELOPMENT_WORKFLOW.md).

## 실행

필수: macOS, Xcode Command Line Tools, Rust stable, Node.js 18+ (이 환경에서는 Node 18.20.7 / Vite 6 사용). 새 환경은 유지보수 중인 Node LTS 권장.

```sh
npm ci
npm run tauri -- dev
```

배포용 게임 패키지가 아닌 로컬 검증용 번들:

```sh
npm run tauri -- build --debug --bundles app
```

`src-tauri/target/debug/bundle/macos/LUMA Spike.app`을 실행한다. ad-hoc 서명한 로컬 빌드이며 notarization은 하지 않았다. `npm run dev`만으로 브라우저를 열면 native overlay는 동작하지 않는다.

이 작업에서 Rust가 없어서 사용자 PATH를 변경하지 않고 `/private/tmp`에 설치했다. 현재 머신에서 해당 임시 툴체인을 쓰려면:

```sh
export PATH="/private/tmp/luma-cargo/bin:$PATH"
export CARGO_HOME=/private/tmp/luma-cargo
export RUSTUP_HOME=/private/tmp/luma-rustup
npm run tauri -- dev
```

임시 폴더가 삭제되면 공식 Rust 툴체인을 설치해야 한다.

## 조작

- MOA: 좌클릭 반응, 좌버튼 드래그. 기본 디스플레이 하단 work area 내에서만 이동.
- MOA 우클릭 또는 macOS 메뉴바 **LUMA → Spawn PIP**: PIP 한 마리 생성.
- PIP 클릭: 별도 floating 창에 PIP / Battle / Capture / Close 표시.
- Battle / Capture: 실행 터미널에 `[LUMA DEBUG]` 로그만 남김.
- LUMA → Despawn PIP: 소멸 애니메이션.
- LUMA → Quit LUMA: 정상 종료. 개발 실행은 터미널 Ctrl+C로도 중단 가능.
- 키보드 포커스를 받지 않도록 설계했으므로 entity 창의 키보드 탐색은 지원하지 않는다.

## 검증

```sh
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
LUMA_SMOKE=1 './src-tauri/target/debug/bundle/macos/LUMA Spike.app/Contents/MacOS/luma-spike'
python3 scripts/measure.py <LUMA_PID> <WEBKIT_HELPER_PID> --seconds 30
```

Smoke 모드는 약 10초 동안 spawn → interaction → close → despawn → Tauri 정상 종료를 실행한다. 실제 마우스 입력 테스트를 대체하지 않는다. 개발 로그에는 상태, 위치, app activation 변경만 기록하며 키보드 내용은 수집하지 않는다.

## 파일 지도

| 경로 | 책임 |
|---|---|
| `src/components/` | MOA/PIP 임시 CSS 그림, interaction UI |
| `src/entities/assets.ts` | 교체 가능한 이름/색상 |
| `src/stores/entities.ts` | Rust snapshot/event 구독 |
| `src/types/entity.ts` | frontend DTO |
| `src/overlay/bridge.ts` | IPC 입력 전달 |
| `src/behaviors/README.md` | Rust 행동 계층 위치 설명 |
| `src-tauri/src/entities.rs` | 상태 enum, entity, boundary |
| `src-tauri/src/behaviors.rs` | timer/random/movement/state 전이 및 테스트 |
| `src-tauri/src/overlay.rs` | AppKit FFI |
| `src-tauri/src/main.rs` | scheduler/IPC/lifecycle/진단 |
| `src-tauri/native/panel.m` | 실제 nonactivating NSPanel, work area, 메뉴바 |
| `src-tauri/{Cargo.toml,Cargo.lock,build.rs,tauri.conf.json,capabilities/}` | Rust/Tauri 빌드와 최소 event 권한 |
| `scripts/measure.py` | CPU/RSS 측정 |

[Window 결정과 OS 제한](docs/ARCHITECTURE.md) · [검증 결과](docs/validation.md)

## Spike 01.1 focus audit

[현재 검증 결과](docs/validation.md) · [최소 Tao patch 범위](docs/tao-patch.md) · [실행 증거](docs/evidence/focus-01.1/summary.json)

`src-tauri/vendor/tao`는 기존 Tao 0.35.3의 opt-in startup 수정입니다. Tauri/Wry/entity/behavior 구조는 유지합니다. `Info.plist`의 LSUIElement와 pre-run Accessory를 사용하며, 다른 앱을 다시 activate하는 포커스 복구 코드는 없습니다.

반복 실행 도구는 `scripts/launch_audit.m`이며 컴파일/실행법은 검증 보고서에 있습니다. 기본 실행은 audit가 꺼져 있고, `LUMA_FOCUS_AUDIT=1`을 설정할 때만 activation/key-window notification을 기록합니다. `LUMA_AUDIT_EXIT_SECONDS=120`으로 검증용 자동 정상 종료를 설정할 수 있습니다.
