package dev.luma.game;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class EvolutionRulesTest {
    GameDtos.Companion companion(String species, int stage, int level, int bond) {
        return new GameDtos.Companion(42, species, stage, "fixture", level, 321, bond);
    }
    @Test void onlyApprovedSpeciesAndStagesResolve() {
        for(String species:new String[]{"MOA","RUU","NOX","UNKNOWN","moa","",null}) {
            for(int stage=-1;stage<=6;stage++) {
                var rule=EvolutionRules.next(companion(species,stage,100,100));
                assertEquals("MOA".equals(species) && (stage==1 || stage==2),rule.isPresent());
            }
        }
    }
    @Test void approvedBoundariesAndIdentityRemainExact() {
        for(var expected:new EvolutionRules.Rule[]{new EvolutionRules.Rule("MOA",1,2,3,5),new EvolutionRules.Rule("MOA",2,3,6,12)}) {
            var rule=EvolutionRules.next(companion("MOA",expected.fromStage(),1,0)).orElseThrow();
            assertEquals(expected,rule);
            assertTrue(rule.eligible(companion("MOA",rule.fromStage(),rule.requiredLevel(),rule.requiredBond())));
            assertFalse(rule.eligible(companion("MOA",rule.fromStage(),rule.requiredLevel()-1,rule.requiredBond())));
            assertFalse(rule.eligible(companion("MOA",rule.fromStage(),rule.requiredLevel(),rule.requiredBond()-1)));
            assertFalse(rule.eligible(companion("RUU",rule.fromStage(),100,100)));
            assertFalse(rule.eligible(companion("MOA",rule.toStage(),100,100)));
        }
    }
}
