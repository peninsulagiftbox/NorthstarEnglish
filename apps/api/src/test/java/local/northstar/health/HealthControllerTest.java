package local.northstar.health;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.JdbcOperations;
import local.northstar.config.DatabaseGuard;

class HealthControllerTest {
    @Test void reportsActualDatabaseAndMigration() {
        JdbcOperations jdbc = mock(JdbcOperations.class);
        when(jdbc.queryForObject(anyString(), eq(String.class))).thenReturn(DatabaseGuard.PROJECT, "001", "northstar_phase01_test");
        var response = new HealthController(jdbc).health();
        assertEquals(200, response.getStatusCode().value());
        assertEquals("true", response.getHeaders().getFirst("X-Northstar-Test-Database"));
        assertEquals("001", ((HealthController.Health) response.getBody()).migrationVersion());
    }

    @Test void databaseFailureIs503AndDoesNotExposeDriverDetails() {
        JdbcOperations jdbc = mock(JdbcOperations.class);
        when(jdbc.queryForObject(anyString(), eq(String.class)))
                .thenThrow(new DataAccessResourceFailureException("secret password / SQL / URL"));
        var response = new HealthController(jdbc).health();
        assertEquals(503, response.getStatusCode().value());
        var problem = (ProblemDetail) response.getBody();
        assertFalse(problem.getDetail().contains("secret"));
        assertEquals("DATABASE_UNAVAILABLE", problem.getProperties().get("code"));
    }

    @Test void wrongProjectNeverReportsUp() {
        JdbcOperations jdbc = mock(JdbcOperations.class);
        when(jdbc.queryForObject(anyString(), eq(String.class))).thenReturn("other-project", "001");
        assertEquals(503, new HealthController(jdbc).health().getStatusCode().value());
    }
}
