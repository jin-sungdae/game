package dev.luma.game;

import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.boot.test.web.client.TestRestTemplate;
import static org.junit.jupiter.api.Assertions.*;

class CompanionOwnershipRestartTest {
    ConfigurableApplicationContext start() {
        String db=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!db.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?")) throw new IllegalStateException("Test DB required");
        return new SpringApplicationBuilder(GameApplication.class).run("--server.port=0",
            "--spring.datasource.url="+db,"--spring.datasource.username="+System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),
            "--spring.datasource.password="+System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD",""));
    }
    String url(ConfigurableApplicationContext app) { return "http://127.0.0.1:"+app.getEnvironment().getProperty("local.server.port")+"/api/v1/companions"; }
    @Test void committedRosterSurvivesIndependentServerRestart() {
        var http=new TestRestTemplate();CompanionOwnershipDtos.Ownership before;
        try(var app=start()) {
            var db=app.getBean(JdbcTemplate.class);CompanionOwnershipIntegrationTest.clean(db);
            CompanionOwnershipIntegrationTest.add(db,1,"RUU");CompanionOwnershipIntegrationTest.add(db,1,"NOX");
            db.update("UPDATE game.t_player_companion SET level=3,exp=321,bond=8 WHERE active AND player_id=1");
            before=http.getForObject(url(app),CompanionOwnershipDtos.Ownership.class);
            assertNotNull(before);assertEquals(3,before.companions().size());
        }
        try(var app=start()) {
            try { assertEquals(before,http.getForObject(url(app),CompanionOwnershipDtos.Ownership.class)); }
            finally { CompanionOwnershipIntegrationTest.clean(app.getBean(JdbcTemplate.class)); }
        }
    }
}
