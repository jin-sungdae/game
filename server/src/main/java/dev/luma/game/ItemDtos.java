package dev.luma.game;
import java.util.*;
public final class ItemDtos {
    private ItemDtos() {}
    public record ShopItem(String itemCode,String itemName,String itemType,long price,int ownedQuantity,int maxStack) {}
    public record Owned(String itemCode,String itemName,String itemType,int quantity) {}
    public record PurchaseRequest(String itemCode,Integer quantity) {}
    public record UseRequest(UUID battleId) {}
    public record Purchase(UUID purchaseId,String itemCode,int quantity,long unitPrice,long totalPrice,long goldAfter,int remainingQuantity) {}
    public record Use(String itemCode,int remainingQuantity,Integer healedAmount,Integer currentHp,Integer maxHp,
                      Integer bondBefore,Integer bondAfter,Boolean armed,Double bonus,UUID battleId) {}
    public record Effect(UUID battleId,String effectType,double value,boolean armed,java.time.Instant consumedAt) {}
}
