# LUMA Architecture

## 현재 Desktop — 검증된 Spike 01.1

Tauri **2.11.5** / Rust / React + TypeScript / Vite를 사용한다. Rust가 현재 entity state machine과 behavior/timing을 소유하고 React는 표현과 입력 전달을 담당한다. entity-sized native nonactivating NSPanel에 WKWebView를 연결한다. startup focus는 LSUIElement, event-loop 이전 Accessory policy, Tao 0.35.3의 최소 opt-in patch로 보호한다.

사용자가 실제 macOS의 launch/MOA interaction에서 기존 keyboard focus 유지를 확인하여 **Spike 01.1 최종 GO**로 확정했다. [측정과 사용자 확인](validation.md), [native integration 상세](SPIKE_ARCHITECTURE.md), [Tao patch 정확한 범위/upgrade 체크리스트](tao-patch.md)를 따른다. 이번 foundation은 이 구현을 변경하지 않는다.

## 향후 Local Backend — 미구현

| 경계 | 책임 |
|---|---|
| Client: Tauri/Rust/React | 표현, animation, position, desktop interaction |
| Server: Spring Boot | 게임 판정 |
| Database: PostgreSQL | persistent game state |

**Client presents. Server decides. Database remembers.**

향후 도메인 판정은 server로 분리하되 현재 Spike의 Rust behavior/state는 desktop UX 검증용이다. 이번 작업에서 server/DB를 추가하거나 기존 Rust state를 이동시키지 않는다. API, 배포, 데이터 스키마, 실제 Battle/Capture 규칙은 별도 설계 대상이다.

architecture 변경이 필요하면 먼저 PR에 문제·이유·대안·영향·검증 계획을 기록한다. HUMAN_REVIEW_REQUIRED로 두고 AI가 임의 승인/merge하지 않는다. 검증되지 않은 기능을 현재 architecture로 묘사하지 않는다.
