package local.northstar.config;

import java.sql.Connection;
import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DatabaseGuard {
    public static final String PROJECT = "northstar-english-local-v1";

    @Bean
    FlywayMigrationStrategy guardedMigration() {
        return flyway -> {
            try (Connection connection = flyway.getConfiguration().getDataSource().getConnection()) {
                String catalog = connection.getCatalog();
                if (!"northstar_english".equals(catalog) && !"northstar_phase01_test".equals(catalog)) {
                    throw new IllegalStateException("Database schema is not a Northstar schema");
                }
                try (var statement = connection.prepareStatement("SELECT project_key FROM project_identity")) {
                    try (var result = statement.executeQuery()) {
                        if (!result.next() || !PROJECT.equals(result.getString(1)) || result.next()) {
                            throw new IllegalStateException("Database project identity mismatch");
                        }
                    }
                }
                // Bootstrap only our verified identity-only schema, never an arbitrary non-empty database.
                boolean history;
                try (var statement = connection.prepareStatement("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'flyway_schema_history'")) {
                    try (var result = statement.executeQuery()) { result.next(); history = result.getInt(1) > 0; }
                }
                if (!history) {
                    try (var statement = connection.prepareStatement("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()")) {
                        try (var result = statement.executeQuery()) {
                            result.next();
                            if (result.getInt(1) != 1) {
                                throw new IllegalStateException("Unrecognized tables; refuse bootstrap");
                            }
                        }
                    }
                    flyway.baseline();
                }
            } catch (Exception exception) {
                // Never attach driver exceptions: they may contain connection details.
                throw new IllegalStateException("Northstar database identity check failed; inspect local configuration");
            }
            flyway.migrate();
        };
    }
}
