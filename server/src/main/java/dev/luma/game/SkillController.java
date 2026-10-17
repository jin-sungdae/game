package dev.luma.game;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import jakarta.servlet.http.HttpServletRequest;
import java.util.*;
@RestController
@RequestMapping("/api/v1")
public class SkillController {
    private final SkillCommandService skills;
    public SkillController(SkillCommandService skills){this.skills=skills;}
    @GetMapping("/skills/catalog") public List<SkillCatalog.Entry> catalog(){return SkillCatalog.all();}
    @PostMapping("/battles/{id}/skills") public ResponseEntity<String> cast(@PathVariable UUID id,@RequestBody Map<String,Object> body,HttpServletRequest request){
        if(!request.getParameterMap().isEmpty()||!body.keySet().equals(Set.of("commandId","skillCode","expectedTurn")))throw new GameFault(400,"INVALID_SKILL_COMMAND");
        SkillCommandService.Request command;
        try {
            if(!(body.get("commandId") instanceof String c)||!(body.get("skillCode") instanceof String skill)||!(body.get("expectedTurn") instanceof Integer turn))throw new IllegalArgumentException();
            UUID uuid=UUID.fromString(c);if(!uuid.toString().equalsIgnoreCase(c))throw new IllegalArgumentException();
            command=new SkillCommandService.Request(uuid,skill,turn);
        }catch(IllegalArgumentException ex){throw new GameFault(400,"INVALID_SKILL_COMMAND");}
        var result=skills.execute(id,command);
        return ResponseEntity.status(result.status()).contentType(MediaType.APPLICATION_JSON).body(result.body());
    }
}
