package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named = "NORTHSTAR_DB_TEST", matches = "1")
class CatalogIntegrationTest {
    @Test void mysqlSeedVersionConstraintsAndRealMediaHttp() throws Exception {
        assertEquals("northstar_phase01_test", System.getenv("DB_NAME"));
        try (var context = new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            var jdbc = context.getBean(JdbcTemplate.class);
            var flyway = context.getBean(Flyway.class);
            var admin = new JdbcTemplate(flyway.getConfiguration().getDataSource());
            var seed = context.getBean(ContentSeeder.class);
            Map<String, Integer> before = counts(jdbc);
            seed.seed();
            seed.seed();
            assertEquals(before, counts(jdbc));
            assertEquals(Map.of("book",4,"lesson",1,"lesson_version",2,"sentence",20,"audio_asset",20,"content_license",3), before);
            assertEquals(0, flyway.migrate().migrationsExecuted);
            assertNull(jdbc.queryForMap("SELECT book_id FROM lesson WHERE id = 'demo-01'").get("book_id"));
            assertEquals(4, jdbc.queryForObject("SELECT COUNT(*) FROM book WHERE availability = 'catalog_only'", Integer.class));
            assertThrows(org.springframework.dao.DataAccessException.class, () -> jdbc.update("UPDATE lesson SET availability = 'withdrawn' WHERE id = 'demo-01'"));
            assertThrows(org.springframework.dao.DataAccessException.class, () -> admin.update("UPDATE sentence SET audio_asset_id = 'missing' WHERE id = 'demo-01-v1-s01'"));
            assertThrows(org.springframework.dao.DataAccessException.class, () -> admin.update("UPDATE sentence SET sequence_no = 2 WHERE id = 'demo-01-v1-s01'"));
            assertThrows(org.springframework.dao.DataAccessException.class, () -> admin.update("UPDATE lesson SET current_version_id = 'missing' WHERE id = 'demo-01'"));
            String base = "http://127.0.0.1:" + context.getEnvironment().getRequiredProperty("local.server.port") + "/api/v1";
            var client = HttpClient.newHttpClient();
            var mapper = JsonMapper.builder().build();
            assertEquals(200, get(client, base + "/books", null).statusCode());
            assertProblem(client, base + "/lessons/unknown", 404, "LESSON_NOT_FOUND");
            assertProblem(client, base + "/lessons/nce-book-1", 404, "LESSON_NOT_FOUND");
            assertProblem(client, base + "/audio/unknown", 404, "AUDIO_NOT_FOUND");
            assertProblem(client, base + "/licenses/unknown", 404, "LICENSE_NOT_FOUND");
            var latest = mapper.readTree(get(client, base + "/lessons/demo-01", null).body());
            assertEquals("demo-01-v2",latest.path("versionId").asText());
            assertEquals("demo-01-v2-a06",latest.path("sentences").get(5).path("audio").path("id").asText());
            assertTrue(latest.path("audioLabel").asText().contains("Sonia"));
            var response = get(client, base + "/lessons/demo-01?versionId=demo-01-v1", null);
            assertEquals(200, response.statusCode());
            assertEquals("no-store", response.headers().firstValue("cache-control").orElseThrow());
            var lesson = mapper.readTree(response.body());
            assertEquals(10, lesson.path("sentences").size());
            assertFalse(lesson.path("releaseReady").asBoolean());
            assertFalse(new String(response.body(), java.nio.charset.StandardCharsets.UTF_8).contains("answerKey"));
            for (var sentence : lesson.path("sentences")) {
                var asset = sentence.path("audio");
                String uri = base.replace("/api/v1", "") + asset.path("uri").asText();
                var audio = get(client, uri, null);
                assertEquals(200, audio.statusCode());
                assertEquals("audio/mpeg", audio.headers().firstValue("content-type").orElseThrow());
                assertEquals(asset.path("byteSize").asInt(), audio.body().length);
                assertEquals(asset.path("sha256").asText(), ContentPackage.sha256(audio.body()));
                var range = get(client, uri, "bytes=0-31");
                assertEquals(206, range.statusCode());
                assertArrayEquals(java.util.Arrays.copyOf(audio.body(),32), range.body());
                assertEquals("bytes 0-31/" + audio.body().length, range.headers().firstValue("content-range").orElseThrow());
                assertEquals(206, get(client, uri, "bytes=-16").statusCode());
                assertEquals(416, get(client, uri, "bytes=99999999-").statusCode());
                assertEquals(416, get(client, uri, "bytes=abc").statusCode());
            }
            // Simulate a missing file only in DB metadata in the isolated test schema.
            String key = admin.queryForObject("SELECT storage_key FROM audio_asset WHERE id='demo-01-v1-a01'", String.class);
            try {
                admin.update("UPDATE audio_asset SET storage_key='demo-01/v999/audio/01.mp3' WHERE id='demo-01-v1-a01'");
                assertProblem(client, base + "/audio/demo-01-v1-a01", 503, "AUDIO_UNAVAILABLE");
                var degraded = get(client,base + "/lessons/demo-01?versionId=demo-01-v1",null);
                assertEquals(200,degraded.statusCode());
                assertEquals("unavailable",mapper.readTree(degraded.body()).path("sentences").get(0).path("audio").path("status").asText());
            } finally { admin.update("UPDATE audio_asset SET storage_key=? WHERE id='demo-01-v1-a01'", key); }
            try {
                admin.update("UPDATE audio_asset SET sha256=? WHERE id='demo-01-v1-a01'", "0".repeat(64));
                assertProblem(client, base + "/audio/demo-01-v1-a01", 503, "AUDIO_UNAVAILABLE");
            } finally {
                admin.update("UPDATE audio_asset SET sha256=? WHERE id='demo-01-v1-a01'", lesson.path("sentences").get(0).path("audio").path("sha256").asText());
            }
            Path manifest = Path.of("../../content/demo-01/v1/manifest.json");
            byte[] original = Files.readAllBytes(manifest);
            // Do not mutate source package to test immutability; alter isolated DB version hash instead.
            String hash = ContentPackage.sha256(original);
            try {
                admin.update("UPDATE lesson_version SET manifest_sha256=? WHERE id='demo-01-v1'", "0".repeat(64));
                assertThrows(IllegalStateException.class, seed::seed);
            } finally { admin.update("UPDATE lesson_version SET manifest_sha256=? WHERE id='demo-01-v1'", hash); }
            seed.seed();
            var transaction = new org.springframework.transaction.support.TransactionTemplate(new org.springframework.jdbc.datasource.DataSourceTransactionManager(flyway.getConfiguration().getDataSource()));
            transaction.executeWithoutResult(status -> {
                admin.update("INSERT INTO lesson (id,slug,kind,availability) VALUES ('test-other','test-other','original_demo','draft')");
                admin.update("INSERT INTO lesson_version (id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json) VALUES ('test-other-v1','test-other',1,'demo-text-v1',?,?,'{}')", "0".repeat(64), "0".repeat(64));
                assertThrows(org.springframework.dao.DataAccessException.class, () -> admin.update("UPDATE lesson SET current_version_id='test-other-v1' WHERE id='demo-01'"));
                assertThrows(org.springframework.dao.DataAccessException.class, () -> admin.update("UPDATE sentence SET lesson_version_id='test-other-v1' WHERE id='demo-01-v1-s01'"));
                status.setRollbackOnly();
            });
            assertEquals(before, counts(jdbc));
        }
    }

    private static Map<String, Integer> counts(JdbcTemplate jdbc) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (String table : new String[]{"book","lesson","lesson_version","sentence","audio_asset","content_license"}) counts.put(table, jdbc.queryForObject("SELECT COUNT(*) FROM " + table, Integer.class));
        return counts;
    }

    private static HttpResponse<byte[]> get(HttpClient client, String uri, String range) throws Exception {
        var request = HttpRequest.newBuilder(URI.create(uri)).timeout(java.time.Duration.ofSeconds(10));
        if (range != null) request.header("Range", range);
        return client.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }

    private static void assertProblem(HttpClient client, String uri, int status, String code) throws Exception {
        var response = get(client, uri, null);
        assertEquals(status, response.statusCode());
        var json = JsonMapper.builder().build().readTree(response.body());
        assertEquals(code, json.path("code").asText());
        assertTrue(json.has("traceId") && json.has("instance"));
    }
}
