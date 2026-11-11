import java.util.*;
import org.flywaydb.core.Flyway;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

public final class Migrate {
    public static void main(String[] args) {
        var env = System.getenv();
        String port = env.get("MYSQL_PORT"), schema = env.get("DB_NAME");
        if (port.equals("3308") || !Set.of("northstar_phase01_test", "northstar_english").contains(schema))
            throw new IllegalArgumentException("Isolated target required");
        String url = "jdbc:mysql://127.0.0.1:" + port + "/" + schema + "?connectionTimeZone=UTC&socketTimeout=600000";
        var source = new DriverManagerDataSource(url, "northstar_migrator", env.get("DB_MIGRATION_PASSWORD"));
        var db = new JdbcTemplate(source);
        if (!env.get("NORTHSTAR_EXPECTED_DB_UUID").equals(db.queryForObject("SELECT @@server_uuid", String.class)))
            throw new IllegalArgumentException("Identity mismatch");
        var config = Flyway.configure().dataSource(source).cleanDisabled(true).locations("classpath:db/migration");
        if (args.length == 1) config.target(args[0]);
        var flyway = config.load();
        int tables = db.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()", Integer.class);
        if (tables == 1 && db.queryForObject("SELECT COUNT(*) FROM project_identity WHERE project_key='northstar-english-local-v1'", Integer.class) == 1)
            Flyway.configure().dataSource(source).baselineVersion("0").load().baseline();
        flyway.migrate();
        System.out.println(db.queryForObject("SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1", String.class));
    }
}
