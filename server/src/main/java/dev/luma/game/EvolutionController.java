package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/companions/active")
public class EvolutionController {
    private final EvolutionService service;
    public EvolutionController(EvolutionService service) { this.service=service; }
    @GetMapping("/evolution") public EvolutionDtos.Status status() { return service.status(); }
    @PostMapping("/evolve") public EvolutionDtos.Result evolve(
            @RequestBody(required=false) String body, HttpServletRequest request) {
        if ((body!=null && !body.isBlank()) || !request.getParameterMap().isEmpty())
            throw new GameFault(400,"NO_EVOLUTION_FIELDS_ACCEPTED");
        return service.evolve();
    }
}
