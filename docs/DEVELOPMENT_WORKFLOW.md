# Development Foundation & GitHub Automation

## Branch / Human Gate

요구사항 → 한 목적의 branch → Codex 구현/검증 → PR → GitHub event → 자동 검증 → 필요한 수정 → 같은 branch push → 재검증 → Human Gate → 사용자가 merge.

현재 main=`44bf9ea`, 검증된 Spike HEAD=`dcf1e72`이며 PR #1은 아직 열려 있다. `chore/development-foundation`은 `dcf1e72`에서 분기한다. foundation PR은 **spike/focus-startup-fix를 base로 하는 stacked PR**로 만들고 #1 선행 의존성을 명시한다. 기존 spike branch/main에 push하지 않는다. 사용자가 #1을 merge한 뒤 foundation PR base를 main으로 변경하고 새 base 검증을 실행해야 한다. 지금 main으로 merge하거나 spike 이력을 다시 쓰지 않는다.

## Jobs and event flow

`.github/workflows/pr-validation.yml`은 `pull_request: opened, synchronize, reopened`에서 즉시 실행된다. polling scheduler는 없다. 새 commit은 synchronize, 같은 PR 진행 중인 오래된 실행은 concurrency로 취소한다.

| Job | Runner / 실제 검증 |
|---|---|
| desktop-static | Ubuntu: npm ci, TypeScript/Vite build, 자동화 정책 단위 테스트, Tao integrity, whitespace 검사 |
| macos-native | macOS 14: 앞 job의 dist 재사용, Rust fmt, cargo test(결정론적 6개 + native link), cargo clippy --no-deps -- -D warnings, AppKit audit harness compile |
| review-result | Ubuntu: 항상 job 결과를 집계, `LUMA_REVIEW_RESULT` JSON artifact와 Step Summary 생성. skipped/cancelled/missing을 PASS로 처리하지 않음 |

Rust는 stable toolchain이며 runner 버전과 toolchain 업데이트는 별도 재현성 위험이다. vendor 기존 경고는 표시하며 관련 없는 patch 확대로 없애지 않는다. macOS 빌드는 한 job으로 모아 중복 npm build/전체 bundle build를 피한다. hosted runner의 AppKit 컴파일 통과는 실제 WindowServer/사용자 입력 검증이 아니다. focus runtime, 투명 합성, mouse/typing은 **MANUAL_REQUIRED / NOT_RUN**으로 표시한다.

## Codex 연결 — 공식 지원과 현재 상태를 분리

