# Battle / Capture / Reward v0.1 — implementation design

Server JDBC domain extends existing backend; Desktop remains presentation only. Existing native panels, behavior, movement, animation, assets, single instance and Tao remain unchanged.

Lock order: local player -> encounter -> battle (SELECT FOR UPDATE). This preserves the existing per-player encounter serialization and adds explicit battle locking. Concurrent attacks are distinct serialized turns; without a request token, identical network requests cannot be deduplicated. No automatic mutation retries on Desktop. Terminal requests never pay again.

V3 additive migration introduces battle/reward/collection plus PLAYER_DEFEATED encounter status. Battle CAPTURED/ESCAPED distinguish non-combat resolution from VICTORY/DEFEAT. No rewrite of V1/V2. Capture active success pays no victory reward. Defeat maps to PLAYER_DEFEATED. Ignore maps to ESCAPED. Battle ACTIVE suspends spawn expiration. VICTORY resets expires_at to a 60-second capture opportunity; timeout or failed post-victory capture resolves DEFEATED, no counterattack. Post-victory capture is one attempt; active failures consume a turn/counterattack. No arbitrary battle timeout in v0.1; explicit Ignore resolves abandoned active battles.

Alternative considered: marking encounter DEFEATED immediately on victory prevents capture and violates requested loop. Keeping ordinary spawn TTL in active battle would despawn PIP mid-turn. We instead expose expirationSuspended + battleId in encounter presentation, preserving non-null timestamps for old contracts.

Formulas stay in CombatRules. Reward insert and gold/EXP/bond/level updates share the victory transaction; UNIQUE(encounter_id) prevents repeat reward. Collection UPSERT shares capture resolution transaction. Level is derived from total EXP [0,100,300,600,1000], capped at 5, never evolves species.

Validation pending. Existing PR10 automated UI activation attribution remains MANUAL_REQUIRED; no new focus acceptance claim.
