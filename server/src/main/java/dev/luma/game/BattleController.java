package dev.luma.game;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@RestController
@RequestMapping("/api/v1")
public class BattleController {
    private final BattleService service;
    public BattleController(BattleService service) {this.service=service;}
    private void empty(Map<String,Object> body,HttpServletRequest request) {
        if((body!=null&&!body.isEmpty()) || !request.getParameterMap().isEmpty()) throw new GameFault(400,"INVALID_REQUEST");
    }
    @PostMapping("/encounters/{id}/battle") public BattleDtos.Battle start(@PathVariable UUID id,@RequestBody(required=false) Map<String,Object> body,HttpServletRequest r) {empty(body,r);return service.start(id);}
    @GetMapping("/battles/{id}") public BattleDtos.Battle get(@PathVariable UUID id) {return service.get(id);}
    @PostMapping("/battles/{id}/attack") public BattleDtos.Battle attack(@PathVariable UUID id,@RequestBody(required=false) Map<String,Object> body,HttpServletRequest r) {empty(body,r);return service.attack(id);}
    @PostMapping("/battles/{id}/capture") public BattleDtos.Capture capture(@PathVariable UUID id,@RequestBody(required=false) Map<String,Object> body,HttpServletRequest r) {empty(body,r);return service.capture(id);}
    @PostMapping("/encounters/{id}/ignore") public BattleDtos.Resolution ignore(@PathVariable UUID id,@RequestBody(required=false) Map<String,Object> body,HttpServletRequest r) {empty(body,r);return service.ignore(id);}
    @GetMapping("/collection") public List<BattleDtos.Collected> collection() {return service.collection();}
}
