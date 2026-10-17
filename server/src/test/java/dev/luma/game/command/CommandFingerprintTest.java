package dev.luma.game.command;

import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CommandFingerprintTest {
    private CommandRequest request(String json) {
        return new CommandRequest(1, UUID.randomUUID(), "TEST_COMMAND", "target", json);
    }
    @Test void canonicalObjectsAndNumbersButOrderedArrays() {
        assertEquals(CommandFingerprint.of(request("{\"b\":[1,2],\"a\":1.00}")),
            CommandFingerprint.of(request("{ \"a\":1e0,\"b\":[1.0,2]}")));
        assertNotEquals(CommandFingerprint.of(request("[1,2]")), CommandFingerprint.of(request("[2,1]")));
    }
    @Test void nullMissingAndStringsAreDistinct() {
        assertNotEquals(CommandFingerprint.of(request("{}")), CommandFingerprint.of(request("{\"a\":null}")));
        assertNotEquals(CommandFingerprint.of(request("\" x\"")), CommandFingerprint.of(request("\"x\"")));
        assertNotEquals(CommandFingerprint.of(request("1")), CommandFingerprint.of(request("\"1\"")));
    }
    @Test void exactLargeNumbersAndNestedKeys() {
        assertNotEquals(CommandFingerprint.of(request("9007199254740992")),CommandFingerprint.of(request("9007199254740993")));
        assertEquals(CommandFingerprint.of(request("{\"a\":{\"z\":0,\"b\":2}}")),CommandFingerprint.of(request("{\"a\":{\"b\":2,\"z\":-0.0}}")));
    }
    @Test void rejectsAmbiguousOrInvalidJson() {
        for (String json : new String[]{"", "{", "{} {}", "{\"a\":1,\"a\":2}", "NaN"})
            assertThrows(IllegalArgumentException.class, () -> CommandFingerprint.of(request(json)));
    }
    @Test void malformedUnicodeCannotCollideWithReplacementCharacters() {
        String invalid = String.valueOf((char) 0xd800);
        assertThrows(IllegalArgumentException.class, () -> CommandFingerprint.of(request("\""+invalid+"\"")));
        assertThrows(IllegalArgumentException.class, () -> CommandFingerprint.of(request("{\""+invalid+"\":1}")));
        String valid = new String(Character.toChars(0x1f600));
        assertNotEquals(CommandFingerprint.of(request("\""+valid+"\"")),CommandFingerprint.of(request("\"?\"")));
    }
    @Test void identityValidationAndResponseVersion() {
        assertThrows(IllegalArgumentException.class, () -> new CommandRequest(0,UUID.randomUUID(),"TEST","x","{}"));
        assertThrows(IllegalArgumentException.class, () -> new CommandRequest(1,UUID.randomUUID(),"test","x","{}"));
        assertThrows(IllegalArgumentException.class, () -> new CommandResponse(200,"{}",0));
        assertThrows(IllegalArgumentException.class, () -> new CommandResponse(199,"{}",1));
    }
}
