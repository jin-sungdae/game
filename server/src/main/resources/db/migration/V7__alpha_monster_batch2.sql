-- Approved Batch 2 only; previous masters and migrations are unchanged.
-- Rarity defaults remain server-owned: COMMON100, UNCOMMON50.
INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn)
VALUES ('PEBB','PEBB','COMMON','GROUND',1,3,100,true),
       ('PUFF','PUFF','COMMON','FLOATING',1,3,100,true),
       ('TIKKI','TIKKI','UNCOMMON','GROUND',1,3,50,true),
       ('MIMI','MIMI','UNCOMMON','STATIC',1,3,50,true),
       ('WISP','WISP','UNCOMMON','FLOATING',1,3,50,true);
