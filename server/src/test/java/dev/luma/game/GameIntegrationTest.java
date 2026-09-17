package dev.luma.game;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.dao.DataIntegrityViolationException;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.*;
import java.time.Duration;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class GameIntegrationTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry registry) {
        String url=System.getenv().getOrDefault("LUMA_TEST_DB_URL","jdbc:postgresql://127.0.0.1:55439/luma_game_test");
        if(!url.matches("jdbc:postgresql://[^/]+/[^/?]+_test(\\?.*)?")) throw new IllegalStateException("Integration tests require a dedicated *_test database");
        registry.add("spring.datasource.url",()->url);
        registry.add("spring.datasource.username",()->System.getenv().getOrDefault("LUMA_TEST_DB_USER","luma"));
        registry.add("spring.datasource.password",()->System.getenv().getOrDefault("LUMA_TEST_DB_PASSWORD",""));
    }
    @Autowired TestRestTemplate http;
    @Autowired JdbcTemplate jdbc;
    @LocalServerPort int port;
    String url(String path) {return "http://127.0.0.1:"+port+"/api/v1"+path;}
    @BeforeEach void reset() {
        jdbc.update("DELETE FROM game.t_encounter");
        jdbc.update("UPDATE game.m_monster SET use_yn=true");
        jdbc.update("UPDATE game.t_player_companion SET active=true WHERE player_id=1");
    }
    GameDtos.Encounter create() {
        var response=http.postForEntity(url("/encounters"),null,GameDtos.Encounter.class);
        assertEquals(HttpStatus.OK,response.getStatusCode());return response.getBody();
    }
    void expire() {
        jdbc.update("UPDATE game.t_encounter SET spawned_at=clock_timestamp()-interval '61 seconds', expires_at=clock_timestamp()-interval '1 second'");
    }
    @Test void bootstrapAndSeeds() {
        var response=http.getForEntity(url("/game/bootstrap"),GameDtos.Bootstrap.class);
        assertEquals(HttpStatus.OK,response.getStatusCode());var b=response.getBody();
        assertEquals(new GameDtos.Player(1,"LOCAL_PLAYER",0),b.player());
        assertEquals("MOA",b.activeCompanion().species());assertEquals(1,b.activeCompanion().evolutionStage());
        assertEquals("MOA",b.activeCompanion().evolutionName());assertEquals(1,b.activeCompanion().level());
        assertEquals(0,b.activeCompanion().exp());assertEquals(0,b.activeCompanion().bond());
        assertEquals(3,jdbc.queryForObject("SELECT count(*) FROM game.m_species",Integer.class));
        assertEquals(java.util.List.of("MOA","MOKORI","NEBLA","SYLVAON","AETHERIA"),jdbc.queryForList("SELECT e.name FROM game.m_species_evolution e JOIN game.m_species s USING(species_id) WHERE s.code='MOA' ORDER BY evolution_stage",String.class));
        assertEquals(2,jdbc.queryForObject("SELECT count(*) FROM game.m_species_evolution e JOIN game.m_species s USING(species_id) WHERE s.code IN ('RUU','NOX')",Integer.class));
    }
    @Test void createReuseAndTtl() {
        var first=create();var second=create();assertEquals(first,second);
        assertEquals("PIP",first.monster().code());assertEquals("COMMON",first.monster().rarity());
        assertEquals("GROUND",first.monster().movementProfile());assertTrue(first.monster().level()>=1&&first.monster().level()<=3);
        assertEquals(Duration.ofSeconds(60),Duration.between(first.spawnedAt(),first.expiresAt()));
        assertEquals(first,http.getForObject(url("/encounters/active"),GameDtos.Encounter.class));
    }
    @Test void lazyExpirationOnGetAndReplacement() {
        var first=create();expire();
        assertEquals(HttpStatus.NO_CONTENT,http.getForEntity(url("/encounters/active"),String.class).getStatusCode());
        assertEquals("EXPIRED",jdbc.queryForObject("SELECT status FROM game.t_encounter WHERE encounter_id=?",String.class,first.encounterId()));
        assertNotNull(jdbc.queryForObject("SELECT resolved_at FROM game.t_encounter WHERE encounter_id=?",java.time.OffsetDateTime.class,first.encounterId()));
        assertNotEquals(first.encounterId(),create().encounterId());
    }
    @Test void lazyExpirationOnPost() {
        var first=create();expire();assertNotEquals(first.encounterId(),create().encounterId());
        assertEquals(1,jdbc.queryForObject("SELECT count(*) FROM game.t_encounter WHERE status='ACTIVE'",Integer.class));
    }
    @Test void concurrentPostsReturnSameActive() throws Exception {
        try(var pool=Executors.newFixedThreadPool(2)) {
            var gate=new CountDownLatch(1);
            Callable<GameDtos.Encounter> request=()->{gate.await();return create();};
            var one=pool.submit(request);var two=pool.submit(request);gate.countDown();
            assertEquals(one.get(10,TimeUnit.SECONDS).encounterId(),two.get(10,TimeUnit.SECONDS).encounterId());
        }
        assertEquals(1,jdbc.queryForObject("SELECT count(*) FROM game.t_encounter WHERE status='ACTIVE'",Integer.class));
    }
    @Test void dbConstraintsRejectSecondActiveAndInvalidForeignKey() {
        var e=create();
        assertThrows(DataIntegrityViolationException.class,()->jdbc.update("INSERT INTO game.t_encounter SELECT ?,player_id,monster_id,monster_level,rarity,status,spawned_at,expires_at,resolved_at,created_at,updated_at FROM game.t_encounter WHERE encounter_id=?",UUID.randomUUID(),e.encounterId()));
        assertThrows(DataIntegrityViolationException.class,()->jdbc.update("INSERT INTO game.t_player_companion(player_id,species_id,evolution_stage,active) SELECT player_id,species_id,evolution_stage,true FROM game.t_player_companion WHERE active"));
        assertThrows(DataIntegrityViolationException.class,()->jdbc.update("UPDATE game.t_player_companion SET evolution_stage=99 WHERE player_id=1"));
    }
    @Test void invalidDbStateIsUnavailableWithoutInventingData() {
        jdbc.update("UPDATE game.m_monster SET use_yn=false");
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,http.postForEntity(url("/encounters"),null,String.class).getStatusCode());
        assertEquals(0,jdbc.queryForObject("SELECT count(*) FROM game.t_encounter",Integer.class));
        jdbc.update("UPDATE game.t_player_companion SET active=false");
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE,http.getForEntity(url("/game/bootstrap"),String.class).getStatusCode());
    }
    @Test void clientCannotSelectMonsterOrSupplyLifecycleFields() {
        for(String field:java.util.List.of("monster","rarity","monsterLevel","encounterId","expiresAt","playerId"))
            assertEquals(HttpStatus.BAD_REQUEST,http.postForEntity(url("/encounters"),Map.of(field,"injected"),String.class).getStatusCode());
        assertEquals(HttpStatus.BAD_REQUEST,http.postForEntity(url("/encounters?monster=PIP"),null,String.class).getStatusCode());
    }
    @Test void browserOriginCannotTriggerLocalEncounter() {
        var headers=new HttpHeaders();headers.set("Origin","https://example.com");
        assertEquals(HttpStatus.FORBIDDEN,http.exchange(url("/encounters"),HttpMethod.POST,new HttpEntity<Void>(null,headers),String.class).getStatusCode());
    }
}
