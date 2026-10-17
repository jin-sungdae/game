package dev.luma.game;

import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import java.time.Instant;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;

class CollectionEncounterRestartTest {
    ConfigurableApplicationContext start() {
        String db=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!db.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?"))throw new IllegalStateException("Test DB required");
        return new SpringApplicationBuilder(GameApplication.class).run("--server.port=0","--luma.collection-foundation.enabled=true",
            "--spring.datasource.url="+db,"--spring.datasource.username="+System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),
            "--spring.datasource.password="+System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD",""));
    }
    @Test void persistedReceiptHoldAndIssuanceDeadlineSurviveApplicationRestart() {
        UUID encounter;UUID reservation=UUID.randomUUID();Instant deadline;
        try(var app=start()){
            var db=app.getBean(JdbcTemplate.class);CollectionEncounterFoundationTest.clean(db);
            var f=app.getBean(CollectionEncounterFoundation.class);var b=app.getBean(BattleService.class);
            var issued=f.issueNatural();encounter=issued.encounter().encounterId();deadline=issued.nextAvailableAt();
            var battle=b.start(encounter);
            while(battle.status().equals("ACTIVE"))battle=b.attack(battle.battleId());
            assertEquals("VICTORY",battle.status());assertTrue(f.recordCompletion(encounter));
            f.reserve(reservation,"PIP",1);b.ignore(encounter);
        }
        try(var app=start()){
            var db=app.getBean(JdbcTemplate.class);
            try {
                var f=app.getBean(CollectionEncounterFoundation.class);
                assertEquals(new CollectionEncounterFoundation.Progress(1,1,0),f.progress());
                assertFalse(f.recordCompletion(encounter));
                assertEquals("HELD",f.reserve(reservation,"PIP",1).consumptionState());
                var blocked=f.issueNatural();assertNull(blocked.encounter());assertEquals(deadline,blocked.nextAvailableAt());
                f.cancel(reservation);assertEquals(1,f.progress().available());
            } finally {CollectionEncounterFoundationTest.clean(db);}
        }
    }
}
