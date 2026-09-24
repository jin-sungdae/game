package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/companions/active")
public class CompanionInteractionController {
    private final CompanionInteractionService service;
    public CompanionInteractionController(CompanionInteractionService service) {this.service=service;}
    @PostMapping("/interact")
    public CompanionInteractionService.Result interact(@RequestBody(required=false) String body,HttpServletRequest request) {
        if((body!=null && !body.isBlank()) || !request.getParameterMap().isEmpty())
            throw new GameFault(400,"NO_INTERACTION_FIELDS_ACCEPTED");
        return service.interact();
    }
}
