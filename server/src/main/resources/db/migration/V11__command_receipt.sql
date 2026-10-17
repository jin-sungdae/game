CREATE TABLE game.t_command_receipt (
    player_id bigint NOT NULL REFERENCES game.t_player(player_id),
    command_id uuid NOT NULL,
    command_type varchar(64) NOT NULL CHECK (command_type ~ '^[A-Z][A-Z0-9_]{0,63}$'),
    target_id varchar(200) NOT NULL CHECK (length(btrim(target_id)) > 0),
    request_fingerprint varchar(64) NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
    response_status integer NOT NULL CHECK (response_status BETWEEN 200 AND 599),
    -- text preserves the original JSON representation for exact replay.
    response_body text NOT NULL CHECK (response_body IS JSON),
    response_schema_version integer NOT NULL CHECK (response_schema_version > 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (player_id, command_id)
);
