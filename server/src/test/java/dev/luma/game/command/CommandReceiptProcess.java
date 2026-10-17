package dev.luma.game.command;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;

/** Test-only separate JVM: no gameplay API or production endpoint is added. */
public final class CommandReceiptProcess {
    public static void main(String[] args) {
        String url = System.getenv().getOrDefault("LUMA_TEST_DB_URL", "jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if (!url.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?")) throw new IllegalStateException("Test database required");
        var source = new DriverManagerDataSource(url,
            System.getenv().getOrDefault("LUMA_TEST_DB_USER", "luma"),
            System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD", ""));
        var jdbc = new JdbcTemplate(source);
        var executor = new CommandReceiptExecutor(jdbc, new DataSourceTransactionManager(source));
        long player = Long.parseLong(args[0]);
        var request = new CommandRequest(player, UUID.fromString(args[1]), "TEST_RESTART", "fixture", "{}");
        var response = executor.execute(request, () -> {
            if (args[2].equals("replay")) throw new AssertionError("Mutation repeated after restart");
            jdbc.update("UPDATE game.t_player SET gold=gold+7 WHERE player_id=?", player);
            return new CommandResponse(201, "{ \"result\": \"persisted\" }", 3);
        });
        if (!response.equals(new CommandResponse(201, "{ \"result\": \"persisted\" }", 3)))
            throw new AssertionError("Stored response changed");
        System.out.println("RECEIPT_PROCESS_OK");
    }
}
