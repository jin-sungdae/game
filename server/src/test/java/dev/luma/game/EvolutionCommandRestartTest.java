package dev.luma.game;

import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import static org.junit.jupiter.api.Assertions.*;

/** Independent HTTP application contexts share only PostgreSQL receipts/state.
 * The revision provider is a test fixture; this does not exercise Switching or ABA.
 * Orderly context restart is not a PostgreSQL crash-recovery test.
 */
class EvolutionCommandRestartTest {
    private static final String SCHEMA = "X-Luma-Response-Schema-Version";
    private final String database = System.getenv().getOrDefault("LUMA_TEST_DB_URL",
        "jdbc:postgresql://127.0.0.1:55439/luma_game_test");
    private final String user = System.getenv().getOrDefault("LUMA_TEST_DB_USER", "luma");
    private final String password = System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD", "");

    private void requireTestDatabase() {
        if (!database.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?"))
            throw new IllegalStateException("Test DB required");
    }
    private ConfigurableApplicationContext start(boolean withTestRevision) {
        requireTestDatabase();
        var builder = new SpringApplicationBuilder(GameApplication.class);
        if (withTestRevision) builder.initializers(app -> app.getBeanFactory().registerSingleton(
            "restartTestSelectionRevision", (EvolutionSelectionRevision) player -> 7L));
        return builder.run("--server.port=0", "--spring.datasource.url=" + database,
            "--spring.datasource.username=" + user, "--spring.datasource.password=" + password);
    }
    private String url(ConfigurableApplicationContext app) {
        return "http://127.0.0.1:" + app.getEnvironment().getProperty("local.server.port")
            + "/api/v1/companions/active/evolve";
    }
    private void clean(JdbcTemplate db) {
        db.update("DELETE FROM game.t_command_receipt");
        CompanionBondIntegrationTest.clean(db);
    }
    @Test void committedReceiptReplaysAfterRestartWithoutSwitchingProvider() throws Exception {
        requireTestDatabase();
        var http = new TestRestTemplate();
        // Dedicated test DB connection permits cleanup even after either server stops.
        var cleanup = new JdbcTemplate(new DriverManagerDataSource(database, user, password));
        EvolutionCommandRequest command;
        ResponseEntity<String> original;
        try {
            try (var app = start(true)) {
                var db = app.getBean(JdbcTemplate.class);
                clean(db);
                db.update("UPDATE game.t_player_companion SET level=6,exp=1500,bond=12 WHERE active");
                long companion = db.queryForObject(
                    "SELECT player_companion_id FROM game.t_player_companion WHERE player_id=1 AND active", Long.class);
                command = new EvolutionCommandRequest(UUID.randomUUID(), companion, 1, 7);
                original = http.postForEntity(url(app), command, String.class);
                assertEquals(200, original.getStatusCode().value());
                assertEquals("1", original.getHeaders().getFirst(SCHEMA));
                var result = app.getBean(com.fasterxml.jackson.databind.ObjectMapper.class)
                    .readTree(original.getBody());
                assertEquals("EVOLVED", result.path("result").asText());
                assertEquals(2, result.path("bootstrap").path("activeCompanion").path("evolutionStage").asInt());
                assertEquals(1, db.queryForObject("SELECT count(*) FROM game.t_command_receipt", Integer.class));
                assertEquals(1, db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history", Integer.class));
            }
            try (var app = start(false)) {
                assertTrue(app.getBeansOfType(EvolutionSelectionRevision.class).isEmpty());
                var replay = http.postForEntity(url(app), command, String.class);
                assertEquals(original.getStatusCode(), replay.getStatusCode());
                assertEquals(original.getBody(), replay.getBody());
                assertEquals(original.getHeaders().getFirst(SCHEMA), replay.getHeaders().getFirst(SCHEMA));
                var fresh = new EvolutionCommandRequest(UUID.randomUUID(), command.expectedCompanionId(), 2, 7);
                var blocked = http.postForEntity(url(app), fresh, String.class);
                assertEquals(503, blocked.getStatusCode().value());
                assertEquals("BLOCKED_BY_SWITCHING_CONTRACT",
                    app.getBean(com.fasterxml.jackson.databind.ObjectMapper.class)
                        .readTree(blocked.getBody()).path("code").asText());
                var db = app.getBean(JdbcTemplate.class);
                assertEquals(2, db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE active", Integer.class));
                assertEquals(1, db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history", Integer.class));
                assertEquals(1, db.queryForObject("SELECT count(*) FROM game.t_command_receipt", Integer.class));
            }
        } finally {
            clean(cleanup);
        }
    }
}
