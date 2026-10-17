CREATE TABLE game.t_battle_skill_state (
 battle_id uuid PRIMARY KEY REFERENCES game.t_battle(battle_id) ON DELETE CASCADE,
 schema_version integer NOT NULL DEFAULT 1 CHECK(schema_version=1),
 state jsonb NOT NULL CHECK(jsonb_typeof(state)='object')
);
