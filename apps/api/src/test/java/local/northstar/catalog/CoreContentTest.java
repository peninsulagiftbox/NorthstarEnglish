package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import tools.jackson.databind.node.ObjectNode;

class CoreContentTest {
    @TempDir Path temp;

    @Test void normalization() {
        assertEquals(CoreContent.transcript(List.of(" Cafe\u0301.\r\n", "Two\t words!")),
            CoreContent.transcript(List.of("Café.", "Two\t words!")));
        assertNotEquals(CoreContent.transcript(List.of("Two words!")), CoreContent.transcript(List.of("Two  words!")));
        assertNotEquals(CoreContent.transcript(List.of("A")), CoreContent.transcript(List.of("a")));
    }
    @Test void pathBoundary() throws Exception {
        Files.writeString(temp.resolve("ok.txt"), "source");
        assertEquals(temp.resolve("ok.txt").toRealPath(), CoreContent.checked(temp, "ok.txt"));
        for (String name : List.of("../ok.txt", "/etc/hosts", "%2e%2e/secret", "folder\\secret"))
            assertThrows(java.io.IOException.class, () -> CoreContent.checked(temp, name));
        Files.createSymbolicLink(temp.resolve("outside"), Path.of("/etc/hosts"));
        assertThrows(java.io.IOException.class, () -> CoreContent.checked(temp, "outside"));
    }
    @Test void duplicateJsonKeysRejected() {
        assertThrows(RuntimeException.class, () -> CoreContent.JSON.readTree("{\"id\":1,\"id\":2}"));
    }
    @Test @EnabledIfEnvironmentVariable(named="NORTHSTAR_IMPORT_SAMPLE_ROOT", matches=".+")
    void originalsRemainUnreviewed() throws Exception {
        var path = ImportFixtures.copy(temp.resolve("pending"), "a", false);
        var codes = new CoreContent().validate(CoreContent.load(path)).stream().map(CoreContent.Issue::code).toList();
        assertTrue(codes.containsAll(List.of("PROOFREADING_UNCONFIRMED", "ALIGNMENT_UNVERIFIED", "LICENSE_UNCONFIRMED")));
    }
    @Test @EnabledIfEnvironmentVariable(named="NORTHSTAR_IMPORT_SAMPLE_ROOT", matches=".+")
    void schemaAndSemanticMatrix() throws Exception {
        Path root = ImportFixtures.copy(temp.resolve("contract"), "a", true);
        var base = CoreContent.load(root);
        assertEquals(List.of(), new CoreContent().validate(base));
        record Mutation(String expected, java.util.function.Consumer<ObjectNode> edit) {}
        var mutations = List.of(
            new Mutation("SCHEMA_INVALID", node -> node.remove("lesson")),
            new Mutation("SCHEMA_INVALID", node -> node.put("unknown", true)),
            new Mutation("SCHEMA_INVALID", node -> node.put("sentences", "wrong type")),
            new Mutation("SCHEMA_INVALID", node -> ((ObjectNode)node.path("lesson")).put("id", "../bad")),
            new Mutation("SCHEMA_INVALID", node -> ((ObjectNode)node.path("version")).put("contentReadiness", "teaching_complete")),
            new Mutation("SCHEMA_INVALID", node -> ((ObjectNode)node.path("audioAssets").get(0).path("alignment")).put("reviewedAt", "2026-99-88")),
            new Mutation("DUPLICATE_ID", node -> ((ObjectNode)node.path("paragraphs").get(1)).put("id", node.path("paragraphs").get(0).path("id").asText())),
            new Mutation("SEQUENCE", node -> ((ObjectNode)node.path("sentences").get(1)).put("sequence", 1)),
            new Mutation("PARAGRAPH_REFERENCE", node -> ((ObjectNode)node.path("sentences").get(0)).put("paragraphId", "foreign")),
            new Mutation("TRANSCRIPT_HASH", node -> ((ObjectNode)node.path("version")).put("transcriptSha256", "0".repeat(64))),
            new Mutation("LICENSE_UNCONFIRMED", node -> ((ObjectNode)node.path("sources").get(0)).put("reviewStatus", "expired")),
            new Mutation("ALIGNMENT_UNVERIFIED", node -> ((ObjectNode)node.path("audioAssets").get(0).path("alignment")).put("status", "needs_review")),
            new Mutation("ALIGNMENT_SCOPE", node -> ((ObjectNode)node.path("audioAssets").get(0).path("alignment")).putArray("sentenceIds").add("foreign")),
            new Mutation("ALIGNMENT_AUDIO_HASH", node -> ((ObjectNode)node.path("audioAssets").get(0).path("alignment")).put("audioSha256", "0".repeat(64))),
            new Mutation("ALIGNMENT_TRANSCRIPT_HASH", node -> ((ObjectNode)node.path("audioAssets").get(0).path("alignment")).put("transcriptSha256", "0".repeat(64))),
            new Mutation("AUDIO_INTERVAL", node -> ((ObjectNode)node.path("sentences").get(1)).put("startMs", 0)),
            new Mutation("FILE_PATH", node -> ((ObjectNode)node.path("audioAssets").get(0)).put("storageKey", "../outside.mp3")),
            new Mutation("FILE_HASH", node -> ((ObjectNode)node.path("audioAssets").get(0)).put("sha256", "0".repeat(64))),
            new Mutation("SCHEMA_INVALID", node -> ((ObjectNode)node.path("exerciseSets").get(0)).putArray("exerciseIds")),
            new Mutation("EXERCISE_SOURCE", node -> ((ObjectNode)node.path("exercises").get(0)).putArray("sentenceIds").add("foreign")),
            new Mutation("CHOICE_CONTRACT", node -> ((ObjectNode)node.path("exercises").get(12)).put("answerKey", "missing")),
            new Mutation("CANONICAL_KEY", node -> ((ObjectNode)node.path("knowledge").get(0)).put("canonicalKey", "   "))
        );
        for (var mutation : mutations) {
            ObjectNode changed = ((ObjectNode)base.content()).deepCopy();
            mutation.edit().accept(changed);
            ImportFixtures.save(root, changed, ((ObjectNode)base.manifest()).deepCopy());
            var issues = new CoreContent().validate(CoreContent.load(root));
            assertTrue(issues.stream().anyMatch(issue -> issue.code().equals(mutation.expected())), mutation.expected() + ":" + issues);
            assertTrue(issues.stream().allMatch(issue -> issue.path().startsWith("/") || issue.path().isEmpty()));
        }
    }
}
