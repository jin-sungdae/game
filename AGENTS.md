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
