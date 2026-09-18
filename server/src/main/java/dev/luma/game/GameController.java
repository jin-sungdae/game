package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class GameController {
    private final GameService service;
    public GameController(GameService service) {this.service=service;}
    @GetMapping("/game/bootstrap") public GameDtos.Bootstrap bootstrap() {return service.bootstrap();}
    @PostMapping("/encounters") public GameDtos.Encounter create(@RequestBody(required=false) Map<String,Object> body,HttpServletRequest request) {
        if((body!=null&&!body.isEmpty()) || !request.getParameterMap().isEmpty())
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Encounter is selected by server; no fields accepted");
        return service.createEncounter();
    }
    @GetMapping("/encounters/active") public ResponseEntity<GameDtos.Encounter> active() {
        return service.activeEncounter().map(ResponseEntity::ok).orElseGet(()->ResponseEntity.noContent().build());
    }
}
