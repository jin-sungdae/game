# Technical Spike 01.1 — 최종 검증

2026-09-17, macOS 26.5 (25F71), Apple Silicon. 이전 누적 결과는 [초기 검증 기록](validation-01.1-initial.md)에 분리 보존한다. 이 문서는 새로 빌드한 단일 debug artifact만 다룬다.

**판정: CONDITIONAL GO.** 동일 최종 bundle에서 **Codex foreground 기준 50/50 PASS**. 자동 regression/runtime 검사는 통과했다. **Chrome/IntelliJ/VS Code에서의 실제 mouse/typing 및 startup 재확인은 MANUAL REQUIRED**이므로 GO로 승격하지 않는다. 요청된 편집기 기준 자동 batch는 아래처럼 실패/간섭으로 보존하며 Codex 결과를 편집기 PASS로 표시하지 않는다.

## 동일 최종 bundle 반복 결과

| 새 batch / foreground | 실행 / PASS | activation | foreground 변경 실행 | key window | 비정상·미확인 종료 |
|---|---:|---:|---:|---:|---:|
| Codex, 기본 LaunchServices | **50 / 50** | **0** | **0** | **0** | **0** |
| VS Code, 준비 확인 전 | 4 / 3 | 0 | 1 (Finder) | 0 | 0 |
| VS Code, 준비 확인 후 | 1 / 0 | 0 | 1 (DataGrip) | 0 | 0 |
| VS Code, 20회 요청 batch | 1 / 0 | 0 | 1 (Preview) | 0 | 0 |
| VS Code, 명시적 foreground 대기 | 0 / 0 | — | — | — | — |

마지막 VS Code 대기는 120초 동안 Codex가 foreground여서 launch 없이 종료했다. 외부 전환의 원인은 확정하지 않았으며 LUMA activation 0을 근거로 실패 표본을 PASS로 바꾸지 않았다. 과거 16회/누적 34회는 이번 표에 포함하지 않았다.

[50회 원본 보고서](evidence/focus-final-01.1/startup-codex.json), [해시 재검사·집계](evidence/focus-final-01.1/summary.json), [전체 증거](evidence/focus-final-01.1/). 각 launch는 2초 관찰과 ready/exit/cleanup 확인을 포함한다. 50회 batch 초반에는 동일 artifact의 70초 walking 검사를 별도 프로세스로 병행했다. 후반 **25–50회(26회)**는 walking 프로세스 종료 이후다. 장시간 입력 검증과 다른 OS/실행 경로의 보장을 의미하지 않는다.

## 최종 artifact

- Tauri 2.11.5 / Tao 0.35.3 opt-in patch / LSUIElement=true / pre-run Accessory / nonactivating NSPanel 유지.
- executable SHA-256: `c246e1ca3beb8133d4af4e84b39f415f7b6c7f75171ffd4afccb5d4611fbe0b5`.
- [전체 bundle 파일 해시](evidence/focus-final-01.1/artifact.json). 빌드 후 `/private/tmp/luma-final-011/LUMA Spike.app`으로 복사하여 동일 artifact를 실행했다. 결과 작성 후 전체 파일 해시를 재비교하여 모두 동일함을 확인했다.
- 새 기능, dependency, vendor/native/entity/behavior/React 변경 없음. 수정 범위는 검증 도구와 문서뿐이다.

## Root cause / 해결책

Tao `AppState::launched`는 Tauri setup보다 먼저 `window_activation_hack`와 `activateIgnoringOtherApps`를 실행한다. non-key NSPanel과 Accessory policy만으로 application activation 요청이 제거되지는 않는다. 기존 stock 대조 실행에서 activation 1회를 확인했다. 최소 opt-in patch는 startup의 두 activation 경로만 제외한다. 이벤트 루프, policy, native hosting은 유지한다. 정확한 세 파일 diff와 upgrade 위험은 [tao-patch.md](tao-patch.md)에 있다.

## 자동 regression과 runtime 검증

