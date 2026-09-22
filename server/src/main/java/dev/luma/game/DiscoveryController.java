package dev.luma.game;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class DiscoveryController {
    private final DiscoveryService service;
    public DiscoveryController(DiscoveryService service){this.service=service;}
    @PostMapping("/monsters/{code}/discoveries")
    public DiscoveryService.Entry discover(@PathVariable String code,@RequestBody DiscoveryService.Request body,HttpServletRequest request){
        if(!request.getParameterMap().isEmpty() || body==null)throw new GameFault(400,"INVALID_REQUEST");
        return service.discover(code,body.encounterId());
    }
    @GetMapping("/dex") public List<DiscoveryService.Entry> dex(){return service.dex();}
}
