ALTER TABLE game.t_encounter DROP CONSTRAINT t_encounter_status_check;
ALTER TABLE game.t_encounter ADD CONSTRAINT ck_encounter_status CHECK (status IN ('ACTIVE','DEFEATED','CAPTURED','ESCAPED','EXPIRED','PLAYER_DEFEATED'));
CREATE TABLE game.t_battle (
 battle_id uuid CONSTRAINT pk_battle PRIMARY KEY,
 encounter_id uuid NOT NULL CONSTRAINT uk_battle_encounter UNIQUE CONSTRAINT fk_battle_encounter REFERENCES game.t_encounter,
 player_companion_id bigint NOT NULL CONSTRAINT fk_battle_companion REFERENCES game.t_player_companion,
 monster_id bigint NOT NULL CONSTRAINT fk_battle_monster REFERENCES game.m_monster,
 companion_hp integer NOT NULL, companion_max_hp integer NOT NULL CHECK(companion_max_hp>0),
 monster_hp integer NOT NULL, monster_max_hp integer NOT NULL CHECK(monster_max_hp>0),
 companion_attack integer NOT NULL CHECK(companion_attack>0), monster_attack integer NOT NULL CHECK(monster_attack>0),
 turn_no integer NOT NULL DEFAULT 0 CHECK(turn_no>=0),
 status varchar(24) NOT NULL CHECK(status IN ('ACTIVE','VICTORY','DEFEAT','CAPTURED','ESCAPED')),
 started_at timestamptz NOT NULL DEFAULT now(), ended_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT ck_battle_hp CHECK(companion_hp BETWEEN 0 AND companion_max_hp AND monster_hp BETWEEN 0 AND monster_max_hp),
 CONSTRAINT ck_battle_end CHECK((status='ACTIVE' AND ended_at IS NULL) OR (status<>'ACTIVE' AND ended_at IS NOT NULL)),
 CONSTRAINT ck_battle_outcome CHECK((status<>'VICTORY' OR monster_hp=0) AND (status<>'DEFEAT' OR companion_hp=0))
);
CREATE INDEX ix_battle_companion ON game.t_battle(player_companion_id);
CREATE INDEX ix_battle_monster ON game.t_battle(monster_id);
CREATE TABLE game.t_reward (
 reward_id uuid CONSTRAINT pk_reward PRIMARY KEY,
 encounter_id uuid NOT NULL CONSTRAINT uk_reward_encounter UNIQUE CONSTRAINT fk_reward_encounter REFERENCES game.t_encounter,
 player_id bigint NOT NULL CONSTRAINT fk_reward_player REFERENCES game.t_player,
 gold_reward bigint NOT NULL CHECK(gold_reward>=0), exp_reward bigint NOT NULL CHECK(exp_reward>=0),
 bond_reward integer NOT NULL CHECK(bond_reward>=0), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_reward_player ON game.t_reward(player_id);
CREATE TABLE game.t_collection (
 collection_id bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_collection PRIMARY KEY,
 player_id bigint NOT NULL CONSTRAINT fk_collection_player REFERENCES game.t_player,
 monster_id bigint NOT NULL CONSTRAINT fk_collection_monster REFERENCES game.m_monster,
 first_captured_at timestamptz NOT NULL, last_captured_at timestamptz NOT NULL,
 capture_count bigint NOT NULL CHECK(capture_count>0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT uk_collection_player_monster UNIQUE(player_id,monster_id),
 CONSTRAINT ck_collection_time CHECK(last_captured_at>=first_captured_at)
);
CREATE INDEX ix_collection_monster ON game.t_collection(monster_id);
