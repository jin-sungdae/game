package dev.luma.game;
import org.springframework.web.bind.annotation.*;
import jakarta.servlet.http.HttpServletRequest;
import java.util.*;
@RestController
@RequestMapping("/api/v1")
public class ItemController {
    private final ItemService service;
    public ItemController(ItemService service) {this.service=service;}
    private void noQuery(HttpServletRequest request) {if(!request.getParameterMap().isEmpty()) throw new GameFault(400,"ITEM_NOT_USABLE");}
    @GetMapping("/shop/items") public List<ItemDtos.ShopItem> shop() {return service.shop();}
    @GetMapping("/inventory") public List<ItemDtos.Owned> inventory() {return service.inventory();}
    @PostMapping("/shop/purchases") public ItemDtos.Purchase purchase(@RequestBody ItemDtos.PurchaseRequest body,HttpServletRequest request) {noQuery(request);return service.purchase(body);}
    @PostMapping("/inventory/items/{code}/use") public ItemDtos.Use use(@PathVariable String code,@RequestBody(required=false) ItemDtos.UseRequest body,HttpServletRequest request) {noQuery(request);return service.use(code,body==null?null:body.battleId());}
    @GetMapping("/battles/{id}/item-effects") public List<ItemDtos.Effect> effects(@PathVariable UUID id) {return service.effects(id);}
}
