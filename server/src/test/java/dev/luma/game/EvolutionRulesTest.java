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
                assertEquals(java.util.Set.of("MOA","RUU","NOX").contains(species==null?"":species) && stage>=1 && stage<=4,rule.isPresent());
            }
        }
    }
    @Test void approvedBoundariesAndIdentityRemainExact() {
        int[] levels={3,6,30,60},bonds={5,12,40,80};
        for(String species:new String[]{"MOA","RUU","NOX"}) for(int stage=1;stage<=4;stage++) {
            var rule=EvolutionRules.next(companion(species,stage,1,0)).orElseThrow();
            assertEquals(new EvolutionRules.Rule(species,stage,stage+1,levels[stage-1],bonds[stage-1]),rule);
            assertTrue(rule.eligible(companion(species,stage,rule.requiredLevel(),rule.requiredBond())));
            assertFalse(rule.eligible(companion(species,stage,rule.requiredLevel()-1,rule.requiredBond())));
            assertFalse(rule.eligible(companion(species,stage,rule.requiredLevel(),rule.requiredBond()-1)));
            assertFalse(rule.eligible(companion("UNKNOWN",stage,100,100)));
            assertFalse(rule.eligible(companion(species,stage+1,100,100)));
        }
    }
}
