package dev.luma.game;

import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@SpringBootTest
class BattleRulesVersionIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Autowired BattleService battles;
    @Autowired GameService game;
    @Autowired ItemService items;
    @MockitoBean RandomSource random;
    @BeforeEach void reset(){CompanionBondIntegrationTest.clean(db);when(random.nextLong(anyLong())).thenReturn(0L);}
    @AfterEach void clean(){CompanionBondIntegrationTest.clean(db);}

    BattleDtos.Battle start(String code,int monsterLevel,int level) {
        db.update("UPDATE game.m_monster SET use_yn=(code=?)",code);
        db.update("UPDATE game.t_player_companion SET level=?,exp=?",level,50L*level*(level-1));
        var encounter=game.createEncounter();
        db.update("UPDATE game.t_encounter SET monster_level=? WHERE encounter_id=?",monsterLevel,encounter.encounterId());
        return battles.start(encounter.encounterId());
    }
    String snapshot(String table) {
        return db.queryForObject("SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM game."+table+" t",String.class);
    }
    Map<String,String> snapshot() {
        var state=new LinkedHashMap<String,String>();
        for(String t:List.of("t_battle","t_encounter","t_reward","t_collection","t_player","t_player_companion","t_battle_item_effect","t_inventory","t_item_purchase"))
            state.put(t,snapshot(t));
        return state;
    }
    void replaceVersion(UUID battle,String version) {
        // A future writer fixture INSERTs an unsupported version; UPDATE is forbidden.
        String json=db.queryForObject("SELECT jsonb_set(to_jsonb(b),'{rules_version}',to_jsonb(?::text))::text FROM game.t_battle b WHERE battle_id=?",String.class,version,battle);
        db.update("DELETE FROM game.t_battle WHERE battle_id=?",battle);
        db.update("INSERT INTO game.t_battle SELECT * FROM jsonb_populate_record(NULL::game.t_battle,?::jsonb)",json);
    }

    @ParameterizedTest
    @ValueSource(strings={"PIP","MELLO","MOSSY","CHIRP","BUBU","PEBB","PUFF","TIKKI","MIMI","WISP","SHADE","EMBER","LUNET","NOVA","NOCT"})
    void allAlphaSpeciesMatchFrozenArithmeticAndCounterOracle(String code) {
        for(int level:List.of(1,20)) for(int monsterLevel=1;monsterLevel<=3;monsterLevel++) {
            CompanionBondIntegrationTest.clean(db);
            when(random.nextLong(anyLong())).thenReturn(0L);
            var b=start(code,monsterLevel,level);
            assertEquals("ALPHA_V1",db.queryForObject("SELECT rules_version FROM game.t_battle WHERE battle_id=?",String.class,b.battleId()));
            assertEquals(b.battleId(),battles.start(b.encounterId()).battleId());
            int hp=100,monsterHp=20+10*monsterLevel,turn=0;
            var personality=MonsterContent.find(code).orElseThrow().battlePersonality();
            when(random.nextLong(100)).thenReturn(50L);
            while(monsterHp>0) {
                monsterHp=Math.max(0,monsterHp-(10+2*level));
                boolean counter=monsterHp>0 && switch(personality) {
                    case BALANCED, AGGRESSIVE -> true;
                    case DEFENSIVE -> false;
                    case ERRATIC -> turn%2==1;
                };
                if(counter)hp=Math.max(0,hp-(3+2*monsterLevel));
                b=battles.attack(b.battleId());turn++;
                assertEquals(hp,b.companion().hp());assertEquals(monsterHp,b.monster().hp());assertEquals(turn,b.turn());
                assertEquals(counter,b.events().contains("MONSTER_ATTACK"));
                assertEquals(monsterHp>0&&!counter,b.events().contains("MONSTER_WAIT"));
            }
            assertEquals("VICTORY",b.status());
            assertEquals(new BattleDtos.Reward(monsterLevel*10L,monsterLevel*20L,0),b.reward());
            var expiry=db.queryForObject("SELECT expires_at FROM game.t_encounter WHERE encounter_id=?",java.time.OffsetDateTime.class,b.encounterId());
            when(random.nextLong(1_000_000)).thenReturn(0L);
            var captured=battles.capture(b.battleId());
            double base=switch(MonsterContent.find(code).orElseThrow().rarity()) {
                case "COMMON" -> .35; case "UNCOMMON" -> .25; case "RARE" -> .15; case "SPECIAL" -> .05;
                default -> throw new AssertionError();
            };
            assertTrue(captured.success());assertEquals(base+.5,captured.chance(),1e-12);
            assertEquals(expiry,db.queryForObject("SELECT expires_at FROM game.t_encounter WHERE encounter_id=?",java.time.OffsetDateTime.class,b.encounterId()));
            assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
        }
    }

    @Test void activeCaptureAndDefeatPreserveAlphaResults() {
        var b=start("PIP",1,1);
        when(random.nextLong(1_000_000)).thenReturn(999999L);
        var failed=battles.capture(b.battleId());
        assertFalse(failed.success());assertEquals(.35,failed.chance(),1e-12);
        assertEquals(95,failed.battle().companion().hp());assertEquals(1,failed.battle().turn());
        when(random.nextLong(1_000_000)).thenReturn(0L);
        assertTrue(battles.capture(b.battleId()).success());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
        CompanionBondIntegrationTest.clean(db);
        b=start("PIP",1,1);
        db.update("UPDATE game.t_battle SET companion_hp=1 WHERE battle_id=?",b.battleId());
        var loss=battles.attack(b.battleId());
        assertEquals("DEFEAT",loss.status());assertEquals(0,loss.companion().hp());assertEquals(18,loss.monster().hp());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
    }

    @ParameterizedTest @ValueSource(strings={"EXPANDED_V2","UNKNOWN_V99"})
    void unsupportedActiveAndVictoryRejectWithoutAnyMutationIncludingLazyExpiry(String version) {
        for(boolean victory:List.of(false,true)) {
            CompanionBondIntegrationTest.clean(db);
            var b=start("PIP",1,1);
            if(victory)while(b.status().equals("ACTIVE"))b=battles.attack(b.battleId());
            final var stored=b;
            replaceVersion(b.battleId(),version);
            db.update("UPDATE game.t_encounter SET spawned_at=clock_timestamp()-interval '2 minutes',expires_at=clock_timestamp()-interval '1 second' WHERE encounter_id=?",b.encounterId());
            var before=snapshot();clearInvocations(random);
            for(Runnable action:List.<Runnable>of(
                ()->battles.get(stored.battleId()),()->battles.start(stored.encounterId()),
                ()->battles.attack(stored.battleId()),()->battles.capture(stored.battleId()),
                ()->battles.ignore(stored.encounterId()),
                ()->items.use("SMALL_POTION",stored.battleId()),
                ()->items.use("CAPTURE_CHARM",stored.battleId()),
                ()->items.effects(stored.battleId()))) {
                assertThrows(GameUnavailable.class,action::run);
                assertEquals(before,snapshot());
            }
            if(victory) {
                assertThrows(GameUnavailable.class,game::activeEncounter);
                assertEquals(before,snapshot());
                assertThrows(GameUnavailable.class,game::createEncounter);
                assertEquals(before,snapshot());
            }
            verifyNoInteractions(random);
        }
    }

    @Test void databaseVersionIsImmutableAndAlphaExpiryStillCommits() {
        var b=start("PIP",1,1);
        assertThrows(org.springframework.dao.DataIntegrityViolationException.class,()->db.update(
            "UPDATE game.t_battle SET rules_version='EXPANDED_V2' WHERE battle_id=?",b.battleId()));
        var current=b;while(current.status().equals("ACTIVE"))current=battles.attack(current.battleId());
        db.update("UPDATE game.t_encounter SET spawned_at=clock_timestamp()-interval '2 minutes',expires_at=clock_timestamp()-interval '1 second' WHERE encounter_id=?",b.encounterId());
        assertThrows(GameFault.class,()->battles.capture(b.battleId()));
        assertEquals("DEFEATED",db.queryForObject("SELECT status FROM game.t_encounter WHERE encounter_id=?",String.class,b.encounterId()));
        assertEquals("ALPHA_V1",db.queryForObject("SELECT rules_version FROM game.t_battle WHERE battle_id=?",String.class,b.battleId()));
    }
    @Test void missingAndReservedVersionsNeverFallback() {
        for(String value:Arrays.asList(null,"","alpha_v1","EXPANDED_V2","FUTURE"))
            assertThrows(GameUnavailable.class,()->BattleRulesVersion.requireSupported(value));
        assertDoesNotThrow(()->BattleRulesVersion.requireSupported("ALPHA_V1"));
    }
}
