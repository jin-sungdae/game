package dev.luma.game;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
@SpringBootTest
class SkillCommandIntegrationTest {
 @DynamicPropertySource static void database(DynamicPropertyRegistry r){GameIntegrationTest.database(r);}
 @Autowired JdbcTemplate db;@Autowired BattleService battles;@Autowired GameService game;@Autowired SkillCommandService commands;@Autowired SkillStateStore states;
 @BeforeEach void clean(){db.update("DELETE FROM game.t_command_receipt");db.update("DELETE FROM game.t_reward");db.update("DELETE FROM game.t_battle");db.update("DELETE FROM game.t_encounter");db.update("UPDATE game.m_monster SET use_yn=(code='PIP')");db.update("UPDATE game.t_player_companion SET level=1,evolution_stage=1");}
 UUID battle(){UUID id=UUID.randomUUID();db.update("INSERT INTO game.t_encounter(encounter_id,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at) SELECT ?,1,monster_id,1,rarity,'ACTIVE',clock_timestamp(),clock_timestamp()+interval '60 seconds' FROM game.m_monster WHERE code='PIP'",id);return battles.start(id).battleId();}
 @Test void replayPersistsCooldownAndDoesNotRepeatTurn(){var id=battle();var request=new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",0);var first=commands.execute(id,request);assertEquals(first,commands.execute(id,request));assertEquals(1,battles.get(id).turn());assertEquals(3,states.load(id).ready.get("MOA_S1"));assertThrows(GameFault.class,()->commands.execute(id,new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",1)));assertEquals(1,battles.get(id).turn());}
 @Test void staleLockedPassiveAndConceptCommandsDoNotMutate(){var id=battle();for(String code:List.of("MOA_S5","MOA_S1_PASSIVE","M001_ACTIVE","RUU_S1")){assertThrows(GameFault.class,()->commands.execute(id,new SkillCommandService.Request(UUID.randomUUID(),code,0)));}assertEquals(0,battles.get(id).turn());assertNull(states.load(id));assertThrows(GameFault.class,()->commands.execute(id,new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",1)));}
 @Test void requestIdCannotChangeMeaning(){var id=battle();var command=UUID.randomUUID();commands.execute(id,new SkillCommandService.Request(command,"MOA_S1",0));assertThrows(GameFault.class,()->commands.execute(id,new SkillCommandService.Request(command,"MOA_S2",0)));}
 @Test void cooldownAdvancesOnNormalActionsAndRewardRemainsOnce(){var id=battle();commands.execute(id,new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",0));battles.attack(id);battles.attack(id);commands.execute(id,new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",3));battles.attack(id);assertEquals("VICTORY",battles.get(id).status());assertEquals(1,db.queryForObject("SELECT count(*) FROM game.t_reward",Integer.class));}
 @Test void concurrentSameCommandCommitsOneTurn()throws Exception{var id=battle();var request=new SkillCommandService.Request(UUID.randomUUID(),"MOA_S1",0);try(var pool=Executors.newFixedThreadPool(2)){var gate=new CountDownLatch(1);Callable<String> job=()->{gate.await();return commands.execute(id,request).body();};var a=pool.submit(job);var b=pool.submit(job);gate.countDown();assertEquals(a.get(10,TimeUnit.SECONDS),b.get(10,TimeUnit.SECONDS));}assertEquals(1,battles.get(id).turn());}
}
