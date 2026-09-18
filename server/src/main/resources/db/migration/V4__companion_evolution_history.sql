CREATE TABLE game.t_companion_evolution_history (
    evolution_history_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_companion_id bigint NOT NULL REFERENCES game.t_player_companion(player_companion_id),
    species_id bigint NOT NULL REFERENCES game.m_species(species_id),
    from_stage integer NOT NULL CHECK (from_stage BETWEEN 1 AND 4),
    to_stage integer NOT NULL CHECK (to_stage = from_stage + 1),
    level_at_evolution integer NOT NULL CHECK (level_at_evolution >= 1),
    bond_at_evolution integer NOT NULL CHECK (bond_at_evolution >= 0),
    evolved_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (species_id, from_stage) REFERENCES game.m_species_evolution(species_id, evolution_stage),
    FOREIGN KEY (species_id, to_stage) REFERENCES game.m_species_evolution(species_id, evolution_stage),
    UNIQUE (player_companion_id, from_stage, to_stage)
);
CREATE INDEX idx_evolution_history_species_from ON game.t_companion_evolution_history(species_id, from_stage);
CREATE INDEX idx_evolution_history_species_to ON game.t_companion_evolution_history(species_id, to_stage);
