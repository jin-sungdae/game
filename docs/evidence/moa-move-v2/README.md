# MOA MOVE v2 anatomy-guided delivery

Replaces only the supplied MOVE bytes in the existing `walk/walk_00..07.png` slots. Original `move_01..08.png` names and hashes remain in `source-manifest.json`; `asset-validation.json` proves ZIP-byte equality and recomputed zero center/bottom drift. Frames01/05 intentionally share bytes; seven unique decoded frames exist. The alpha planes are not all identical to base, but their registration bounds meet the delivered contract; this is not an alpha-equality approval.

Base/Breath/Blink, AnimationStateResolver, static registry, shared clock, MovementController, velocity-linked rate and CSP are unchanged. Existing80ms/frame,640ms/1× cycle remains a **candidate**, not production visual approval. IDLE stays1800ms Breath,90ms Blink,3–7s randomized Blink.

`pixel-variation.json` measures adjacent frame pairs including08→01 in the prior anatomy bounding-box ROIs. These are explicit pixel measurement regions, not authoritative semantic masks. V1 front/rear paw RGB variation was zero; V2 front paw changed-pixel counts are262,168,168,262,19,16,16,19; rear paw0,0,0,0,260,162,162,260; body interior301,301,357,357,301,301,357,357. Planted rear-paw phases correctly have zero difference; phase variation is not the same as judged gait quality.

Production GUI comparison is in progress with the same existing World seed165945 as V1. Until analyzed, V2 actual playback/continuity/clipping/facing acceptance is NOT_VERIFIED. V1 evidence and recordings are retained. No runtime or timing changes are made to improve visual results.
