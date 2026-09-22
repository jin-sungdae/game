package dev.luma.game;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Transactional
class MonsterContentIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r) {GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate jdbc;
    @Autowired GameRepository repository;
    @Test void evenExplicitlyEnabledAlphaAndUnknownDbRowsCannotEnterEncounterCandidates() {
        jdbc.update("UPDATE game.m_monster SET use_yn=true WHERE code='PIP'");
        for(var d:MonsterContent.definitions()) if(d.alphaCandidate() && !d.contentReady())
            jdbc.update("INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn) VALUES (?,?,?,?,1,3,?,true)",d.monsterCode(),d.displayName(),d.rarity(),d.movementProfile(),d.encounterWeight());
        jdbc.update("INSERT INTO game.m_monster(code,name,rarity,movement_profile,min_level,max_level,encounter_weight,use_yn) VALUES ('UNKNOWN','Unknown','COMMON','GROUND',1,3,100,true)");
        assertEquals(List.of("PIP","MELLO","MOSSY","CHIRP","BUBU"),repository.monsters().stream().map(MonsterSelector.Monster::code).toList());
        jdbc.update("UPDATE game.m_monster SET use_yn=false");
        assertTrue(repository.monsters().isEmpty());
    }
    @Test void pipDatabaseMasterAndPersistentIdentityRemainUnchanged() {
        var pip=repository.monsters().getFirst();
        assertEquals("PIP",pip.code());assertEquals("COMMON",pip.rarity());assertEquals("GROUND",pip.movementProfile());
        assertEquals(1,pip.minLevel());assertEquals(3,pip.maxLevel());assertEquals(100,pip.weight());
        jdbc.update("UPDATE game.m_monster SET encounter_weight=999 WHERE code='PIP'");
        assertThrows(GameUnavailable.class,()->repository.monsters());
    }
}
