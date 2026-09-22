-- Final reviewed Alpha rows from Batch3 preparation (#30); previous masters unchanged.
INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn)
VALUES ('SHADE','SHADE','UNCOMMON','EDGE',1,3,50,true),
       ('EMBER','EMBER','RARE','FREE_2D',1,3,20,true),
       ('LUNET','LUNET','RARE','FLOATING',1,3,20,true),
       ('NOVA','NOVA','RARE','FREE_2D',1,3,20,true),
       ('NOCT','NOCT','SPECIAL','EDGE',1,3,1,true);
