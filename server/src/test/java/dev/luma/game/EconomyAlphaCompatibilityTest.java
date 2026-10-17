package dev.luma.game;

import dev.luma.game.economy.*;
import static dev.luma.game.economy.RewardEntitlement.*;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import org.springframework.test.annotation.DirtiesContext;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(properties="spring.datasource.hikari.maximum-pool-size=2")
@DirtiesContext(classMode=DirtiesContext.ClassMode.AFTER_CLASS)
class EconomyAlphaCompatibilityTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Autowired GameService game;
    @Autowired BattleService battles;
    @Autowired RewardEconomy economy;
    @Autowired EncounterIssuancePolicy policy;
    @BeforeEach @AfterEach void cleanup(){CompanionBondIntegrationTest.clean(db);}
    @Test void defaultDisabledAndAlphaIssueReuseIgnoreAndRewardAreUnchanged(){
        assertEquals(EncounterIssuancePolicy.Mode.DISABLED,policy.mode());
        assertThrows(GameFault.class,()->economy.entitle(Key.weekly(1,LocalDate.of(2026,10,12),"SLOT"),
            new Terms("TEST",7,Map.of())));
        var first=game.createEncounter();assertEquals(first,game.createEncounter());
        assertEquals(Duration.ofSeconds(60),Duration.between(first.spawnedAt(),first.expiresAt()));
        assertTrue(first.monster().level()>=1&&first.monster().level()<=3);
        battles.ignore(first.encounterId());
        var second=game.createEncounter();assertNotEquals(first.encounterId(),second.encounterId());
        var battle=battles.start(second.encounterId());
        while(battle.status().equals("ACTIVE"))battle=battles.attack(battle.battleId());
        assertEquals("VICTORY",battle.status());
        assertEquals(CombatRules.gold(second.monster().level()),battle.reward().gold());
        assertEquals(CombatRules.exp(second.monster().level()),battle.reward().exp());
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward_entitlement",Integer.class));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_economy_reward_ledger",Integer.class));
    }
}
