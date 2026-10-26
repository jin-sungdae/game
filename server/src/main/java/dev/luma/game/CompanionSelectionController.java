package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/companions/selection")
public class CompanionSelectionController {
    private final CompanionSelectionService service;
    public CompanionSelectionController(CompanionSelectionService service) { this.service=service; }
    private void noQuery(HttpServletRequest request) {
        if (!request.getParameterMap().isEmpty()) throw new GameFault(400,"NO_SELECTION_QUERY_FIELDS_ACCEPTED");
    }
    @GetMapping public CompanionSelectionService.Snapshot current(HttpServletRequest request) {
        noQuery(request); return service.snapshot();
    }
    @PostMapping public ResponseEntity<String> select(@RequestBody String body,HttpServletRequest request) {
        noQuery(request);var result=service.select(service.parse(body));
        return ResponseEntity.status(result.status()).contentType(MediaType.APPLICATION_JSON)
            .header("X-Luma-Response-Schema-Version",Integer.toString(result.schemaVersion())).body(result.body());
    }
}
