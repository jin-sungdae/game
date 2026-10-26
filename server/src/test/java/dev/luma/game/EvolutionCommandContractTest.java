package dev.luma.game;

import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import static org.junit.jupiter.api.Assertions.*;

/** Production wiring intentionally has no Selection Revision provider. */
@SpringBootTest(webEnvironment=SpringBootTest.WebEnvironment.RANDOM_PORT)
class EvolutionCommandContractTest {
    @DynamicPropertySource static void database(DynamicPropertyRegistry r) { GameIntegrationTest.database(r); }
    @Autowired TestRestTemplate http; @Autowired JdbcTemplate db; @Autowired EvolutionCommandService commands;
    @LocalServerPort int port;
    long companion;
    String url(){return "http://127.0.0.1:"+port+"/api/v1/companions/active/evolve";}
    @BeforeEach void setup(){clean();companion=db.queryForObject("SELECT player_companion_id FROM game.t_player_companion WHERE player_id=1 AND active",Long.class);db.update("UPDATE game.t_player_companion SET level=6,exp=1500,bond=12");}
    @AfterEach void clean(){db.update("DELETE FROM game.t_command_receipt");CompanionBondIntegrationTest.clean(db);}
    @Test void missingSwitchingProviderFailsClosedButBodylessCompatibilityRemains() {
        var response=http.postForEntity(url(),new EvolutionCommandRequest(UUID.randomUUID(),companion,1,0),String.class);
        assertEquals(503,response.getStatusCode().value());assertTrue(response.getBody().contains("BLOCKED_BY_SWITCHING_CONTRACT"));
        assertEquals(1,db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE player_companion_id=?",Integer.class,companion));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history",Integer.class));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
        assertEquals(200,http.postForEntity(url(),null,String.class).getStatusCode().value());
        assertEquals(2,db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE player_companion_id=?",Integer.class,companion));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
    }
    @Test void expandedTransitionsCannotBypassReceiptOrSelectionThroughBodylessApi() {
        try {
            for(String species:List.of("MOA","RUU","NOX")) {
                int stage=species.equals("MOA")?3:1;
                db.update("UPDATE game.t_player_companion SET species_id=(SELECT species_id FROM game.m_species WHERE code=?),evolution_stage=?,level=100,exp=88900,bond=100",species,stage);
                var legacy=http.postForEntity(url(),null,String.class);
                assertEquals(409,legacy.getStatusCode().value());assertTrue(legacy.getBody().contains("EVOLUTION_COMMAND_REQUIRED"));
                var command=http.postForEntity(url(),new EvolutionCommandRequest(UUID.randomUUID(),companion,stage,0),String.class);
                assertEquals(503,command.getStatusCode().value());assertTrue(command.getBody().contains("BLOCKED_BY_SWITCHING_CONTRACT"));
                assertEquals(stage,db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE active",Integer.class));
            }
            assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_companion_evolution_history",Integer.class));
            assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
        } finally {db.update("UPDATE game.t_player_companion SET species_id=(SELECT species_id FROM game.m_species WHERE code='MOA'),evolution_stage=1");}
    }
    @Test void strictRequestParsingRejectsIncompleteAmbiguousAndOutOfRangePayloads() {
        String valid="{\"commandId\":\""+UUID.randomUUID()+"\",\"expectedCompanionId\":"+companion+",\"expectedStage\":1,\"expectedSelectionRevision\":0}";
        for(String body:List.of("{}","null","[]",valid+" {}",valid.replace("\"expectedStage\":1","\"expectedStage\":1,\"expectedStage\":2"),
            valid.replace("\"expectedStage\":1","\"expectedStage\":1.0"),valid.replace("\"expectedStage\":1","\"expectedStage\":null"),
            valid.replace("\"expectedStage\":1","\"expectedStage\":6"),valid.replace("\"expectedSelectionRevision\":0","\"expectedSelectionRevision\":-1"),
            valid.replace("\"expectedSelectionRevision\":0","\"expectedSelectionRevision\":9223372036854775808"),
            valid.replace("}",",\"extra\":true}"))) {
            var response=http.postForEntity(url(),body,String.class);assertEquals(400,response.getStatusCode().value(),body);
            assertTrue(response.getBody().contains("INVALID_EVOLUTION_COMMAND"));
        }
        assertEquals(400,http.postForEntity(url()+"?stage=2",valid,String.class).getStatusCode().value());
        assertEquals(1,db.queryForObject("SELECT evolution_stage FROM game.t_player_companion WHERE player_companion_id=?",Integer.class,companion));
        assertEquals(0,db.queryForObject("SELECT count(*) FROM game.t_command_receipt",Integer.class));
    }
    @Test void identityNormalizationAcceptsUuidCaseAndJsonFieldOrder() {
        UUID id=UUID.randomUUID();
        var a=commands.parse("{\"expectedStage\":1,\"expectedSelectionRevision\":0,\"expectedCompanionId\":"+companion+",\"commandId\":\""+id.toString().toUpperCase(Locale.ROOT)+"\"}");
        assertEquals(new EvolutionCommandRequest(id,companion,1,0),a);
    }
}
