-- Additive dormant economy. V11 belongs to command receipts, V12/V13 to PR #71/#72.
-- Deploy V12/V13 before V14; never enable outOfOrder to bypass release ordering.
-- No seed rewards, updates, backfill, encounter budget or reservation duplication.
CREATE TABLE game.t_reward_entitlement (
    entitlement_id uuid PRIMARY KEY,
    player_id bigint NOT NULL REFERENCES game.t_player(player_id),
    reward_type varchar(32) NOT NULL CHECK (reward_type IN ('WEEKLY','COLLECTION_DISCOVERY','COLLECTION_CAPTURE')),
    week_start date,
    reward_slot varchar(64),
    campaign_id varchar(80),
    milestone bigint,
    policy_version varchar(64) NOT NULL CHECK (policy_version ~ '^[A-Z0-9][A-Z0-9_.-]*$'),
    gold bigint NOT NULL CHECK (gold >= 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (entitlement_id, player_id),
    CHECK (
        (reward_type='WEEKLY' AND week_start IS NOT NULL AND reward_slot IS NOT NULL
         AND reward_slot ~ '^[A-Z0-9][A-Z0-9_.-]*$' AND campaign_id IS NULL AND milestone IS NULL)
        OR
        (reward_type IN ('COLLECTION_DISCOVERY','COLLECTION_CAPTURE') AND campaign_id IS NOT NULL
         AND campaign_id ~ '^[A-Z0-9][A-Z0-9_.-]*$' AND milestone IS NOT NULL AND milestone > 0
         AND week_start IS NULL AND reward_slot IS NULL)
    )
);
CREATE UNIQUE INDEX uk_reward_weekly
    ON game.t_reward_entitlement(player_id, week_start, reward_slot) WHERE reward_type='WEEKLY';
CREATE UNIQUE INDEX uk_reward_collection
    ON game.t_reward_entitlement(player_id, campaign_id, reward_type, milestone) WHERE reward_type<>'WEEKLY';

CREATE TABLE game.t_reward_entitlement_item (
    entitlement_id uuid NOT NULL REFERENCES game.t_reward_entitlement(entitlement_id),
    item_id bigint NOT NULL REFERENCES game.m_item(item_id),
    quantity integer NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (entitlement_id, item_id)
);
CREATE TABLE game.t_economy_reward_ledger (
    entitlement_id uuid PRIMARY KEY,
    player_id bigint NOT NULL,
    command_id uuid NOT NULL,
    granted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (entitlement_id, player_id) REFERENCES game.t_reward_entitlement(entitlement_id, player_id),
    UNIQUE (player_id, command_id)
);
CREATE INDEX ix_economy_ledger_player_time ON game.t_economy_reward_ledger(player_id, granted_at);

-- Runtime history is append-only. No cascade deletion, expiry or rewrite pathway.
CREATE FUNCTION game.reject_economy_history_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Economy history is immutable' USING ERRCODE='23514';
END;
$$;
CREATE TRIGGER immutable_reward_entitlement BEFORE UPDATE OR DELETE ON game.t_reward_entitlement
FOR EACH ROW EXECUTE FUNCTION game.reject_economy_history_mutation();
CREATE TRIGGER immutable_reward_entitlement_item BEFORE UPDATE OR DELETE ON game.t_reward_entitlement_item
FOR EACH ROW EXECUTE FUNCTION game.reject_economy_history_mutation();
CREATE TRIGGER immutable_economy_reward_ledger BEFORE UPDATE OR DELETE ON game.t_economy_reward_ledger
FOR EACH ROW EXECUTE FUNCTION game.reject_economy_history_mutation();
