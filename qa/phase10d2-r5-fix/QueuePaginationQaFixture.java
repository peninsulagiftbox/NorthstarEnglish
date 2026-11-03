package local.northstar.knowledge;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import local.northstar.NorthstarApplication;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;
import static org.junit.jupiter.api.Assertions.assertEquals;

class QueuePaginationQaFixture {
    @Test void registerPaginationQueueContent() throws Exception {
        assertEquals("1", System.getenv("NORTHSTAR_FINAL_QA"));
        assertEquals("northstar_phase01_test", System.getenv("DB_NAME"));
        try (var app = new SpringApplicationBuilder(NorthstarApplication.class).run("--spring.main.web-application-type=none")) {
            var admin = new JdbcTemplate(app.getBean(org.flywaydb.core.Flyway.class).getConfiguration().getDataSource());
            assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"), admin.queryForObject("SELECT @@server_uuid", String.class));
            var fixture = new ConceptReviewIntegrationTest();
            Field field = fixture.getClass().getDeclaredField("admin");
            field.setAccessible(true);
            field.set(fixture, admin);
            Method make = fixture.getClass().getDeclaredMethod("fixture", String.class, int.class, int.class, Map.class);
            make.setAccessible(true);
            String[] words = new String[100];
            var sentences = new HashMap<Integer, String>();
            for (int index = 0; index < words.length; index++) {
                words[index] = String.format("w%02d", index + 1);
                sentences.put(index + 1, "I can see the " + words[index] + ".");
            }
            make.invoke(fixture, "qa-r5fix-queue", 1, words.length, sentences);
            var mapper = JsonMapper.builder().build();
            var request = mapper.createObjectNode().put("versionId", "qa-r5fix-queue-v1").put("reviewer", "independent-qa-pagination-fixture");
            var concepts = request.putArray("concepts");
            var occurrences = request.putArray("occurrences");
            var exerciseSentences = request.putArray("exerciseSentences");
            var exerciseKnowledge = request.putArray("exerciseKnowledge");
            for (int index = 0; index < words.length; index++) {
                String suffix = Integer.toString(index + 1);
                String concept = "qa-r5fix-c" + suffix, revision = "qa-r5fix-r" + suffix, occurrence = "qa-r5fix-o" + suffix;
                String sentence = "qa-r5fix-queue-v1-s" + suffix, exercise = sentence + "-dictation";
                admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES (?,'qa-r5fix-queue','qa-r5fix-queue-v1',?,'dictation','english_token_v1')", exercise, sentence);
                concepts.addObject().put("id", concept).put("kind", "vocabulary").put("canonicalKey", words[index])
                    .put("senseKey", "garden-object").putArray("revisions").addObject()
                    .put("id", revision).put("revisionNo", 1).put("displayName", "QA garden " + words[index])
                    .put("explanation", "原创花园测试词义：" + words[index]).put("sourceRef", "self-authored QA fixture")
                    .put("reviewStatus", "confirmed").put("reviewedAt", "2026-11-03T10:00:00Z");
                occurrences.addObject().put("id", occurrence).put("revisionId", revision).put("scope", "sentence").put("sentenceId", sentence).putObject("usage");
                exerciseSentences.addObject().put("exerciseId", exercise).put("sentenceId", sentence).put("role", "primary");
                exerciseKnowledge.addObject().put("exerciseId", exercise).put("occurrenceId", occurrence).put("role", "target");
            }
            assertEquals("REGISTERED", app.getBean(KnowledgeRegistrationCli.class).register(request).get("code"));
            assertEquals(0, admin.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='qa-r5fix-queue'", Integer.class));
        }
    }
}
