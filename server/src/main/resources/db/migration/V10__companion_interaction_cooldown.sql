-- Independent of battle/item/evolution updated_at. Existing Bond and stages are untouched.
ALTER TABLE game.t_player_companion ADD COLUMN last_bond_interaction_at timestamptz;
