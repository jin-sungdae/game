package dev.luma.game;

import java.net.URLClassLoader;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import org.springframework.test.annotation.DirtiesContext;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(properties="spring.datasource.hikari.maximum-pool-size=2")
@DirtiesContext(classMode=DirtiesContext.ClassMode.AFTER_CLASS)
class RewardEconomyRestartTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
    @Autowired JdbcTemplate db;
    @Test void entitlementLedgerAndReceiptSurviveSeparateJvmRestarts() throws Exception {
        long player=db.queryForObject("INSERT INTO game.t_player(player_name) VALUES ('economy-restart') RETURNING player_id",Long.class);
        var command=UUID.randomUUID();
        var entries=new LinkedHashSet<String>(Arrays.asList(System.getProperty("java.class.path").split(java.io.File.pathSeparator)));
        for(ClassLoader loader=getClass().getClassLoader();loader!=null;loader=loader.getParent())
            if(loader instanceof URLClassLoader urls)for(var url:urls.getURLs())entries.add(Path.of(url.toURI()).toString());
        try {
            for(String mode:List.of("write","replay","new-command")){
                var log=Files.createTempFile("economy-restart-",".log");
                var process=new ProcessBuilder(Path.of(System.getProperty("java.home"),"bin","java").toString(),
                    "-cp",String.join(java.io.File.pathSeparator,entries),EconomyRestartProcess.class.getName(),
                    Long.toString(player),(mode.equals("new-command")?UUID.randomUUID():command).toString(),mode)
                    .redirectErrorStream(true).redirectOutput(log.toFile()).start();
                try {
                    assertTrue(process.waitFor(45,TimeUnit.SECONDS),"Restart process timeout");
                    String output=Files.readString(log);
                    assertEquals(0,process.exitValue(),output);
                    assertTrue(output.contains("ECONOMY_RESTART_OK"),output);
                } finally {if(process.isAlive())process.destroyForcibly();Files.deleteIfExists(log);}
            }
            assertEquals(7,db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=?",Long.class,player));
            assertEquals(2,db.queryForObject("SELECT quantity FROM game.t_inventory WHERE player_id=?",Integer.class,player));
            assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_economy_reward_ledger WHERE player_id=?",Integer.class,player));
            assertEquals(2,db.queryForObject("SELECT count(*) FROM game.t_command_receipt WHERE player_id=?",Integer.class,player));
        } finally {
            db.execute("TRUNCATE game.t_economy_reward_ledger,game.t_reward_entitlement_item,game.t_reward_entitlement");
            db.update("DELETE FROM game.t_inventory WHERE player_id=?",player);
            db.update("DELETE FROM game.t_command_receipt WHERE player_id=?",player);
            db.update("DELETE FROM game.t_player WHERE player_id=?",player);
        }
    }
}
