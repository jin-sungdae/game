package dev.luma.game;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Cross-check the offline Python report against actual Java domain implementations. */
class ProgressionBondAnalysisTest {
    private JsonNode report() throws Exception {
        return new ObjectMapper().readTree(Path.of("../tests/fixtures/progression-bond-analysis.json").toFile());
    }
    @Test void generatedThresholdsAndTimelineUseProductionDomain() throws Exception {
        var report=report();
        assertEquals(CombatRules.MAX_LEVEL,report.get("thresholds").size());
        for(var row:report.get("thresholds"))
            assertEquals(CombatRules.levelThreshold(row.get("level").asInt()),row.get("exp").asLong());
        for(var row:report.get("timeline_fixed_level2")) {
            int wins=row.get("wins").asInt();long exp=wins*CombatRules.exp(2);
            assertEquals(exp,row.get("exp").asLong());
            assertEquals(wins*CombatRules.gold(2),row.get("gold").asLong());
            assertEquals(CombatRules.level(exp),row.get("level").asInt());
            for(int stage=1;stage<=2;stage++) {
                var c=new GameDtos.Companion(1,"MOA",stage,"analysis",CombatRules.level(exp),exp,wins);
                assertEquals(EvolutionRules.next(c).orElseThrow().eligible(c),
                    row.get(stage==1?"mokori_requirements_met":"nebla_requirements_met").asBoolean());
            }
        }
    }
    @Test void naturalGateBerryAndExactThresholdDistinction() {
        for(int monster=1;monster<=3;monster++) {
            long exp=0;int wins=0;
            while(CombatRules.level(exp)<6){exp+=CombatRules.exp(monster);wins++;}
            assertTrue(wins>=25 && wins<=75);
            var c=new GameDtos.Companion(1,"MOA",2,"MOKORI",6,exp,wins);
            assertTrue(EvolutionRules.next(c).orElseThrow().eligible(c));
        }
        // Explicit legacy/test state: this is NOT reachable from fresh production rewards.
        var before=new GameDtos.Companion(1,"MOA",2,"MOKORI",6,1500,11);
        var after=new GameDtos.Companion(1,"MOA",2,"MOKORI",6,1500,11+ItemRules.BERRY_BOND);
        assertFalse(EvolutionRules.next(before).orElseThrow().eligible(before));
        assertTrue(EvolutionRules.next(after).orElseThrow().eligible(after));
        assertEquals(30,ItemRules.total(30,1));
        assertEquals(9,(500+CombatRules.exp(3)-1)/CombatRules.exp(3));
        assertEquals(8,(1500-1020+CombatRules.exp(3)-1)/CombatRules.exp(3));
    }
}
