package local.northstar.health;

import java.time.Instant;
import java.util.Map;
import local.northstar.common.ApiProblems;
import local.northstar.config.DatabaseGuard;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    private final JdbcOperations jdbc;
    public HealthController(JdbcOperations jdbc) { this.jdbc = jdbc; }

    @GetMapping("/api/v1/health")
    public ResponseEntity<?> health() {
        try {
            String project = jdbc.queryForObject("SELECT p.project_key FROM project_identity p JOIN user_setting s ON s.project_key = p.project_key WHERE s.owner_key = 'local'", String.class);
            String version = jdbc.queryForObject("SELECT version FROM flyway_schema_history WHERE success = TRUE AND version IS NOT NULL ORDER BY installed_rank DESC LIMIT 1", String.class);
            if (!DatabaseGuard.PROJECT.equals(project) || version == null) {
                return unavailable();
            }
            return ResponseEntity.ok().cacheControl(org.springframework.http.CacheControl.noStore())
                    .body(new Health("UP", "UP", project, version, Instant.now()));
        } catch (DataAccessException exception) {
            return unavailable();
        }
    }

    private ResponseEntity<?> unavailable() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .cacheControl(org.springframework.http.CacheControl.noStore())
                .body(ApiProblems.problem(HttpStatus.SERVICE_UNAVAILABLE, "DATABASE_UNAVAILABLE", "数据库连接暂不可用，请检查本地服务。", "/api/v1/health"));
    }

    @GetMapping("/api/v1/capabilities")
    public Map<String, Object> capabilities() {
        return Map.of("phase", "03", "contentApiAvailable", true, "learningContentAvailable", true, "aiEnabled", false, "asrEnabled", false, "pronunciationScoringEnabled", false);
    }

    @GetMapping("/api/v1/settings")
    public Map<String, Object> settings() {
        return jdbc.queryForMap("SELECT timezone, default_speed AS defaultSpeed, show_translation AS showTranslation, show_hints AS showHints, shortcut_enabled AS shortcutEnabled, recording_retention AS recordingRetention, row_version AS rowVersion FROM user_setting WHERE owner_key = 'local'");
    }

    public record Health(String status, String database, String project, String migrationVersion, Instant checkedAt) {}
}
