package dev.luma.game.command;

import dev.luma.game.GameFault;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.net.URLClassLoader;
import java.nio.file.Path;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.UnexpectedRollbackException;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class CommandReceiptIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry registry) {
        String url = System.getenv().getOrDefault("LUMA_TEST_DB_URL", "jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if (!url.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?")) throw new IllegalStateException("Test database required");
        registry.add("spring.datasource.url", () -> url);
        registry.add("spring.datasource.username", () -> System.getenv().getOrDefault("LUMA_TEST_DB_USER", "luma"));
        registry.add("spring.datasource.password", () -> System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD", ""));
    }
    @Autowired JdbcTemplate db;
    @Autowired CommandReceiptExecutor executor;
    @Autowired PlatformTransactionManager manager;
    @Autowired FaultCaller faultCaller;
    private final List<Long> players = new ArrayList<>();
    private long player;
    @BeforeEach void setup() { player = newPlayer(); }
    long newPlayer() {
        long id = db.queryForObject("INSERT INTO game.t_player(player_name) VALUES (?) RETURNING player_id", Long.class, "receipt-"+UUID.randomUUID());
        players.add(id); return id;
    }
    @AfterEach void cleanup() {
        for (long id : players) {
            db.update("DELETE FROM game.t_command_receipt WHERE player_id=?", id);
            db.update("DELETE FROM game.t_player WHERE player_id=?", id);
        }
    }
    CommandRequest request(UUID id, String json) { return new CommandRequest(player,id,"TEST_MUTATION","fixture",json); }
    CommandRequest request() { return request(UUID.randomUUID(),"{}"); }
    long gold(long id) { return db.queryForObject("SELECT gold FROM game.t_player WHERE player_id=?",Long.class,id); }
    long count() { return db.queryForObject("SELECT count(*) FROM game.t_command_receipt WHERE player_id=?",Long.class,player); }
    CommandResponse mutate(long id) {
        db.update("UPDATE game.t_player SET gold=gold+1 WHERE player_id=?",id);
        return new CommandResponse(201,"{ \"value\": 1 }",1);
    }
    @Test void sameCommandReplaysOriginalResponseAndSchema() {
        var r=request(UUID.randomUUID(),"{\"b\":2,\"a\":1}");
        var original=executor.execute(r,()->mutate(player));
        var replay=executor.execute(request(r.commandId(),"{\"a\":1.0,\"b\":2}"),()->new CommandResponse(202,"{}",2));
        assertEquals(original,replay); assertEquals(1,gold(player)); assertEquals(1,count());
        assertNotNull(db.queryForObject("SELECT created_at FROM game.t_command_receipt WHERE player_id=?",java.time.OffsetDateTime.class,player));
    }
    @Test void reusedPayloadTypeAndTargetAreRejected() {
        var r=request(); executor.execute(r,()->mutate(player));
        var changed=List.of(request(r.commandId(),"{\"revision\":1}"),
            new CommandRequest(player,r.commandId(),"OTHER_COMMAND","fixture","{}"),
            new CommandRequest(player,r.commandId(),"TEST_MUTATION","other","{}"));
        for(var next:changed) assertEquals("COMMAND_ID_REUSED",assertThrows(GameFault.class,
            ()->executor.execute(next,()->{throw new AssertionError("must not mutate");})).getMessage());
        assertEquals(1,gold(player)); assertEquals(1,count());
    }
    @Test void sameIdDifferentPlayersAndNewIntent() {
        var r=request(); long second=newPlayer();
        executor.execute(r,()->mutate(player));
        executor.execute(new CommandRequest(second,r.commandId(),r.commandType(),r.targetId(),r.requestJson()),()->mutate(second));
        executor.execute(request(),()->mutate(player));
        assertEquals(2,gold(player));assertEquals(1,gold(second));
    }
    @Test void concurrentSameCommandExecutesOnce() throws Exception {
        var r=request();var calls=new AtomicInteger();var start=new CountDownLatch(1);
        try(var pool=Executors.newFixedThreadPool(4)) {
            var futures=new ArrayList<Future<CommandResponse>>();
            for(int i=0;i<4;i++) futures.add(pool.submit(()->{start.await();return executor.execute(r,()->{calls.incrementAndGet();return mutate(player);});}));
            start.countDown();
            for(var f:futures) assertEquals(new CommandResponse(201,"{ \"value\": 1 }",1),f.get(10,TimeUnit.SECONDS));
        }
        assertEquals(1,calls.get());assertEquals(1,gold(player));assertEquals(1,count());
    }
    @Test void concurrentDifferentPayloadOneWinner() throws Exception {
        var id=UUID.randomUUID();var start=new CountDownLatch(1);
        try(var pool=Executors.newFixedThreadPool(2)) {
            var futures=new ArrayList<Future<String>>();
            for(int i=0;i<2;i++) {int n=i;futures.add(pool.submit(()->{start.await();try {
                executor.execute(request(id,"{\"n\":"+n+"}"),()->mutate(player));return "OK";
            } catch(GameFault ex){return ex.getMessage();}}));}
            start.countDown();var results=new HashSet<String>();for(var f:futures)results.add(f.get(10,TimeUnit.SECONDS));
            assertEquals(Set.of("OK","COMMAND_ID_REUSED"),results);
        }
        assertEquals(1,gold(player));assertEquals(1,count());
    }
    @Test void mutationFailureAndInvalidResponseRollback() {
        var r=request();
        assertThrows(GameFault.class,()->executor.execute(r,()->{mutate(player);throw new GameFault(409,"TEST_FAILURE");}));
        assertEquals(0,gold(player));assertEquals(0,count());
        assertThrows(IllegalArgumentException.class,()->executor.execute(r,()->{mutate(player);return new CommandResponse(200,"not-json",1);}));
        assertEquals(0,gold(player));assertEquals(0,count());
        executor.execute(r,()->mutate(player));assertEquals(1,gold(player));
    }
    @Test void receiptInsertFailureRollsBackMutationAndReceipt() {
        var r=request();
        assertThrows(org.springframework.dao.DuplicateKeyException.class,()->executor.execute(r,()->{
            mutate(player);
            db.update("INSERT INTO game.t_command_receipt(player_id,command_id,command_type,target_id,request_fingerprint,response_status,response_body,response_schema_version) VALUES (?,?,'TEST_MUTATION','fixture',?,200,'{}',1)",player,r.commandId(),"0".repeat(64));
            return new CommandResponse(200,"{}",1);
        }));
        assertEquals(0,gold(player));assertEquals(0,count());
    }
    @Test void outerRollbackRemovesBothAndCaughtFailureCannotCommit() {
        var r=request();var tx=new TransactionTemplate(manager);
        tx.executeWithoutResult(status->{executor.execute(r,()->mutate(player));status.setRollbackOnly();});
        assertEquals(0,gold(player));assertEquals(0,count());
        assertThrows(UnexpectedRollbackException.class,()->tx.executeWithoutResult(status->{
            try {executor.execute(r,()->{mutate(player);throw new GameFault(409,"FAIL");});}catch(GameFault ignored){}
        }));
        assertEquals(0,gold(player));assertEquals(0,count());
    }
    @Test void callerNoRollbackForCannotCommitFailedMutation() {
        assertThrows(UnexpectedRollbackException.class,()->faultCaller.fail(request()));
        assertEquals(0,gold(player));assertEquals(0,count());
    }
    @Test void readOnlyTransactionRejectsCallback() {
        var tx=new TransactionTemplate(manager);tx.setReadOnly(true);
        assertThrows(IllegalStateException.class,()->tx.execute(status->executor.execute(request(),()->{throw new AssertionError();})));
        assertEquals(0,count());
    }
    @Test void strongerIsolationFailsBeforeMutation() {
        var tx=new TransactionTemplate(manager);
        tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_REPEATABLE_READ);
        assertThrows(IllegalStateException.class,()->tx.execute(status->executor.execute(request(),()->{throw new AssertionError();})));
        assertEquals(0,count());
    }
    @Test void newExecutorReplaysStoredVersionWithoutDomainCode() {
        var r=request();var response=executor.execute(r,()->new CommandResponse(409,"{\"code\":\"TEST_DOMAIN_REJECTION\"}",7));
        var fresh=new CommandReceiptExecutor(db,manager);
        assertEquals(response,fresh.execute(r,()->{throw new AssertionError();}));
    }
    @Test void processRestartReplaysDurableResponse() throws Exception {
        var id=UUID.randomUUID();
        var entries=new LinkedHashSet<String>(Arrays.asList(System.getProperty("java.class.path").split(java.io.File.pathSeparator)));
        for(ClassLoader loader=getClass().getClassLoader();loader!=null;loader=loader.getParent())
            if(loader instanceof URLClassLoader urls)for(var url:urls.getURLs())entries.add(Path.of(url.toURI()).toString());
        String cp=String.join(java.io.File.pathSeparator,entries);
        for(String mode:List.of("write","replay")) {
            var process=new ProcessBuilder(Path.of(System.getProperty("java.home"),"bin","java").toString(),"-cp",cp,
                CommandReceiptProcess.class.getName(),Long.toString(player),id.toString(),mode).redirectErrorStream(true).start();
            try {
                assertTrue(process.waitFor(20,TimeUnit.SECONDS),"process timeout");
                String output=new String(process.getInputStream().readAllBytes(),java.nio.charset.StandardCharsets.UTF_8);
                assertEquals(0,process.exitValue(),output);assertTrue(output.contains("RECEIPT_PROCESS_OK"),output);
            } finally {if(process.isAlive())process.destroyForcibly();}
        }
        assertEquals(7,gold(player));assertEquals(1,count());
    }
    @TestConfiguration static class Config {
        @Bean FaultCaller faultCaller(CommandReceiptExecutor executor,JdbcTemplate db){return new FaultCaller(executor,db);}
    }
    public static class FaultCaller {
        private final CommandReceiptExecutor executor;private final JdbcTemplate db;
        public FaultCaller(CommandReceiptExecutor executor,JdbcTemplate db){this.executor=executor;this.db=db;}
        @Transactional(noRollbackFor=GameFault.class)
        public void fail(CommandRequest request) {
            executor.execute(request,()->{
                db.update("UPDATE game.t_player SET gold=gold+1 WHERE player_id=?",request.playerId());
                throw new GameFault(409,"FAIL_AFTER_MUTATION");
            });
        }
    }
}
