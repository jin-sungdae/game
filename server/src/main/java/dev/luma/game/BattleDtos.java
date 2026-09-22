package dev.luma.game;
import java.util.*;
import java.time.Instant;
public final class BattleDtos {
    private BattleDtos() {}
    public record PresentationEvent(String type,int damage) {}
    public record Hp(int hp,int maxHp) {}
    public record Reward(long gold,long exp,int bond) {}
    public record Battle(UUID battleId,UUID encounterId,int turn,String status,String encounterStatus,
                         Hp companion,Hp monster,List<String> events,Reward reward,List<PresentationEvent> presentationEvents) {}
    public record Collected(String monsterCode,String monsterName,long captureCount,Instant firstCapturedAt,Instant lastCapturedAt) {}
    public record Monster(String code,String name) {}
    public record Capture(UUID battleId,UUID encounterId,boolean success,double chance,Monster monster,
                          String battleStatus,String encounterStatus,Collected collection,Battle battle,double baseChance,double itemBonus,double finalChance) {}
    public record Resolution(UUID encounterId,String encounterStatus) {}
}
