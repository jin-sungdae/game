INSERT INTO game.m_species(code,name) VALUES ('MOA','MOA'),('RUU','RUU'),('NOX','NOX');
INSERT INTO game.m_species_evolution(species_id,evolution_stage,name)
SELECT species_id, stage, evolution_name FROM game.m_species
CROSS JOIN (VALUES (1,'MOA'),(2,'MOKORI'),(3,'NEBLA'),(4,'SYLVAON'),(5,'AETHERIA')) AS stages(stage,evolution_name)
WHERE code='MOA';
-- TODO: RUU/NOX stages 2-5 require confirmed Master Concept names. Do not invent them.
INSERT INTO game.m_species_evolution(species_id,evolution_stage,name)
SELECT species_id,1,name FROM game.m_species WHERE code IN ('RUU','NOX');
INSERT INTO game.t_player(player_id,player_name,gold) VALUES (1,'LOCAL_PLAYER',0);
SELECT setval(pg_get_serial_sequence('game.t_player','player_id'),1,true);
INSERT INTO game.t_player_companion(player_id,species_id,evolution_stage,level,exp,bond,active)
SELECT 1,species_id,1,1,0,0,true FROM game.m_species WHERE code='MOA';
INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn)
VALUES ('PIP','PIP','COMMON','GROUND',1,3,100,true);
