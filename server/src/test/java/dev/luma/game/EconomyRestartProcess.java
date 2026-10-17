package dev.luma.game;

import dev.luma.game.economy.RewardEconomy;
import static dev.luma.game.economy.RewardEntitlement.*;
import java.time.LocalDate;
import java.util.Map;
import java.util.UUID;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;

/** Separate test JVM; no production command or endpoint. */
public final class EconomyRestartProcess {
    public static void main(String[] args) {
        String url=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!url.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?"))throw new IllegalStateException("Test DB required");
        try(var app=new SpringApplicationBuilder(GameApplication.class).web(WebApplicationType.NONE).run(
                "--spring.datasource.url="+url,
                "--spring.datasource.username="+System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"),
                "--spring.datasource.password="+System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD",""),
                "--spring.datasource.hikari.maximum-pool-size=1",
                "--luma.economy.rewards-enabled=true")) {
            long player=Long.parseLong(args[0]);var command=UUID.fromString(args[1]);String mode=args[2];
            var economy=app.getBean(RewardEconomy.class);
            var terms=new Terms(mode.equals("write")?"TEST_V1":"TEST_V2",mode.equals("write")?7:999,Map.of("SMALL_POTION",2));
            var right=economy.entitle(Key.weekly(player,LocalDate.of(2026,10,12),"RESTART"),terms);
            if(!right.terms().policyVersion().equals("TEST_V1") || right.terms().gold()!=7)
                throw new AssertionError("Stored terms were rewritten");
            var result=economy.claim(player,right.id(),command);
            if(result.granted()==mode.equals("new-command"))throw new AssertionError("Incorrect replay");
            System.out.println("ECONOMY_RESTART_OK");
        }
    }
}
