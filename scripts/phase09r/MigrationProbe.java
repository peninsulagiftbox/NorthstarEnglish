import java.sql.*;
import org.flywaydb.core.Flyway;

// Acceptance-only probe: no application startup, migrate, repair, baseline or DDL.
class MigrationProbe {
    public static void main(String[] args) throws Exception {
        String url = "jdbc:mysql://127.0.0.1:" + System.getenv("MYSQL_PORT") + "/" + System.getenv().getOrDefault("DB_NAME", "northstar_english");
        String password = System.getenv("DB_PASSWORD");
        try (Connection c = DriverManager.getConnection(url, "northstar_app", password)) {
            c.setReadOnly(true);
            try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT version,description,type,script,checksum,success FROM flyway_schema_history WHERE version='008'")) {
                int count=0;
                while(r.next()) {
                    count++;
                    System.out.printf("V008 version=%s description=%s type=%s script=%s checksum=%s success=%s%n",r.getString(1),r.getString(2),r.getString(3),r.getString(4),r.getString(5),r.getString(6));
                    if (!r.getBoolean(6)) throw new IllegalStateException("V008 not successful");
                }
                if (count!=1) throw new IllegalStateException("Expected one V008 record");
            }
            try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT column_name,column_type,is_nullable,column_default,extra FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='user_setting' ORDER BY ordinal_position")) {
                boolean found=false;
                while(r.next()) {
                    System.out.printf("user_setting %s %s nullable=%s default=%s extra=%s%n",r.getString(1),r.getString(2),r.getString(3),r.getString(4),r.getString(5));
                    if (r.getString(1).equals("recording_enabled")) {
                        found=true;
                        if (!r.getString(2).equals("tinyint(1)") || !r.getString(3).equals("NO") || !r.getString(4).equals("1")) throw new IllegalStateException("V008 DDL mismatch");
                    }
                }
                if (!found) throw new IllegalStateException("Missing recording_enabled");
            }
        }
        Flyway.configure().dataSource(url,"northstar_app",password).locations("filesystem:"+args[0]).cleanDisabled(true).load().validate();
        System.out.println("PASS: read-only V008 metadata and Flyway validate; no migrate/repair/history writes");
    }
}
