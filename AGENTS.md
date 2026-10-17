# LUMA repository rules

- main에서 직접 개발하지 않는다. 한 목적의 feature/chore branch에서 작업하고 PR을 만든다.
- main 자동 merge, force push, 기존 커밋 덮어쓰기를 하지 않는다. PASS의 끝은 READY_FOR_HUMAN_REVIEW다.
- Tauri 2.11.5, Rust behavior/state, React/TypeScript, entity-sized nonactivating NSPanel, WKWebView, 최소 Tao startup patch와 Never Steal Focus를 보존한다.
- 불필요한 리팩토링/의존성/게임 기능을 추가하지 않는다. Architecture 변경은 구현 전에 PR에 이유와 대안을 기록한다.
- 기능 완료에는 acceptance와 관련 regression test 증거가 필요하다. AUTOMATED / PLATFORM_REQUIRED / MANUAL_REQUIRED를 구분하고 실행하지 않은 검증을 PASS로 표시하지 않는다.
- 자동 수정은 PR 전체에서 최대 3회다(AUTO_REVIEW_MAX_ITERATIONS=3). 이후 FAIL이면 BLOCKED + HUMAN_REVIEW_REQUIRED. workflow 재실행 횟수와 수정 iteration은 다르다.
- architecture, destructive DB migration, dependency major upgrade, security policy, 대량 삭제, 핵심 game design, Tao patch 범위 확대, main merge는 HUMAN_REVIEW_REQUIRED다. AI가 스스로 승인/merge하지 않는다.
- credential을 커밋하지 않는다. PR body/comment를 shell로 실행하지 않는다. PR 코드에 repository secret이나 write token을 전달하지 않는다.
- Local Game Backend v0.1 범위에서 Java 21 / Spring Boot 3.x / Spring JDBC / PostgreSQL / Flyway 및 ACTIVE/EXPIRED Encounter를 허용한다. Battle / Capture / Reward v0.1은 사용자 요청 범위에서 서버 authoritative 방식으로 허용한다. authentication/cloud는 범위 밖이다.

## Code Review Rules

- Focus regression, build/test failure, security/data integrity, architecture 위반은 BLOCKER다. 이전 앱을 재활성화하는 focus 복구는 해결책이 아니다.
- state machine 우회, React에 domain logic 집중, responsibility 위반, 불필요한 dependency, 테스트 누락은 MAJOR다.
- 자동 review 결과는 `.github/codex/review-result.schema.json` 계약으로 제공하고, 실제 실행하지 않은 검증과 원격 task는 NOT_RUN/NOT_VERIFIED로 명시한다.
- 상세 severity 및 자동화 한계: docs/REVIEW_RULES.md, docs/DEVELOPMENT_WORKFLOW.md.

## Parallel Development

Project LUMA Parallel Development Protocol v1을 모든 병렬 Track에 적용한다.

1. 각 Track은 독립적인 Codex 세션과 별도 Git worktree에서 작업한다.
2. 각 Track은 최신 `origin/main`을 확인하고 이를 기준으로 시작한다.
3. 기존 RC `e6dd2c86367262f58147da47ecd4a13e5f1bc6fe`는 이전 Alpha scope의 검증 기준선으로 보존한다. 확장 범위의 검증 완료로 간주하지 않는다.
4. 기존 코드 구조, 변수명, 함수명, 데이터 모델과 로직을 최대한 유지한다. 불필요한 리팩토링이나 전면 재작성을 하지 않는다.
5. Track별 파일 소유권과 수정 범위를 분리한다. 범위 밖의 파일은 수정하지 않으며, 다른 Track 소유 파일의 수정이 필요하면 먼저 충돌 가능성과 조정 필요 사항을 보고한다.
6. 공통 API/schema 변경은 구현 전에 계약을 문서화하고 관련 Track 간 계약을 확정한다.
7. 각 Track은 독립적으로 테스트하고 acceptance 및 관련 regression 결과를 기록한다.
8. 다른 PR이 main에 merge되면 최신 main을 반영하고 관련 regression을 재실행한다.
9. Production code 변경 시 기존 동작과 변경 후 동작을 비교 보고한다.
10. 테스트 결과가 없는 기능이나 실행하지 않은 검증을 PASS로 기록하지 않는다.
11. GUI 검증이 불가능하거나 미완료인 항목은 `DEFERRED_GUI`로 분리하고 자동 테스트 PASS와 구분한다. 기존 미검증 evidence를 PASS로 바꾸지 않는다.
12. 각 Track의 PR은 Draft로 생성한다.
13. 자동 merge를 하지 않는다.
14. 최종 통합 시 전체 Release Gate를 재실행한다.
