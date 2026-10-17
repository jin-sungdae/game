package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/companions")
public class CompanionOwnershipController {
    private final CompanionOwnershipService service;
    public CompanionOwnershipController(CompanionOwnershipService service) { this.service = service; }
    @GetMapping
    public CompanionOwnershipDtos.Ownership owned(HttpServletRequest request) {
        if (!request.getParameterMap().isEmpty()) throw new GameFault(400,"NO_OWNERSHIP_FIELDS_ACCEPTED");
        return service.owned();
    }
}
