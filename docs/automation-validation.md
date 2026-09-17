# Foundation automation validation

2026-09-17. 기존 Spike는 사용자 확인으로 GO이며, 아래는 별개의 automation 검증이다.

## 실제 실행과 증거

- Foundation PR: https://github.com/jin-sungdae/game/pull/2 (base: spike/focus-startup-fix).
- 격리된 test PR: https://github.com/jin-sungdae/game/pull/3 (base: chore/development-foundation, merge 금지).
- `opened` 이벤트: VERIFIED. 초기 실패 run https://github.com/jin-sungdae/game/actions/runs/35181659767.
- 의도적 실패: VERIFIED. commit `cc0f47c`의 fixture 4가 기대값 3과 달라 `test_ci_fixture`가 실패했다. macOS job은 비용을 쓰지 않고 skipped. 집계는 skipped를 성공으로 바꾸지 않았다.
- FAIL machine result: VERIFIED. [원본 JSON](evidence/foundation/intentional-failure.json), status=FAIL, next_action=FIX_REQUIRED, automatic_dispatch=false, iteration=null.
- 공식 `@codex` 요청 게시: VERIFIED. https://github.com/jin-sungdae/game/pull/3#issuecomment-5708480732. 단 한 번, fixture 파일 하나/커밋 하나로 제한했다.
- 원격 Codex task 생성 및 같은 PR commit/push: 아직 NOT_VERIFIED. 멘션 게시 자체는 task 실행 성공이 아니다.

- 초기 foundation 전체 CI: VERIFIED PASS. https://github.com/jin-sungdae/game/actions/runs/35181638072, head `28b149f`. [원본 JSON](evidence/foundation/initial-foundation-pass.json). 새 workflow/규칙 변경을 감지해 `HUMAN_REVIEW_REQUIRED`로 남겼다.
- 로컬 Codex fixture 수정/commit/push: VERIFIED. `4102cab`은 이 로컬 작업에서 만든 커밋이며 원격 integration 결과가 아니다.
- 수정 push 이후 새 workflow: VERIFIED. https://github.com/jin-sungdae/game/actions/runs/35181877413. 자동화에 polling trigger를 추가하지 않았다.

- 재검증 완료: **VERIFIED PASS / READY_FOR_HUMAN_REVIEW**. [원본 JSON](evidence/foundation/repaired-test-pass.json). Linux build/policy, macOS Rust 6/6・fmt・clippy・AppKit compile, 결과 집계 모두 통과했다. 실제 desktop focus는 NOT_RUN으로 유지됐다.
- main merge: 수행하지 않음. foundation/test PR 모두 merge하지 않았다.

## 단계별 최종 판정

| 단계 | 결과 |
|---|---|
| PR 생성 → opened → validation | VERIFIED |
| 의도적 failure → FAIL JSON | VERIFIED |
| 공식 @codex 수정 요청 게시 | VERIFIED |
| 원격 task 생성 / 자동 commit / 자동 push | NOT_VERIFIED: 관측 기간 내 bot 응답·reaction·task 링크·원격 커밋 없음. 설치 불가능이라는 단정은 하지 않음 |
| 로컬 Codex 수정 → 새 commit/push | VERIFIED, 사용자 인증 gh/git 경로, 자동 cloud executor와 다름 |
| synchronize → 재검증 → PASS | VERIFIED |
| READY_FOR_HUMAN_REVIEW → 정지 | VERIFIED, merge 없음 |
| 최대 3회 / 초과 BLOCKED 정책 | 단위 테스트 VERIFIED. 영속 distributed loop enforcement는 executor 미연결로 NOT_VERIFIED |

최종 제공 상태는 **개발 기반/PR 검증 사용 가능, 원격 무인 수정 연결은 미검증·비활성**이다. 다음 단계는 사용자의 main Human Gate/보호 설정, Codex repository 연결 확인, trusted iteration ledger와 credential 격리 설계 승인 후 실제 remote task→push 검증이다. 이 prerequisite를 우회하려고 secret을 PR job에 노출하지 않는다.

## 보장하지 않는 사항

완전 무인 auto-repair loop, persistent iteration ledger/동시성, App token push의 event chain, remote Codex 인증/비용, 실제 macOS focus runtime는 이번 CI에서 검증됐다고 주장하지 않는다. 공식 Action 기반 실행은 secret 및 trusted controller 설계가 준비될 때까지 미설치다.

PR validation artifact는 PR 코드가 만든 비신뢰 데이터다. 이를 privileged 자동화에 바로 연결하지 않는다. 자동화 정책/경로 gate는 review 보조이며 GitHub ruleset을 대체하지 않는다. main branch protection은 사용자가 별도로 설정해야 한다.
