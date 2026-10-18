-- V16/V17/V18 belong to growth/evolution/selection; require those migrations first.
-- Existing pre-battle encounters were issued under ALPHA_V1. Existing battle versions win.
-- No historical companion level is invented: legacy spawn_tier remains NULL.
ALTER TABLE game.t_encounter ADD COLUMN rules_version varchar(32);
ALTER TABLE game.t_encounter ADD COLUMN spawn_tier smallint CHECK (spawn_tier BETWEEN 1 AND 5);
UPDATE game.t_encounter e SET rules_version=COALESCE(
    (SELECT b.rules_version FROM game.t_battle b WHERE b.encounter_id=e.encounter_id), 'ALPHA_V1');
ALTER TABLE game.t_encounter ALTER COLUMN rules_version SET NOT NULL;
ALTER TABLE game.t_encounter ALTER COLUMN rules_version SET DEFAULT 'ALPHA_V1';
ALTER TABLE game.t_encounter ADD CONSTRAINT ck_encounter_rules_version CHECK (length(btrim(rules_version))>0);

CREATE FUNCTION game.preserve_encounter_generation_snapshot() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.rules_version IS DISTINCT FROM OLD.rules_version OR NEW.spawn_tier IS DISTINCT FROM OLD.spawn_tier THEN
        RAISE EXCEPTION 'Encounter generation snapshot is immutable' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER encounter_generation_snapshot_immutable BEFORE UPDATE OF rules_version,spawn_tier
    ON game.t_encounter FOR EACH ROW EXECUTE FUNCTION game.preserve_encounter_generation_snapshot();

-- Prevent an old writer from replacing a future encounter version with its Alpha default.
CREATE FUNCTION game.require_battle_encounter_rules_version() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.rules_version IS DISTINCT FROM (SELECT e.rules_version FROM game.t_encounter e WHERE e.encounter_id=NEW.encounter_id) THEN
        RAISE EXCEPTION 'Battle rules must match encounter snapshot' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER battle_encounter_rules_version_match BEFORE INSERT ON game.t_battle
    FOR EACH ROW EXECUTE FUNCTION game.require_battle_encounter_rules_version();
