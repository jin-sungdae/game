package dev.luma.game;

import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.boot.test.web.client.TestRestTemplate;
import static org.junit.jupiter.api.Assertions.*;

/** Two independently started/stopped Spring HTTP servers share only PostgreSQL state. */
class CompanionBondRestartTest {
    ConfigurableApplicationContext start() {
        String db=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!db.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?"))throw new IllegalStateException("Test DB required");
        return new SpringApplicationBuilder(GameApplication.class).run("--server.port=0",
            "--spring.datasource.url="+db,"--spring.datasource.username="+System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),
            "--spring.datasource.password="+System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD",""));
    }
    String url(ConfigurableApplicationContext app,String path){return "http://127.0.0.1:"+app.getEnvironment().getProperty("local.server.port")+"/api/v1"+path;}
    @Test void interactionAndBerryAndCooldownSurviveSpringRestart() {
        var http=new TestRestTemplate();java.time.Instant next;
        try(var app=start()){
            var db=app.getBean(JdbcTemplate.class);CompanionBondIntegrationTest.clean(db);
            db.update("UPDATE game.t_player_companion SET bond=75,exp=1500,level=6,evolution_stage=3");
            db.update("UPDATE game.t_player SET gold=30");
            var r=http.postForObject(url(app,"/companions/active/interact"),null,CompanionInteractionService.Result.class);
            assertEquals(76,r.bootstrap().activeCompanion().bond());next=r.nextAvailableAt();
            http.postForObject(url(app,"/shop/purchases"),new ItemDtos.PurchaseRequest("BOND_BERRY",1),ItemDtos.Purchase.class);
            var use=http.postForObject(url(app,"/inventory/items/BOND_BERRY/use"),null,ItemDtos.Use.class);assertEquals(77,use.bondAfter());
        }
        try(var app=start()){
            try {
                var b=http.getForObject(url(app,"/game/bootstrap"),GameDtos.Bootstrap.class);
                assertEquals(77,b.activeCompanion().bond());assertEquals(3,b.activeCompanion().evolutionStage());assertEquals(0,b.player().gold());
                var r=http.postForObject(url(app,"/companions/active/interact"),null,CompanionInteractionService.Result.class);
                assertEquals(CompanionInteractionService.Outcome.COOLDOWN,r.outcome());assertEquals(next,r.nextAvailableAt());assertEquals(77,r.bootstrap().activeCompanion().bond());
                assertEquals(409,http.postForEntity(url(app,"/inventory/items/BOND_BERRY/use"),null,String.class).getStatusCode().value());
            } finally {CompanionBondIntegrationTest.clean(app.getBean(JdbcTemplate.class));}
        }
    }
}
