package dev.luma.game;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.luma.game.command.*;
import org.springframework.stereotype.Service;
import java.util.*;
@Service
public class SkillCommandService {
    public record Request(UUID commandId,String skillCode,int expectedTurn) {}
    public record Phase(String phase,int durationMs) {}
    public record Cue(UUID commandId,String skillCode,String species,String castMotion,String element,String assetStatus,List<Phase> phases) {}
    public record Result(BattleDtos.Battle battle,Cue cue) {}
    private final CommandReceiptExecutor receipts; private final BattleService battles; private final ObjectMapper json;
    public SkillCommandService(CommandReceiptExecutor receipts,BattleService battles,ObjectMapper json){this.receipts=receipts;this.battles=battles;this.json=json;}
    private String encode(Object value){try{return json.writeValueAsString(value);}catch(Exception ex){throw new GameUnavailable("Skill result serialization failed");}}
    public CommandResponse execute(UUID id,Request request){
        if(request==null||request.commandId()==null||request.commandId().equals(new UUID(0,0))||request.skillCode()==null||request.skillCode().length()>80||request.expectedTurn()<0)
            throw new GameFault(400,"INVALID_SKILL_COMMAND");
        return receipts.execute(new CommandRequest(1,request.commandId(),"SKILL",id.toString(),encode(request)),()->{
            var entry=SkillCatalog.find(request.skillCode()).orElseThrow(()->new GameFault(404,"UNKNOWN_SKILL"));
            var battle=battles.skill(id,entry,request.expectedTurn());
            var cue=new Cue(request.commandId(),request.skillCode(),entry.definition().speciesCode(),entry.castMotion(),entry.element(),entry.assetStatus(),
                List.of(new Phase("CAST_START",120),new Phase("CHARGE",240),new Phase("RELEASE",120),new Phase(entry.delivery(),240),new Phase("IMPACT",160),new Phase("RECOVERY",240)));
            return new CommandResponse(200,encode(new Result(battle,cue)),1);
        });
    }
}
