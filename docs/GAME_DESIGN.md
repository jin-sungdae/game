# LUMA Game Design

확정 개념의 공통 어휘다. 아래 게임 시스템은 설계 방향이며 구현 완료를 의미하지 않는다. 수치/규칙이 제공되지 않은 항목은 추후 Human Gate에서 결정한다.

| 개념 | 방향 / 현재 범위 |
|---|---|
| Ambient Desktop Creature RPG | 다른 desktop 작업과 공존하는 creature RPG |
| Companion | 사용자의 desktop 동반자. MOA / RUU / NOX가 핵심 companion 개념이며 현재 MOA 임시 entity만 존재 |
| 5 Stage Evolution | 5단계 성장. 단계명/진화 조건은 미정 |
| Level 1–100 | 성장 레벨 범위. 경험치 곡선은 미정 |
| Personality | 개체 행동/반응의 성격. 세부 규칙 미정 |
| Bond | 사용자와 companion의 유대. 증가/감소 규칙 미정 |
| Monster / Encounter | desktop에 등장하는 만남 대상과 조우. PIP은 spike용 임시 대상 |
| Battle / Capture | 전투 판정과 포획. 현재 버튼은 debug log만 출력 |
| Collection | 획득 개체 수집. 저장/중복 정책 미정 |
| Item / Economy | 아이템과 자원 경제. 상품/가격/결제 모델 미정 |
| Focus Mode | 작업 집중에 맞춘 방해 최소화 모드. 세부 동작 미정 |
| Never Steal Focus | launch, 이동, animation, interaction 때문에 기존 작업 앱의 keyboard focus를 가져오지 않는다 |

현재 검증된 것은 overlay/interaction 기술이다. RUU/NOX, evolution, level, personality, bond, battle/capture, collection, item/economy를 이번 foundation 작업에서 구현하지 않는다. 핵심 design 변경은 HUMAN_REVIEW_REQUIRED다.