공식 [GitHub integration](https://learn.chatgpt.com/docs/third-party/github)은 연결된 repository에서 `@codex review` 및 task 요청을 지원한다. review가 자동 commit/push까지 한다는 의미는 아니다. Codex cloud repository environment와 GitHub 연결/해당 repository 접근, code review 설정을 확인해야 한다. 이 로컬 Codex 대화 또는 gh 인증만으로 cloud integration 설치를 증명할 수 없다.

공식 [Codex GitHub Action](https://learn.chatgpt.com/docs/github-action)은 `openai/codex-action`으로 CI에서 Codex를 실행할 수 있다. 선택 시 별도 `OPENAI_API_KEY` secret과 API 사용 권한/비용 설정이 필요하다. 현재 repository secret 목록은 비어 있어 Action 기반 executor는 **미설치/비활성**이다. secret 값을 요청하거나 코드에 넣지 않는다.

**현재 구현은 event 기반 검증 + machine-readable 수정 요청 준비까지다. 무인 FAIL→Codex→push 자동 수정 loop는 활성화하지 않았다.** 실제 integration 응답/동일 PR push는 E2E 기록으로만 판정한다. 공식 문서에 없는 API나 멘션봇을 가정하지 않는다. 사람이 이 JSON과 job 로그를 Codex에 전달하면 같은 PR branch에서 수정하도록 요청할 수 있다.

## 자동 수정 연결 전 필수 조건

1. 신뢰하는 default-branch controller 또는 별도 GitHub App에서 PR별 영속 iteration ledger를 관리한다. 키는 repo+PR, SHA별 새 예산을 주지 않는다.
2. `repair_gate.decide`로 최대 3회 제한을 검사하고 실행 **전에** 원자적으로 reservation한다. 중복 run/event를 idempotency key로 차단한다. counter 미확인/손상은 BLOCKED다.
3. latest PR HEAD, 발신자 권한, fork 여부, 허용 경로, protected changes를 신뢰하는 base 코드로 재검증한다. PR에서 만든 JSON을 권한 있는 명령으로 바로 실행하지 않는다.
4. HUMAN_REVIEW_REQUIRED 영역과 3회 이후 FAIL은 호출하지 않는다. PASS도 READY_FOR_HUMAN_REVIEW까지만 간다.
5. PR 코드 실행과 secret/write credential 단계를 분리한다. 승인된 좁은 patch만 동일 PR branch에 반영하는 설계를 별도 human review한다. main은 대상에서 제외한다.
6. 현재 GitHub 문서상 `GITHUB_TOKEN`으로 PR을 생성/업데이트하면 opened/synchronize/reopened workflow가 **승인 대기 상태**로 생성될 수 있다. 일반 push-trigger workflow 재귀는 억제된다. 따라서 무인 synchronize 실행을 가정하지 않는다. 승인 없는 연쇄가 필요하면 별도 최소 권한 GitHub App installation token 등 공식 지원 인증을 선택하고 실제 event/승인 상태를 검증한다. [GitHub token 문서](https://docs.github.com/en/actions/concepts/security/github_token).

현재 순수 gate 테스트는 한 process 안의 정책을 검증한다. 영속/동시성 보장이나 실제 Codex task 성공을 증명하지 않는다. 연결 전에는 `automatic_dispatch=false`, `iteration=null`이다.

## Repository 설정 / 보안

확인 시점: public repo, Actions enabled, main branch protection 미설정, repository secrets 없음. 이 작업은 security policy를 임의 변경하지 않는다.

사용자가 Human Gate에서 설정할 것:

- main ruleset: PR 필수, 사람 approval 필수, 최신 commit 승인/required checks(`desktop-static`, `macos-native`, `review-result`), force push/삭제 차단, direct push 제한. 조직/계정 플랜과 실제 ruleset 적용 여부 확인.
- Actions의 읽기 전용 기본 token 및 외부 fork 승인 정책 확인. auto-merge는 사용하지 않는다.
- Codex cloud GitHub 연결에서 이 repository만 허용하고 environment/review 설정 확인. 구체적인 App 권한은 설치 화면에서 검토하며 광범위한 계정 권한을 추측해 부여하지 않는다.
- Action executor를 선택할 때만 `OPENAI_API_KEY`를 승인된 secret/environment에 저장한다. 현재 검증 workflow에 필요한 사용자 secret은 **없음**이다.

모든 job은 `contents: read`, checkout은 `persist-credentials: false`, Actions는 commit SHA 고정이다. `pull_request_target`, privileged `workflow_run`, comment shell interpolation, write token, 자동 comment/push/merge가 없다. fork PR도 검증 코드에는 secrets를 주지 않는다. dependency install 자체는 PR 코드 실행이므로 읽기 전용 일회성 runner에서만 수행한다. 규칙/CI 파일도 PR에서 수정 가능하므로 AGENTS와 path detector는 보안 강제 장벽이 아니다. branch protection과 사람 review가 필요하다.

## 실제 E2E 절차

foundation에서 별도 `test/foundation-validation` branch를 만들고 foundation 대상 draft PR을 연다. `tests/automation/fixture.json`의 기대값 3을 임시로 4로 바꿔 contract test가 FAIL하도록 한다. 게임/native 코드를 손대지 않는다.

1. opened → workflow run과 실패 job/JSON 확인.
2. 해당 test PR에 `@codex`로 이 fixture만 복구하도록 한 번 요청한다. task 생성/commit/push의 실제 응답을 기록한다. integration 미연결이면 BLOCKED로 기록하고 자동 재호출하지 않는다.
3. 이 로컬 Codex가 수동으로 복구한 경우 remote integration 성공과 구별한다.
4. 새 commit push → synchronize → 검증 재실행 → 자동 검사 PASS와 human 상태 확인.
5. test PR은 merge하지 않는다. 실제 run/comment/commit URL, 수행 주체, 미검증 단계를 `docs/automation-validation.md`에 기록한다.

CI 완료 여부를 이번 작업 중 조회하는 것은 결과 관측이며 운영용 polling automation이 아니다.
