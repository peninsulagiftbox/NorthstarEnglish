import java.nio.file.*;
import java.sql.*;
import java.util.*;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.callback.*;

// Isolated CLI only. Does not start Spring and has an explicit source port/UUID denylist.
public class MigrationHarness {
    static final String SOURCE_UUID="104d5d9d-cd3f-11f1-8da4-920f115cf5cb";
    public static void main(String[] args) throws Exception {
        int port=Integer.parseInt(System.getenv("TARGET_MYSQL_PORT"));
        if(port<3313 || port>3399) throw new IllegalStateException("Unapproved target port");
        String expected=System.getenv("EXPECTED_TARGET_UUID");
        if(expected==null || expected.equals(SOURCE_UUID)) throw new IllegalStateException("Missing isolated target identity");
        String user=System.getenv().getOrDefault("TARGET_USER","northstar_migrator");
        if(!Set.of("northstar_migrator","northstar_fault_migrator").contains(user)) throw new IllegalStateException("Unexpected target account");
        String password=System.getenv("TARGET_PASSWORD");
        String url="jdbc:mysql://127.0.0.1:"+port+"/northstar_english?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true";
        boolean initialize="true".equals(System.getenv("INITIALIZE_EMPTY_IDENTITY"));
        try(Connection c=DriverManager.getConnection(url,user,password); java.sql.Statement s=c.createStatement()) {
            try(ResultSet r=s.executeQuery("SELECT @@server_uuid,DATABASE()")) {
                r.next(); if(!expected.equals(r.getString(1)) || !"northstar_english".equals(r.getString(2))) throw new IllegalStateException("Target identity mismatch");
            }
            try(ResultSet r=s.executeQuery("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()")) {
                r.next(); if(initialize && r.getInt(1)!=0) throw new IllegalStateException("Initialization target not empty");
            }
            if(!initialize) try(ResultSet r=s.executeQuery("SELECT project_key FROM project_identity")) {
                if(!r.next() || !"northstar-english-local-v1".equals(r.getString(1)) || r.next()) throw new IllegalStateException("Target project mismatch");
            }
        }
        Callback callback=new Callback() {
            public boolean supports(Event e,Context c) { return e==Event.BEFORE_MIGRATE || e.name().contains("MIGRATE_STATEMENT") || e==Event.BEFORE_EACH_MIGRATE || e==Event.AFTER_EACH_MIGRATE || e==Event.AFTER_EACH_MIGRATE_ERROR; }
            public boolean canHandleInTransaction(Event e,Context c) { return false; }
            public String getCallbackName() { return "isolated-identity-and-statement-evidence"; }
            public void handle(Event e,Context c) {
                System.out.println("CALLBACK "+e.name()+" migration="+(c.getMigrationInfo()==null?"none":c.getMigrationInfo().getVersion()));
                if(c.getStatement()!=null) System.out.println("SQL "+c.getStatement().getSql());
                if(e==Event.BEFORE_MIGRATE && initialize) {
                    // Flyway first verifies the empty schema and creates its own history. No baseline or fabricated history.
                    try(java.sql.Statement s=c.getConnection().createStatement()) {
                        s.execute("CREATE TABLE project_identity (project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY, created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)))");
                        s.execute("INSERT INTO project_identity(project_key) VALUES ('northstar-english-local-v1')");
                    } catch(SQLException error) { throw new IllegalStateException("Isolated identity initialization failed",error); }
                }
            }
        };
        var configuration=Flyway.configure().dataSource(url,user,password).cleanDisabled(true).baselineOnMigrate(false).validateOnMigrate(true)
            .locations(Arrays.stream(args).map(p->"filesystem:"+Path.of(p).toAbsolutePath()).toArray(String[]::new)).callbacks(callback);
        String target=System.getenv("MIGRATION_TARGET"); if(target!=null) configuration.target(target);
        Flyway flyway=configuration.load();
        if("validate".equals(System.getenv("HARNESS_ACTION"))) flyway.validate(); else flyway.migrate();
        System.out.println("HARNESS PASS expectedUuid="+expected+" port="+port);
    }
}
