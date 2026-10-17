-- V11 (Command Receipt) and V12 (Collection Encounter) are allocated to other tracks.
ALTER TABLE game.t_battle ADD COLUMN rules_version varchar(32);
UPDATE game.t_battle SET rules_version='ALPHA_V1';
ALTER TABLE game.t_battle ALTER COLUMN rules_version SET DEFAULT 'ALPHA_V1';
ALTER TABLE game.t_battle ALTER COLUMN rules_version SET NOT NULL;
ALTER TABLE game.t_battle ADD CONSTRAINT ck_battle_rules_version
    CHECK (length(btrim(rules_version)) > 0);

-- Supported-version validation belongs to the reader; unknown future versions
-- must remain readable as data and must never be silently executed as Alpha.
CREATE FUNCTION game.preserve_battle_rules_version() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.rules_version IS DISTINCT FROM OLD.rules_version THEN
        RAISE EXCEPTION 'Battle rules version is immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER battle_rules_version_immutable
    BEFORE UPDATE OF rules_version ON game.t_battle
    FOR EACH ROW EXECUTE FUNCTION game.preserve_battle_rules_version();
