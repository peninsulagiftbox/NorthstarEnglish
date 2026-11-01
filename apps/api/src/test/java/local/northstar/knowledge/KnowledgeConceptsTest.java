package local.northstar.knowledge;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

/** Pure-unit coverage for canonical key normalization; DB uniqueness semantics live in the integration tests. */
class KnowledgeConceptsTest {
    @Test void foldsAsciiWhitespaceAndTrims() {
        assertEquals("look after",KnowledgeConcepts.canonicalKey("  look \t after \n"));
    }
    @Test void foldsUnicodeWhitespaceIncludingNbsp() {
        assertEquals("look after",KnowledgeConcepts.canonicalKey("look\u00A0after"));
        assertEquals("bank",KnowledgeConcepts.canonicalKey("\u202Fbank\u2007"));
    }
    @Test void keepsCasePunctuationAndDiacritics() {
        assertEquals("Bank",KnowledgeConcepts.canonicalKey("Bank"));
        assertEquals("don't",KnowledgeConcepts.canonicalKey("don't"));
        assertEquals("well-known",KnowledgeConcepts.canonicalKey("well-known"));
        assertEquals("caf\u00e9",KnowledgeConcepts.canonicalKey("cafe\u0301"));
    }
    @Test void rejectsBlankAndOversizedKeys() {
        assertThrows(KnowledgeConcepts.Failure.class,()->KnowledgeConcepts.canonicalKey(null));
        assertThrows(KnowledgeConcepts.Failure.class,()->KnowledgeConcepts.canonicalKey(" \u00A0 "));
        assertThrows(KnowledgeConcepts.Failure.class,()->KnowledgeConcepts.canonicalKey("存".repeat(256)));
        assertEquals(255,KnowledgeConcepts.canonicalKey("存".repeat(255)).codePoints().count());
    }
}
