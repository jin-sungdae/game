package dev.luma.game;

import dev.luma.game.economy.*;
import static dev.luma.game.economy.EncounterIssuancePolicy.*;
import static dev.luma.game.economy.RewardEntitlement.*;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class EconomyPolicyTest {
    @Test void disabledDoesNotIntroduceCandidateDelay(){
        var policy=new EncounterIssuancePolicy(Mode.DISABLED,0);
        assertEquals(Action.LEGACY_UNCHANGED,policy.evaluate(new Snapshot(1,Instant.MAX,UUID.randomUUID()),Source.NATURAL,Instant.EPOCH).action());
        assertThrows(IllegalStateException.class,()->policy.deadlineAfterIssuance(Instant.EPOCH));
        assertThrows(IllegalArgumentException.class,()->new EncounterIssuancePolicy(Mode.SHARED_PLAYER_BUDGET,0));
    }
    @Test void activePrecedesDeadlineAndSourcesShareOnePlayerBudget(){
        var policy=new EncounterIssuancePolicy(Mode.SHARED_PLAYER_BUDGET,17); // test fixture, not production tuning
        var now=Instant.parse("2026-10-17T00:00:00Z");var id=UUID.randomUUID();
        var snapshot=new Snapshot(7,now.plusSeconds(17),id);
        for(var source:Source.values()){
            assertEquals(7,policy.budgetOwner(snapshot,source));
            assertEquals(new Decision(Action.REUSE_ACTIVE,id,snapshot.nextEligibleAt()),policy.evaluate(snapshot,source,now));
            assertEquals(Action.WAIT,policy.evaluate(new Snapshot(7,snapshot.nextEligibleAt(),null),source,now).action());
            assertEquals(Action.ELIGIBLE,policy.evaluate(new Snapshot(7,snapshot.nextEligibleAt(),null),source,snapshot.nextEligibleAt()).action());
        }
        assertEquals(now.plusSeconds(17),policy.deadlineAfterIssuance(now));
    }
    @Test void restoredSnapshotHasIdenticalDecisionWithoutLocalTimer(){
        var now=Instant.parse("2026-10-17T00:00:00Z");
        var saved=new Snapshot(1,now.plusSeconds(17),null);
        var before=new EncounterIssuancePolicy(Mode.SHARED_PLAYER_BUDGET,17);
        var after=new EncounterIssuancePolicy(Mode.SHARED_PLAYER_BUDGET,17);
        assertEquals(before.evaluate(saved,Source.NATURAL,now),after.evaluate(saved,Source.OBSERVATION_RESERVATION,now));
        assertEquals(Action.ELIGIBLE,after.evaluate(new Snapshot(1,null,null),Source.NATURAL,now).action());
    }
    @Test void keyShapeAndAmountsRejectAmbiguity(){
        assertThrows(IllegalArgumentException.class,()->Key.weekly(0,LocalDate.now(),"SLOT"));
        assertThrows(IllegalArgumentException.class,()->Key.collection(1,"ALPHA",Type.WEEKLY,1));
        assertThrows(IllegalArgumentException.class,()->Key.collection(1,"ALPHA",Type.COLLECTION_CAPTURE,0));
        assertThrows(IllegalArgumentException.class,()->new Terms("V1",-1,Map.of()));
        assertThrows(IllegalArgumentException.class,()->new Terms("V1",0,Map.of()));
        assertThrows(IllegalArgumentException.class,()->new Terms("V1",1,Map.of("SMALL_POTION",0)));
    }
}
