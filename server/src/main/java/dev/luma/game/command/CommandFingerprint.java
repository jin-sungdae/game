package dev.luma.game.command;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.DeserializationFeature;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.TreeSet;

/** Version 1: sorted object keys, ordered arrays, exact decimal normalization.
 * Missing and null differ; strings are not trimmed or Unicode-normalized.
 * Duplicate keys and trailing JSON are rejected. Keep v1 stable for stored receipts.
 */
final class CommandFingerprint {
    private static final ObjectMapper JSON = new ObjectMapper()
        .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
        .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
        .enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS)
        .enable(DeserializationFeature.USE_BIG_INTEGER_FOR_INTS);
    private CommandFingerprint() {}

    static JsonNode parse(String json) {
        try {
            JsonNode node = JSON.readTree(json);
            if (node == null || node.isMissingNode()) throw new IllegalArgumentException("Empty JSON");
            validateUnicode(node);
            return node;
        } catch (java.io.IOException ex) {
            throw new IllegalArgumentException("Invalid command JSON", ex);
        }
    }
    private static void validateUnicode(JsonNode node) {
        if (node.isTextual()) validateString(node.textValue());
        if (node.isObject()) node.fieldNames().forEachRemaining(CommandFingerprint::validateString);
        if (node.isContainerNode()) node.forEach(CommandFingerprint::validateUnicode);
    }
    private static void validateString(String value) {
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (Character.isHighSurrogate(c)) {
                if (++i >= value.length() || !Character.isLowSurrogate(value.charAt(i)))
                    throw new IllegalArgumentException("Unpaired JSON surrogate");
            } else if (Character.isLowSurrogate(c)) {
                throw new IllegalArgumentException("Unpaired JSON surrogate");
            }
        }
    }
    static String of(CommandRequest request) {
        var envelope = JSON.createObjectNode();
        envelope.put("fingerprintVersion", 1);
        envelope.put("commandType", request.commandType());
        envelope.put("targetId", request.targetId());
        envelope.set("payload", parse(request.requestJson()));
        validateUnicode(envelope);
        var canonical = new StringBuilder();
        append(envelope, canonical);
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(canonical.toString().getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) { throw new IllegalStateException(ex); }
    }
    private static void append(JsonNode node, StringBuilder out) {
        if (node.isObject()) {
            out.append('{');
            var keys = new TreeSet<String>();
            node.fieldNames().forEachRemaining(keys::add);
            boolean first = true;
            for (String key : keys) {
                if (!first) out.append(',');
                first = false;
                out.append(JSON.getNodeFactory().textNode(key)).append(':');
                append(node.get(key), out);
            }
            out.append('}');
        } else if (node.isArray()) {
            out.append('[');
            for (int i = 0; i < node.size(); i++) {
                if (i > 0) out.append(',');
                append(node.get(i), out);
            }
            out.append(']');
        } else if (node.isNumber()) {
            out.append(node.decimalValue().stripTrailingZeros().toString());
        } else { out.append(node); }
    }
}
