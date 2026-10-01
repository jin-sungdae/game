# Alpha Pilot Production FLYING Profile v1

PR #52의 supplied CHIRP artwork와 velocity-owned resolver는 사용자 승인된 Alpha Pilot Production 계약이다.

| CHIRP sequence | 상태 | Alpha default |
| --- | --- | --- |
| HOVER | PRODUCTION | 4 frames, 1600ms cycle |
| FLY | PRODUCTION | 6 frames, 90ms/frame, 540ms at 1× |
| GLIDE | NOT_APPLICABLE | supplied asset의 deterministic coverage만 유지 |

## 재사용 가능한 movement profile 계약

Native MovementController가 world x/y, velocity, trajectory와 facing을 계속 소유한다. Animation은 accepted native displacement에서 측정된 vx/vy와 speed magnitude를 읽는 presentation이다. 수직 이동도 speed magnitude에 포함하며 horizontal facing은 기존 native 정책을 따른다.

기존 movement hysteresis를 재사용한다. HOVER에서 speed >=8pt/s이면 FLY에 진입하고, FLY는 speed >=3pt/s일 때 유지한다. 그 아래는 HOVER다. 정지/저속에서 HOVER를 사용하며 경계 속도로 인한 state chatter를 피한다.

FLY playback은 기존 rate = clamp(speed / 40, 0.5, 2)를 유지한다. 실제 ambient speed에서 약 0.5×, 1080ms cycle은 승인된 정상 behavior다. HOVER는 1600ms cycle이다. 이 값들은 Alpha approved default이며 향후 visual polish에서 조정할 수 있다.

현재 native Flying에는 신뢰 가능한 glide-specific signal이 없다. GLIDE PNG가 존재해도 timer, 가상의 movement state 또는 production trigger를 만들지 않는다.

향후 FLYING Monster는 동일 resolver/ownership 계약을 재사용할 수 있다. Monster별 artwork와 registry entry는 별도이며 CHIRP의 identity, geometry 또는 gameplay를 다른 Monster에 복사하지 않는다. 새 engine/RAF/timer/polling은 추가하지 않는다.

## 보존되는 경계

- Shared Clock, generated static registry와 production CSP는 그대로 유지한다. Runtime manifest fetch는 없다.
- Spawn/rarity, ENGAGED/Battle/Capture/Despawn 등 기존 priority가 animation보다 우선한다.
- Reduced Motion은 기존 frame-minimization 정책을 따르며 movement trajectory는 바꾸지 않는다.
- Missing/invalid animation은 해당 Monster own base로 fallback한다.

## 승인 및 evidence

기존 [실제 production evidence](evidence/chirp-flying-v1/)는 삭제하거나 승인 이후 결과로 덮어쓰지 않는다. 당시 candidate/manual-review 표기는 historical record다. 사용자 승인은 현재 문서와 FLYING_PRODUCTION registry 상태에 기록한다.

Wing flap strength, hover naturalness, flying/sliding impression은 향후 visual polish 대상이며 현재 Alpha blocker가 아니다. Alpha=1/255 bottom resampling fringe는 visible clipping이 아닌 Known Visual Caveat로 유지한다.
