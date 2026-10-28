package local.northstar.report;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class ReportExportIntegrationTest {
    private final JsonMapper json=JsonMapper.builder().build();
    private final HttpClient http=HttpClient.newHttpClient();
    @Test void actualMetricsPreferencesCasAndStrictSnapshotPreview() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            var before=admin.queryForMap("SELECT * FROM user_setting WHERE owner_key='local'");
            try {
                var report=body(send(base+"/reports","GET",null));
                assertEquals(admin.queryForObject("SELECT COUNT(*) FROM exercise_attempt a JOIN exercise e ON e.id=a.exercise_id WHERE e.kind='dictation' AND NOT a.answer_exposed",Integer.class),report.path("metrics").path("dictation").path("independentSubmitted").asInt());
                assertEquals(admin.queryForObject("SELECT COALESCE(SUM(correct_count),0) FROM quiz_run",Integer.class),report.path("metrics").path("quiz").path("correct").asInt());
                assertEquals(admin.queryForObject("SELECT COUNT(*) FROM reading_answer",Integer.class),report.path("readingHistory").size());
                for(var lesson:report.path("lessons")) {assertEquals(6,lesson.path("paths").size());assertEquals(0,lesson.path("paths").get(0).path("evidenceCount").asInt());}
                var settings=new LinkedHashMap<String,Object>();settings.put("defaultSpeed",1.25);settings.put("showTranslation",false);settings.put("showHints",false);settings.put("shortcutEnabled",false);settings.put("recordingEnabled",false);settings.put("rowVersion",((Number)before.get("row_version")).longValue());
                assertEquals(200,send(base+"/settings","PUT",settings).statusCode());
                assertEquals(409,send(base+"/settings","PUT",settings).statusCode());
                assertEquals(1.25,body(send(base+"/settings","GET",null)).path("defaultSpeed").asDouble());
                settings.put("rowVersion",((Number)before.get("row_version")).longValue()+1);settings.put("defaultSpeed",2.0);
                assertEquals(422,send(base+"/settings","PUT",settings).statusCode());
                var exported=body(send(base+"/data/export","GET",null));
                var payload=json.readTree(exported.path("payloadJson").asText());assertFalse(payload.path("mediaIncluded").asBoolean());assertFalse(payload.path("browserBuffersIncluded").asBoolean());
                assertTrue(payload.path("tables").has("writing_revision"));assertTrue(payload.path("tables").has("command_receipt"));assertTrue(payload.path("tables").has("review_result"));
                var preview=send(base+"/data/import-preview","POST",exported);assertEquals(200,preview.statusCode(),preview.body());
                assertEquals(body(preview),body(send(base+"/data/import-preview","POST",exported)));
                assertEquals(exported.path("sha256").asText(),body(preview).path("sha256").asText());
                var bad=json.createObjectNode();bad.put("format","northstar.snapshot.v1");bad.put("sha256","broken");bad.put("payloadJson",exported.path("payloadJson").asText());
                assertEquals(422,send(base+"/data/import-preview","POST",bad).statusCode());
                for(String replacement:List.of("\"owner\":\"foreign\"","\"schemaVersion\":\"999\"")) {
                    String raw=exported.path("payloadJson").asText().replace(replacement.contains("owner")?"\"owner\":\"local\"":"\"schemaVersion\":\""+json.readTree(exported.path("payloadJson").asText()).path("schemaVersion").asText()+"\"",replacement);
                    bad.put("payloadJson",raw);bad.put("sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(raw.getBytes(StandardCharsets.UTF_8))));
                    assertEquals(422,send(base+"/data/import-preview","POST",bad).statusCode());
                }
                // Equivalent schemas can be installed at different times on a restore machine.
                var portable=json.readTree(exported.path("payloadJson").asText());
                var history=portable.path("tables").path("flyway_schema_history");
                int installedAt=0;for(int i=0;i<history.path("columns").size();i++)if(history.path("columns").get(i).asText().equals("installed_on"))installedAt=i;
                ((tools.jackson.databind.node.ArrayNode)history.path("rows").get(0)).set(installedAt,"2026-01-01 00:00:00");
                String portableRaw=json.writeValueAsString(portable);
                bad.put("payloadJson",portableRaw);bad.put("sha256",HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(portableRaw.getBytes(StandardCharsets.UTF_8))));
                assertEquals(200,send(base+"/data/import-preview","POST",bad).statusCode());
                assertFalse(exported.toString().contains(System.getenv("DB_PASSWORD")));
                assertEquals(report.path("metrics"),body(send(base+"/reports","GET",null)).path("metrics"));
                assertEquals(0,app.getBean(Flyway.class).migrate().migrationsExecuted);
            } finally {
                admin.update("UPDATE user_setting SET default_speed=?,show_translation=?,show_hints=?,shortcut_enabled=?,recording_enabled=?,row_version=?,updated_at=? WHERE owner_key='local'",before.get("default_speed"),before.get("show_translation"),before.get("show_hints"),before.get("shortcut_enabled"),before.get("recording_enabled"),before.get("row_version"),before.get("updated_at"));
            }
        }
    }
    private JsonNode body(HttpResponse<String> response){return json.readTree(response.body());}
    private HttpResponse<String> send(String url,String method,Object body)throws Exception {
        var request=HttpRequest.newBuilder(URI.create(url)).header("Content-Type","application/json").header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body))).build();
        return http.send(request,HttpResponse.BodyHandlers.ofString());
    }
}
