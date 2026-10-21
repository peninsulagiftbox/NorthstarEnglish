package local.northstar;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;

@EnabledIfEnvironmentVariable(named = "NORTHSTAR_DB_TEST", matches = "1")
class DatabaseIntegrationTest {
    @Test void realMySqlMigrationHttpAndPersistence() throws Exception {
        assertEquals("northstar_phase01_test", System.getenv("DB_NAME"), "integration tests must use isolated test schema");
        try (var context = new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            int port = Integer.parseInt(context.getEnvironment().getRequiredProperty("local.server.port"));
            var client = HttpClient.newHttpClient();
            var health = client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/v1/health"))
                    .build(), HttpResponse.BodyHandlers.ofString());
            assertEquals(200, health.statusCode());
            assertTrue(health.body().contains("northstar-english-local-v1"));
            var flyway = context.getBean(Flyway.class);
            var runtime = context.getBean(JdbcTemplate.class);
            try (var connection = flyway.getConfiguration().getDataSource().getConnection();
                 var statement = connection.createStatement()) {
                statement.executeUpdate("UPDATE user_setting SET timezone = 'Europe/London', row_version = row_version + 1, updated_at = UTC_TIMESTAMP(3) WHERE owner_key = 'local'");
            }
            var before = runtime.queryForMap("SELECT * FROM user_setting WHERE owner_key = 'local'");
            assertEquals("Europe/London", before.get("timezone"));
            assertEquals(0, flyway.migrate().migrationsExecuted);
            assertEquals(before, runtime.queryForMap("SELECT * FROM user_setting WHERE owner_key = 'local'"));
            assertThrows(org.springframework.dao.DataAccessException.class,
                    () -> runtime.update("UPDATE user_setting SET row_version = row_version + 1 WHERE owner_key = 'local'"));
            assertEquals(1, runtime.queryForObject("SELECT COUNT(*) FROM flyway_schema_history WHERE success = TRUE AND version = '001'", Integer.class));
            var forbidden = client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/api/v1/health"))
                    .header("Origin", "https://untrusted.example").build(), HttpResponse.BodyHandlers.ofString());
            assertEquals(403, forbidden.statusCode());
        }
    }
}
