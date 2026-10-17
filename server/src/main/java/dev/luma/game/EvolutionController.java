package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

@RestController
@RequestMapping("/api/v1/companions/active")
public class EvolutionController {
    private final EvolutionService service;
    private final EvolutionCommandService commands;
    public EvolutionController(EvolutionService service, EvolutionCommandService commands) {
        this.service=service; this.commands=commands;
    }
    @GetMapping("/evolution") public EvolutionDtos.Status status() { return service.status(); }
    @PostMapping("/evolve") public ResponseEntity<?> evolve(
            @RequestBody(required=false) String body, HttpServletRequest request) {
        if (!request.getParameterMap().isEmpty()) throw new GameFault(400,"NO_EVOLUTION_FIELDS_ACCEPTED");
        // Compatibility only: old Desktop sends no identity and has no replay guarantee.
        if (body==null || body.isBlank()) return ResponseEntity.ok(service.evolve());
        var result=commands.execute(commands.parse(body));
        return ResponseEntity.status(result.status()).contentType(MediaType.APPLICATION_JSON)
            .header("X-Luma-Response-Schema-Version", Integer.toString(result.schemaVersion()))
            .body(result.body());
    }
}
