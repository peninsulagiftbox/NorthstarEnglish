package local.northstar.study;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST", matches="1")
class StudyIntegrationTest {
    @Test void checkpointValidationConcurrencyCsrfAndPersistence() throws Exception {
        assertEquals("northstar_phase01_test", System.getenv("DB_NAME"));
        try (var context = new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            var jdbc = context.getBean(JdbcTemplate.class);
            var admin = new JdbcTemplate(context.getBean(Flyway.class).getConfiguration().getDataSource());
            var original = jdbc.queryForList("SELECT * FROM study_resume WHERE owner_key='local'");
            var settings = jdbc.queryForMap("SELECT * FROM user_setting WHERE owner_key='local'");
            var client = HttpClient.newHttpClient();
            String url = "http://127.0.0.1:" + context.getEnvironment().getRequiredProperty("local.server.port") + "/api/v1/study/resume";
            String origin = "http://127.0.0.1:" + System.getenv().getOrDefault("WEB_PORT", "3100");
            String body = "{\"lessonId\":\"demo-01\",\"versionId\":\"demo-01-v1\",\"sentenceId\":\"demo-01-v1-s06\",\"tab\":\"dictation\",\"showEnglish\":false,\"showTranslation\":true}";
            var mapper = JsonMapper.builder().build();
            long revision = original.isEmpty() ? 0 : ((Number) original.getFirst().get("row_version")).longValue();
            try {
                assertEquals(403, send(client, url, body, revision, null, false).statusCode());
                assertEquals(403, send(client, url, body, revision, "https://untrusted.example", true).statusCode());
                assertEquals(403, send(client, url, body, revision, origin, false).statusCode());
                var missing = HttpRequest.newBuilder(URI.create(url)).header("Origin", origin).header("X-Northstar-Request", "local-workspace").header("Content-Type", "application/json").PUT(HttpRequest.BodyPublishers.ofString(body)).build();
                assertEquals(428, client.send(missing, HttpResponse.BodyHandlers.ofString()).statusCode());
                assertEquals(400, send(client, url, body.replace("dictation", "practiced"), revision, origin, true).statusCode());
                assertEquals(404, send(client, url, body.replace("demo-01-v1-s06", "foreign-sentence"), revision, origin, true).statusCode());
                assertEquals(400, send(client, url, body.replace("\"showEnglish\":false", "\"showEnglish\":null"), revision, origin, true).statusCode());
                var saved = send(client, url, body, revision, origin, true);
                assertEquals(200, saved.statusCode(), saved.body());
                assertEquals(revision + 1, mapper.readTree(saved.body()).path("rowVersion").asLong());
                assertEquals(412, send(client, url, body.replace("dictation", "writing"), revision, origin, true).statusCode());
                var current = client.send(HttpRequest.newBuilder(URI.create(url)).build(), HttpResponse.BodyHandlers.ofString());
                assertEquals(200, current.statusCode());
                var value = mapper.readTree(current.body());
                assertEquals("demo-01-v1-s06", value.path("sentenceId").asText());
                assertEquals("dictation", value.path("tab").asText());
                assertFalse(value.path("showEnglish").asBoolean());
                assertEquals("\"" + (revision + 1) + "\"", current.headers().firstValue("etag").orElseThrow());
                assertEquals(0, context.getBean(Flyway.class).migrate().migrationsExecuted);
                assertEquals(settings, jdbc.queryForMap("SELECT * FROM user_setting WHERE owner_key='local'"));
                assertThrows(org.springframework.dao.DataAccessException.class, () -> jdbc.update("UPDATE lesson SET availability='withdrawn' WHERE id='demo-01'"));
            } finally {
                if (original.isEmpty()) admin.update("DELETE FROM study_resume WHERE owner_key='local'");
                else {
                    var row = original.getFirst();
                    admin.update("UPDATE study_resume SET session_id=?,lesson_id=?,version_id=?,sentence_id=?,tab_key=?,show_english=?,show_translation=?,row_version=?,updated_at=? WHERE owner_key='local'",
                            row.get("session_id"), row.get("lesson_id"), row.get("version_id"), row.get("sentence_id"), row.get("tab_key"), row.get("show_english"), row.get("show_translation"), row.get("row_version"), row.get("updated_at"));
                }
            }
        }
    }
    private static HttpResponse<String> send(HttpClient client, String url, String body, long revision, String origin, boolean csrf) throws Exception {
        var builder = HttpRequest.newBuilder(URI.create(url)).header("Content-Type", "application/json").header("If-Match", "\"" + revision + "\"");
        if (origin != null) builder.header("Origin", origin);
        if (csrf) builder.header("X-Northstar-Request", "local-workspace");
        return client.send(builder.PUT(HttpRequest.BodyPublishers.ofString(body)).build(), HttpResponse.BodyHandlers.ofString());
    }
}