| 항목 | 이번 결과 / 한계 |
|---|---|
| cargo test | PASS 6/6: interval, walking, click reaction, drag clamp/release, PIP lifecycle/proximity, work area 변경 |
| cargo clippy --no-deps -- -D warnings | 앱 PASS. vendored upstream 기존 경고 18개는 남음 |
| npm build / debug bundle | PASS: TypeScript, Vite, Rust/ObjC, bundling |
| codesign --verify --deep --strict | PASS, 로컬 ad-hoc 서명 |
| Tao patch integrity | PASS: registry 대비 정확히 문서화한 3개 파일만 변경 |
| Transparent panel / always-on-top | 실제 생성 로그 세 panel 모두 opaque=0, level=3, keyAllowed=0, mainAllowed=0. 다른 앱 배경과의 합성/Spaces 시각 확인은 MANUAL REQUIRED |
| MOA click / drag / work area boundary | 상태 머신 회귀 PASS. 실제 mouse 입력과 Dock 경계 시각 검증은 MANUAL REQUIRED |
| PIP spawn / proximity reaction / interaction UI open / Close / despawn | 기존 smoke로 상태 전이와 native 창 표시/숨김 경로 PASS. 실제 DOM 버튼 클릭 검증을 대신하지 않음 |
| 정상 종료 | smoke Tauri app.exit 경로와 startup audit의 AppKit terminate 경로에서 exit audit 및 cleanup 확인 |
| Battle / Capture 클릭 | MANUAL REQUIRED. 기존 debug log 분기 유지; 자동 클릭 PASS를 주장하지 않음 |

Runtime smoke는 Codex(`com.openai.chat`) foreground 기준 약 10초 동안 activation 0 / key window 0 / foreground change 0 / 정상 종료 PASS다. 실제 로그에서 IDLE, SPAWNING, ROAMING, REACTING/ENGAGED, menu=true/false, DESPAWNING, PIP=None을 확인했다. 자동 smoke는 기존 behavior 메서드를 호출하며 mouse event/IPC/React hit testing을 검증하지 않는다.

70초 일반 실행은 실제 t=41.31초에 WALKING, t=45.27초에 IDLE로 돌아왔다. x=1776.0 → 1617.9 이동, activation/key/foreground 변경 0, 정상 종료. 이 또한 Codex 기준이며 실제 타이핑을 포함하지 않는다.

## 실제 사용자 검증

**MANUAL REQUIRED**: launch 중 연속 typing, IDLE/WALKING, MOA click/drag, PIP spawn/click, interaction open, Battle/Capture/Close, despawn, Quit 직후 원래 문서 caret에 입력 유지. [간단한 Chrome / IntelliJ / VS Code 체크리스트](manual-focus-test.md)를 사용한다. 현재 사람이 완료했다고 보고한 항목은 없다.

## 재현

```sh
clang -fobjc-arc -framework AppKit scripts/launch_audit.m -o /private/tmp/luma-launch-audit
/private/tmp/luma-launch-audit \
  "$PWD/src-tauri/target/debug/bundle/macos/LUMA Spike.app" \
  20 2 /private/tmp/luma-new-startup-01 com.microsoft.VSCode
```

초기 foreground는 120초까지 기다린다. 새 output 경로를 사용한다. default `open -n -W`이며 `-g`/`-j` 없음. foreground observer + 10ms polling + main 이전 내부 notification observer를 사용한다. 포커스 복구, keyboard hook, 사용자 입력 기록 없음. ready/exit 누락, timeout, signal/nonzero exit, foreground 변경은 실패하며 즉시 중단한다.

기존 smoke를 같은 검증기로 실행하려면 count 1 / seconds 12 뒤에 `smoke` 인자를 추가한다. 일반 walking은 count 1 / seconds 70으로 실행한다. `scripts/summarize_focus.py BUNDLE REPORT BEFORE_MANIFEST`는 한 batch만 집계하고 전체 artifact 파일 해시를 재검사한다. 과거 실행을 합산하지 않는다.

## Known risks

- 관측된 실행의 통과는 모든 macOS/실행 경로에서 focus가 절대 바뀌지 않는다는 수학적 증명이 아니다.
- local Tao patch와 hidden WKWebView host → NSPanel 연결은 upgrade 시 재검증해야 한다.
- entity-sized 사각 창의 투명 모서리는 interactive이며 per-pixel click-through가 아니다. 창 밖은 OS가 다른 앱에 전달한다.
- 실제 mouse/typing, 다른 macOS, Spaces/Stage Manager, Finder/로그인 실행, release/notarized artifact는 별도 검증이다.
- 이번 작업에서 CPU/memory를 재측정하지 않았다. 이전 Spike 측정치를 새 artifact 결과로 재사용하지 않는다.
