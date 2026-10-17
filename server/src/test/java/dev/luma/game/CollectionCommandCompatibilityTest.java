package dev.luma.game;
import dev.luma.game.command.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;
@SpringBootTest(properties="luma.collection-foundation.enabled=true")
class CollectionCommandCompatibilityTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired JdbcTemplate db; @Autowired GameService game; @Autowired BattleService battles;
 @Autowired CollectionEncounterFoundation f; @Autowired CommandReceiptExecutor commands;
 @BeforeEach @AfterEach void clean(){db.update("DELETE FROM game.t_command_receipt");CollectionEncounterFoundationTest.clean(db);}
 UUID win(){var e=game.createEncounter();var b=battles.start(e.encounterId());while(b.status().equals("ACTIVE"))b=battles.attack(b.battleId());assertEquals("VICTORY",b.status());return e.encounterId();}
 @Test void receiptReplayAndDistinctCommandsForSameEncounterPayOnce() throws Exception {
  var e=win();var request=new CommandRequest(1,UUID.randomUUID(),"OBSERVATION_COMPLETION",e.toString(),"{}");
  var calls=new AtomicInteger();var gate=new CountDownLatch(1);
  try(var pool=Executors.newFixedThreadPool(4)){
   var futures=new ArrayList<Future<CommandResponse>>();
   for(int i=0;i<8;i++) futures.add(pool.submit(()->{gate.await();return commands.execute(request,()->{calls.incrementAndGet();return new CommandResponse(200,"{\"paid\":"+f.recordCompletion(e)+"}",1);});}));
   gate.countDown();for(var result:futures)assertEquals("{\"paid\":true}",result.get(15,TimeUnit.SECONDS).body());
  }
  assertEquals(1,calls.get());assertEquals(1,f.progress().earned());
  var different=new CommandRequest(1,UUID.randomUUID(),"OBSERVATION_COMPLETION",e.toString(),"{}");
  assertEquals("{\"paid\":false}",commands.execute(different,()->new CommandResponse(200,"{\"paid\":"+f.recordCompletion(e)+"}",1)).body());
  assertEquals(1,f.progress().earned());assertEquals(2,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
 }
 @Test void commandFailureRollsBackBattleRewardObservationAndReceiptTogether(){
  var request=new CommandRequest(1,UUID.randomUUID(),"VICTORY_COMPLETION","local","{}");
  assertThrows(IllegalStateException.class,()->commands.execute(request,()->{assertTrue(f.recordCompletion(win()));throw new IllegalStateException("fault after observation");}));
  assertEquals(0,f.progress().earned());assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));
  assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_encounter",Integer.class));assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
 }
}
