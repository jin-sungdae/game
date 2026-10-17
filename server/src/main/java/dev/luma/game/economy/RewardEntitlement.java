package dev.luma.game.economy;

import java.time.LocalDate;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Server-only entitlement identity, independent of policy version and command ID.
 * Weekly boundaries and eligibility are supplied by a future trusted domain policy.
 * First persisted terms win; changing a policy never creates another right.
 */
public record RewardEntitlement(UUID id, Key key, Terms terms) {
    public enum Type { WEEKLY, COLLECTION_DISCOVERY, COLLECTION_CAPTURE }

    public record Key(long playerId, Type type, LocalDate weekStart, String rewardSlot,
                      String campaignId, Long milestone) {
        public Key {
            if (playerId <= 0) throw new IllegalArgumentException("Invalid player");
            Objects.requireNonNull(type, "type");
            if (type == Type.WEEKLY) {
                Objects.requireNonNull(weekStart, "weekStart");
                token(rewardSlot, 64);
                if (campaignId != null || milestone != null) throw new IllegalArgumentException("Weekly key shape");
            } else {
                token(campaignId, 80);
                if (weekStart != null || rewardSlot != null || milestone == null || milestone <= 0)
                    throw new IllegalArgumentException("Collection key shape");
            }
        }
        public static Key weekly(long player, LocalDate week, String slot) {
            return new Key(player, Type.WEEKLY, week, slot, null, null);
        }
        public static Key collection(long player, String campaign, Type type, long milestone) {
            if (type == Type.WEEKLY) throw new IllegalArgumentException("Collection type required");
            return new Key(player, type, null, null, campaign, milestone);
        }
    }

    public record Terms(String policyVersion, long gold, Map<String, Integer> items) {
        public Terms {
            token(policyVersion, 64);
            if (gold < 0) throw new IllegalArgumentException("Negative gold");
            items = Map.copyOf(items);
            items.forEach((code, quantity) -> {
                token(code, 40);
                if (quantity <= 0) throw new IllegalArgumentException("Invalid quantity");
            });
            if (gold == 0 && items.isEmpty()) throw new IllegalArgumentException("Empty reward");
        }
    }

    public record Claim(UUID entitlementId, boolean granted, Terms terms) {}

    private static void token(String value, int max) {
        if (value == null || value.length() > max || !value.matches("[A-Z0-9][A-Z0-9_.-]*"))
            throw new IllegalArgumentException("Invalid stable policy identifier");
    }
}
