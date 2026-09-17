# Review Rules

| Severity | 기준 |
|---|---|
| BLOCKER | build/test 실패, Never Steal Focus regression, security 문제, 데이터 손상 가능성, architecture 원칙 위반 |
| MAJOR | 잘못된 domain responsibility, state machine 우회, React component에 game logic 집중, 불필요한 dependency, 테스트 누락 |
| MINOR | naming, documentation, 작은 구조 개선 |
| PASS | 해당 acceptance 충족, 검사 범위 내 regression 없음 |

PASS는 merge 권한이 아니다. 필수 수동/플랫폼 검증이 남으면 이를 별도로 표시하고 Human Gate가 판단한다. CI의 PASS는 자동 검사 범위만 뜻하며 semantic/security review 전체 통과를 의미하지 않는다.

Architecture 변경, destructive DB migration, dependency major upgrade, security policy 변경, 대량 파일 삭제, 핵심 game design 변경, Tao patch 범위 확대, main merge는 **HUMAN_REVIEW_REQUIRED**다. 경로 검출은 보수적인 안내이며 의미 기반 review를 대체하지 않는다. dependency 파일 변경은 major 여부가 불명확해도 사람에게 보낸다. 삭제 20개 이상을 대량 삭제의 최소 경보 기준으로 삼되 작은 파괴적 삭제도 review 대상이다.

## Machine-readable contract

`LUMA_REVIEW_RESULT` JSON은 `.github/codex/review-result.schema.json`을 따른다. head_sha/base_sha, PR 번호, workflow run ID에 묶인 증거만 소비한다. 오래된 commit의 PASS를 새 HEAD에 적용하지 않는다.

- `status`: PASS / FAIL / BLOCKED
- `iteration`: 실제 자동 수정 횟수. initial=0, 최대 3. GitHub run_attempt/run_number가 아니다.
- `findings`: severity/message 목록; `required_actions`: 수정 요구
- `checks`: AUTOMATED / PLATFORM_REQUIRED / MANUAL_REQUIRED와 실제 status
- `next_action`: FIX_REQUIRED / READY_FOR_HUMAN_REVIEW / HUMAN_REVIEW_REQUIRED
- `automatic_dispatch`: 현재 false. JSON은 실행 명령이 아니라 데이터다.

새 PR push는 검증만 재실행한다. 실제 executor가 없으므로 CI의 iteration은 null(자동 수정 ledger 미연결)이며 임의로 0으로 초기화해 재시도 예산을 늘리지 않는다. `repair_gate.py`는 연결할 trusted coordinator의 최대 3회 gate를 검증하는 순수 함수다. 같은 PR의 영속 ledger, 원자적 reservation, 중복 event 제거, 최신 HEAD 확인 없이 executor를 켜지 않는다. 3회 수정 후 FAIL은 BLOCKED + HUMAN_REVIEW_REQUIRED다. 사람도 자동으로 예산을 reset하는 이벤트를 만들지 않는다.
