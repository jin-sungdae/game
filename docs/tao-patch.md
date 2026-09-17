# Spike 01.1: minimal Tao patch

현재 구조를 유지하는 선택 B: Tauri 2.11.5 + Tao 0.35.3의 opt-in startup patch.

## 출처와 범위

`src-tauri/vendor/tao`는 crates.io에서 받은 Tao 0.35.3의 소스다. registry cache marker 파일 두 개만 제외했으며 라이선스, copyright, 예제, 원래 manifest는 보존했다. publish provenance는 `.cargo_vcs_info.json`에 있고, 모든 원본 파일 SHA-256은 `evidence/tao-0.35.3-sha256.json`에 있다.

변경 파일은 정확히 세 개다:

1. `Cargo.toml`: 기본값이 꺼진 `macos-no-activate-on-launch` feature 추가.
2. `Cargo.toml.orig`: 같은 feature 선언.
3. `src/platform_impl/macos/app_state.rs`: feature가 켜지면 `AppState::launched`의 `window_activation_hack`와 `activateIgnoringOtherApps`를 컴파일에서 제외. 해당 함수용 import만 지역화.

전체 diff: [tao-no-activate.patch](evidence/tao-no-activate.patch).

```sh
python3 scripts/check_tao_patch.py
cargo tree --manifest-path src-tauri/Cargo.toml -i tao -e features
```

Cargo의 feature unification을 이용한다. 앱이 직접 참조하는 Tao는 새로운 runtime 라이브러리를 더하는 것이 아니라 Tauri runtime이 이미 사용하는 **동일한 한 개 Tao**에 opt-in feature를 켠다. `[patch.crates-io]`가 registry copy를 local copy로 대체한다. `Cargo.lock`에는 한 개의 Tao 0.35.3만 존재한다.

## 왜 false 인자를 전달하는 대신 호출을 제외하는가

Tao 자체에는 `EventLoopExtMacOS::set_activate_ignoring_other_apps(false)`가 있다. 그러나 Tauri 2.11.5의 runtime/App API에는 전달 경로가 없다. 게다가 false는 activation API를 호출하지 않는다는 뜻이 아니라 다른 앱을 무시하지 않는다는 뜻이다. 이 앱의 조건은 startup에서 activation을 요청하지 않는 것이므로 해당 호출을 아예 제외한다. 같은 startup 함수의 visible-window `makeKeyAndOrderFront` 보정도 제외한다. LUMA의 host window는 모두 hidden이고 native NSPanel만 `orderFrontRegardless`로 표시되므로 그 보정은 필요 없다.

feature가 꺼진 다른 Tao 사용자는 원래 startup 경로를 유지한다. 이벤트 루프 준비/콜백, activation policy 적용, Dock 처리 등 다른 경로는 유지했다. object_setClass, swizzling, 이전 앱 activate, NSApp.deactivate, global keyboard hook을 추가하지 않았다.

## 대안 비교

| 우선순위 | 검토 결과 |
|---|---|
| A: 설정/버전만 | pre-run Accessory는 공식 API이고 채택. 단독으로 명시적인 activation 호출을 제거하지는 못함. Tao 0.37.0에도 같은 호출이 남아 있음. 현재 runtime은 Tao ^0.35.0이므로 0.37.0은 drop-in 업데이트도 아님. |
| B: 최소 Tao patch | 채택. 위 세 파일만 변경. 앱과 behavior 구조 유지. |
| C: native host + WebView/Rust | NSApplication 수명 전체를 제어할 수 있지만 IPC/메뉴/번들 수명을 다시 연결해야 함. B가 검증되면 이번 범위에서 필요 없음. |
| D: 다른 framework | 해당 framework의 startup 정책도 별도 검증 필요. 현재 문제 하나 때문에 교체하지 않음. |

## 유지보수 위험

local fork이며 upstream 공식 해결책은 아니다. upstream 업데이트를 자동 수용하면 feature가 사라지거나 별도 activation 경로가 생길 수 있다. 새 버전으로 바꿀 때 patch integrity, `cargo tree`의 단일 Tao, 20회 launch audit, 수동 입력 회귀 테스트를 함께 실행해야 한다. enabled feature는 새 일반 key window가 startup에서 자동으로 key가 될 것을 기대하는 앱에는 적합하지 않다. 현재 LUMA는 nonactivating entity panel만 사용한다.

현재 Rust에서 vendored upstream의 기존 deprecated/unused 경고가 드러난다. 관련 없는 Tao 플랫폼 코드를 정리해서 diff를 확대하지 않았다.
