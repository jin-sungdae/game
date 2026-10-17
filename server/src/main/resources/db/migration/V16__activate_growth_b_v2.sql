-- Approved Level 1..100 policy. PostgreSQL/Flyway runs the whole migration transactionally.
-- Invalid legacy saves abort; no automatic cleanup, EXP reduction or reward issuance.
LOCK TABLE game.t_player_companion IN ACCESS EXCLUSIVE MODE;
DO $$
DECLARE row_data record; expected integer;
BEGIN
    FOR row_data IN SELECT player_companion_id, level, exp FROM game.t_player_companion LOOP
        expected := 1;
        WHILE expected < 20 AND row_data.exp >= 50::bigint * (expected + 1) * expected LOOP
            expected := expected + 1;
        END LOOP;
        IF row_data.exp < 0 OR row_data.level NOT BETWEEN 1 AND 20 OR row_data.level <> expected THEN
            RAISE EXCEPTION 'GROWTH_PREFLIGHT_FAILED companion=% level=% exp=% expected_alpha_level=%',
                row_data.player_companion_id, row_data.level, row_data.exp, expected;
        END IF;
    END LOOP;
END $$;

CREATE FUNCTION game.growth_b_level_v2(total_exp bigint) RETURNS integer
LANGUAGE plpgsql IMMUTABLE STRICT AS $$
DECLARE candidate integer; threshold bigint; result integer := 1;
BEGIN
    IF total_exp < 0 THEN RAISE EXCEPTION 'Negative EXP' USING ERRCODE='22023'; END IF;
    FOR candidate IN 2..100 LOOP
        threshold := CASE
            WHEN candidate <= 6 THEN 50::bigint * candidate * (candidate - 1)
            WHEN candidate <= 20 THEN 1500::bigint + 600 * (candidate - 6)
            WHEN candidate <= 50 THEN 9900::bigint + 800 * (candidate - 20)
            WHEN candidate <= 75 THEN 33900::bigint + 1000 * (candidate - 50)
            ELSE 58900::bigint + 1200 * (candidate - 75) END;
        EXIT WHEN total_exp < threshold;
        result := candidate;
    END LOOP;
    RETURN result;
END $$;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM game.t_player_companion WHERE game.growth_b_level_v2(exp) < level) THEN
        RAISE EXCEPTION 'GROWTH_PREFLIGHT_FAILED level decrease';
    END IF;
END $$;
ALTER TABLE game.t_player_companion ADD COLUMN growth_policy_version varchar(32)
    NOT NULL DEFAULT 'GROWTH_B_V2' CHECK (growth_policy_version = 'GROWTH_B_V2');
UPDATE game.t_player_companion SET level = game.growth_b_level_v2(exp);
-- Old servers may still connect, but cannot persist levels calculated using the old curve.
ALTER TABLE game.t_player_companion ADD CONSTRAINT ck_companion_growth_b_v2
    CHECK (level BETWEEN 1 AND 100 AND level = game.growth_b_level_v2(exp));
-- Existing battles, skill states, history, items, cooldowns and rewards are deliberately untouched.
