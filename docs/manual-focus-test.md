# 수동 focus 검증 — Technical Spike 01.1

사용자 최종 확인(2026-09-17): 실제 macOS에서 launch/MOA interaction의 keyboard focus 유지 PASS로 Spike GO 확정. 아래 앱별 세부 표는 별도 입력이 없으므로 임의로 채우지 않는다. 다음 회귀 검증에서는 **MANUAL REQUIRED**. 자동 상태 전이/launch 검사로 실제 mouse/typing PASS를 대신하지 않는다.

1. Chrome 빈 입력란, IntelliJ 임시 문서, VS Code 임시 문서 중 하나를 열고 계속 타이핑한다. 비밀정보는 사용하지 않는다.
2. 아래 명령을 터미널에서 시작하고 120초 안에 대상 문서로 돌아간다. 검증기는 대상 앱 foreground를 기다린 후 LUMA를 실행하며 포커스를 복구하지 않는다.
3. 각 동작 직후 **문서를 다시 클릭하지 말고** 바로 타이핑한다. 원래 caret에 글자가 들어가야 PASS다. 입력이 끊기거나 다른 앱으로 가면 FAIL이다.
4. 앱별로 새 로그 폴더를 사용한다. FAIL 시 단계와 시간을 기록한다. 로그에는 키 입력 내용이 수집되지 않는다.

```sh
clang -fobjc-arc -framework AppKit scripts/launch_audit.m -o /private/tmp/luma-launch-audit
/private/tmp/luma-launch-audit \
  "$PWD/src-tauri/target/debug/bundle/macos/LUMA Spike.app" \
  1 180 /private/tmp/luma-manual-code-01 com.microsoft.VSCode
```

Chrome: `com.google.Chrome`, IntelliJ: `com.jetbrains.intellij`로 마지막 인자를 바꾼다. 180초 뒤 자동 종료한다. 시간이 부족하면 600으로 늘린다. 기존 LUMA는 먼저 종료하고, 자동 종료 시점과 수동 Quit 시점을 구분해서 적는다.

| 순서 / 동작 직후 즉시 타이핑 | Chrome PASS/FAIL | IntelliJ PASS/FAIL | VS Code PASS/FAIL |
|---|---|---|---|
| LUMA launch / MOA IDLE | 미실시 | 미실시 | 미실시 |
| 30–60초 기다려 MOA WALKING 확인 | 미실시 | 미실시 | 미실시 |
| MOA 클릭, reaction 확인 | 미실시 | 미실시 | 미실시 |
| MOA drag 후 놓기 | 미실시 | 미실시 | 미실시 |
| 화면/Dock 경계까지 drag, work area 안에 유지 | 미실시 | 미실시 | 미실시 |
| MOA 우클릭으로 PIP spawn | 미실시 | 미실시 | 미실시 |
| PIP 접근 시 MOA reaction | 미실시 | 미실시 | 미실시 |
| PIP 클릭 → interaction UI open | 미실시 | 미실시 | 미실시 |
| Battle 클릭 (debug log만) | 미실시 | 미실시 | 미실시 |
| Capture 클릭 (debug log만) | 미실시 | 미실시 | 미실시 |
| Close 클릭 → UI 닫힘 | 미실시 | 미실시 | 미실시 |
| LUMA 메뉴 → Despawn PIP | 미실시 | 미실시 | 미실시 |
| 패널 밖 클릭/입력, 투명 배경/항상 위 표시 확인 | 미실시 | 미실시 | 미실시 |
| LUMA 메뉴 → Quit, 원래 문서 입력 지속 | 미실시 | 미실시 | 미실시 |

메뉴를 누르는 동안 메뉴가 입력을 받는 것은 macOS 동작이지만 메뉴를 닫은 뒤 다른 창 클릭 없이 원래 문서로 입력이 이어져야 한다. 작은 entity window의 투명 모서리는 click-through가 아니다. entity window 밖만 다른 앱에 전달된다.

검증일 / macOS / 앱 버전 / bundle SHA-256 / 검사자 / FAIL 시각을 함께 기록한다. `report.json`의 activation, keyWindows, foregroundChanged가 모두 0/false이고 실제 타이핑 항목까지 PASS여야 최종 GO다. 사람이 기록한 결과를 이 문서와 validation.md에 반영한다.
