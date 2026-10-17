-- Switching owns the durable revision; existing saves start at zero.
ALTER TABLE game.t_player ADD COLUMN active_selection_revision bigint NOT NULL DEFAULT 0
    CHECK (active_selection_revision >= 0);
