-- Additive, dormant foundation. V11 is reserved by command infrastructure PR #68.
-- Deploy V11 before V12; do not enable Flyway out-of-order to work around merge order.
-- Existing Alpha paths never write these tables.
CREATE TABLE game.t_observation_receipt (
    encounter_id uuid PRIMARY KEY REFERENCES game.t_encounter(encounter_id),
    player_id bigint NOT NULL REFERENCES game.t_player(player_id),
    reason varchar(16) NOT NULL CHECK (reason IN ('VICTORY','CAPTURED')),
    points integer NOT NULL DEFAULT 1 CHECK (points = 1),
    granted_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX ix_observation_player ON game.t_observation_receipt(player_id);
CREATE TABLE game.t_collection_issuance_budget (
    player_id bigint PRIMARY KEY REFERENCES game.t_player(player_id),
    next_available_at timestamptz NOT NULL
);
-- HELD reserves balance immediately; CONSUMED spends that same hold, never a second debit.
-- Cancellation releases the hold. No expiry or automatic refund policy in v1.
CREATE TABLE game.t_collection_reservation (
    reservation_id uuid PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES game.t_player(player_id),
    target_monster_id bigint NOT NULL REFERENCES game.m_monster(monster_id),
    observation_cost integer NOT NULL CHECK (observation_cost > 0),
    status varchar(16) NOT NULL,
    consumption_state varchar(16) NOT NULL,
    encounter_id uuid UNIQUE REFERENCES game.t_encounter(encounter_id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    consumed_at timestamptz,
    CHECK (
      (status='PENDING' AND consumption_state='HELD' AND encounter_id IS NULL AND consumed_at IS NULL)
      OR (status='CANCELLED' AND consumption_state='RELEASED' AND encounter_id IS NULL AND consumed_at IS NULL)
      OR (status='ISSUED' AND consumption_state='CONSUMED' AND encounter_id IS NOT NULL AND consumed_at IS NOT NULL)
    )
);
CREATE UNIQUE INDEX uk_collection_pending_reservation
 ON game.t_collection_reservation(player_id) WHERE status='PENDING';
