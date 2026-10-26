package dev.luma.game;

import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class EncounterGenerationSnapshotTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Autowired GameService game;
    @Autowired BattleService battles;
    @BeforeEach void reset(){CompanionBondIntegrationTest.clean(db);}
    @AfterEach void clean(){CompanionBondIntegrationTest.clean(db);}
    @Test void levelTierAndRulesStayAtCreationAcrossGrowthAndBattleStart() {
        db.update("UPDATE game.t_player_companion SET exp=88900,level=100 WHERE active");
        var encounter=game.createEncounter();
        assertTrue(encounter.monster().level()>=1 && encounter.monster().level()<=3);
        assertEquals(5,db.queryForObject("SELECT spawn_tier FROM game.t_encounter WHERE encounter_id=?",Integer.class,encounter.encounterId()));
        assertEquals("ALPHA_V1",version(encounter.encounterId()));
        db.update("UPDATE game.t_player_companion SET exp=0,level=1 WHERE active");
        assertEquals(encounter,game.createEncounter());
        var battle=battles.start(encounter.encounterId());
        assertEquals(version(encounter.encounterId()),db.queryForObject("SELECT rules_version FROM game.t_battle WHERE battle_id=?",String.class,battle.battleId()));
        assertEquals(5,db.queryForObject("SELECT spawn_tier FROM game.t_encounter WHERE encounter_id=?",Integer.class,encounter.encounterId()));
    }
    String version(UUID id){return db.queryForObject("SELECT rules_version FROM game.t_encounter WHERE encounter_id=?",String.class,id);}
    @Test void unknownVersionFailsWithoutExpiryOrBattleMutation() {
        var e=game.createEncounter();
        String json=db.queryForObject("SELECT jsonb_set(to_jsonb(e),'{rules_version}','\"EXPANDED_V2\"'::jsonb)::text FROM game.t_encounter e WHERE encounter_id=?",String.class,e.encounterId());
        db.update("DELETE FROM game.t_encounter WHERE encounter_id=?",e.encounterId());
        db.update("INSERT INTO game.t_encounter SELECT * FROM jsonb_populate_record(NULL::game.t_encounter,?::jsonb)",json);
        assertThrows(GameUnavailable.class,()->battles.start(e.encounterId()));
        assertThrows(GameUnavailable.class,game::activeEncounter);
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_battle",Integer.class));
        assertEquals("ACTIVE",db.queryForObject("SELECT status FROM game.t_encounter WHERE encounter_id=?",String.class,e.encounterId()));
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("UPDATE game.t_encounter SET rules_version='ALPHA_V1' WHERE encounter_id=?",e.encounterId()));
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("UPDATE game.t_encounter SET spawn_tier=5 WHERE encounter_id=?",e.encounterId()));
        // Old server defaults must not downgrade a future encounter on battle INSERT.
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update("""
            INSERT INTO game.t_battle(battle_id,encounter_id,player_companion_id,monster_id,
            companion_hp,companion_max_hp,monster_hp,monster_max_hp,companion_attack,monster_attack,status)
            SELECT ?,e.encounter_id,c.player_companion_id,e.monster_id,100,100,30,30,12,5,'ACTIVE'
            FROM game.t_encounter e CROSS JOIN game.t_player_companion c WHERE e.encounter_id=? AND c.active
            """,UUID.randomUUID(),e.encounterId()));
    }
}
