-- Approved Batch 1 only. PIP and previous migration history are unchanged.
-- COMMON defaults: weight100, capture base0.35 (formula remains server-owned).
INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn)
VALUES ('MELLO','MELLO','COMMON','JUMP',1,3,100,true),
       ('MOSSY','MOSSY','COMMON','GROUND',1,3,100,true),
       ('CHIRP','CHIRP','COMMON','FLYING',1,3,100,true),
       ('BUBU','BUBU','COMMON','JUMP',1,3,100,true);
