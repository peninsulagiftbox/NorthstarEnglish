package local.northstar.exercise;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
class TokenAlignerTest {
    @Test void punctuationCaseAndApostrophes() {
        assertTrue(TokenAligner.align("Thank you!", "THANK YOU.").correct());
        assertTrue(TokenAligner.align("It's wet.", "It’s wet!").correct());
        assertFalse(TokenAligner.align("It's wet.", "It is wet.").correct());
    }
    @Test void omissionDoesNotCascadeAndInsertionIsExplicit() {
        var missing=TokenAligner.align("Please put them beside the blue bench.","Please put them beside the bench.");
        assertEquals(1,missing.edits().stream().filter(e -> !e.kind().equals("equal")).count());
        assertEquals("blue",missing.edits().stream().filter(e -> e.kind().equals("omit")).findFirst().orElseThrow().expected());
        assertEquals("insert",TokenAligner.align("the bench", "the big bench").edits().get(1).kind());
    }
    @Test void behindIsNotBeside() {
        var result=TokenAligner.align("Please put them beside the blue bench.","Please put them behind the blue bench.");
        assertFalse(result.correct()); var edit=result.edits().get(3);
        assertEquals("replace",edit.kind());assertEquals("beside",edit.expected());assertEquals("behind",edit.actual());assertEquals(3,edit.expectedIndex());
    }
}
