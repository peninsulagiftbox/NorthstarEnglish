import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.*;
import java.util.HexFormat;
import org.flywaydb.core.Flyway;

/** Explicit one-migration maintenance entry point; no Spring, seeder, baseline or repair. */
public final class ApprovedOrderMigration {
    private static final String SHA = "8b32932f9447faf37a27dd449eb11106130d20637c887ce0bd0b8d2f5bdefa32";
    public static void main(String[] args) throws Exception {
        if (args.length != 1 || !"phase10b2-source-order-v1".equals(System.getenv("NORTHSTAR_APPROVED_ACTION")))
            throw new IllegalStateException("Missing explicit approved maintenance scope");
        String expected = System.getenv("EXPECTED_SOURCE_UUID");
        if (expected == null || expected.isBlank() || !"3308".equals(System.getenv("MYSQL_PORT")))
            throw new IllegalStateException("Missing pinned source identity");
        Path directory = Path.of(args[0]).toRealPath();
        Path migration = directory.resolve("V009_05__lesson_catalog_order.sql");
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(migration)));
        if (!SHA.equals(hash)) throw new IllegalStateException("Unreviewed migration bytes");
        String url = "jdbc:mysql://127.0.0.1:3308/northstar_english?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true";
        String password = System.getenv("DB_MIGRATION_PASSWORD");
        try (Connection c = DriverManager.getConnection(url, "northstar_migrator", password); Statement s = c.createStatement()) {
            c.setReadOnly(true);
            try (ResultSet r = s.executeQuery("SELECT @@server_uuid,DATABASE(),(SELECT project_key FROM project_identity)")) {
                if (!r.next() || !expected.equals(r.getString(1)) || !"northstar_english".equals(r.getString(2)) || !"northstar-english-local-v1".equals(r.getString(3)))
                    throw new IllegalStateException("Source identity mismatch");
            }
            try (ResultSet r = s.executeQuery("SELECT version FROM flyway_schema_history WHERE success=TRUE ORDER BY installed_rank DESC LIMIT 1")) {
                if (!r.next() || !"009.04".equals(r.getString(1))) throw new IllegalStateException("Source must still be V009.04");
            }
        }
        Flyway flyway = Flyway.configure().dataSource(url,"northstar_migrator",password)
                .locations("filesystem:"+directory).target("009.05").cleanDisabled(true).baselineOnMigrate(false).validateOnMigrate(true).load();
        flyway.validate();
        var pending = flyway.info().pending();
        if (pending.length != 1 || !"009.05".equals(pending[0].getVersion().getVersion()))
            throw new IllegalStateException("Only frozen V009.05 may be pending");
        var result = flyway.migrate();
        if (result.migrationsExecuted != 1) throw new IllegalStateException("Unexpected migration count");
        flyway.validate();
        System.out.println("PASS: exactly frozen V009.05 applied and validated on explicitly approved source");
    }
}
