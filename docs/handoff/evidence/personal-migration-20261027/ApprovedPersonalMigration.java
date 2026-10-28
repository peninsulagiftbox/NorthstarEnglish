import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.*;
import java.util.*;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.callback.*;

/** Separate, explicitly approved source entry point. Isolated MigrationHarness is unchanged. */
public class ApprovedPersonalMigration {
    static final String UUID="104d5d9d-cd3f-11f1-8da4-920f115cf5cb";
    static final Map<String,String> HASHES=Map.of(
        "V009_01__paragraph_table.sql","991af047d2158c89ff9bf72e2c3d3ea4a90c4abd2fb5a6337ad46335b2c046e9",
        "V009_02__sentence_paragraph_column.sql","2cfea1ebc7a32a5b96f3bb818f19f6df20303079fe55266a574d86a731c79e0f",
        "V009_03__demo_paragraph_backfill.sql","b98470e3f598f6781f8ec4c0171b63602ae60e573bc03ce17c476a1fc66c35c5",
        "V009_04__sentence_paragraph_constraint.sql","6c9f791c225db2ceb0450dca7fd6762002ea22e3f662f864abc34710ec93ece1");
    static void identity(Connection connection) throws SQLException {
        try(var statement=connection.createStatement();var rows=statement.executeQuery("SELECT @@server_uuid,DATABASE(),CURRENT_USER(),(SELECT project_key FROM project_identity)")) {
            if(!rows.next() || !UUID.equals(rows.getString(1)) || !"northstar_english".equals(rows.getString(2))
                || !"northstar_migrator@%".equals(rows.getString(3)) || !"northstar-english-local-v1".equals(rows.getString(4)) || rows.next())
                throw new IllegalStateException("Approved personal source identity mismatch");
        }
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=3 || !args[0].equals("--execute-approved-personal-migration")
            || !Set.of("009.01","009.02","009.03","009.04","validate").contains(args[1]))
            throw new IllegalArgumentException("Explicit source approval, fixed version and migration directory required");
        if(!"personal-migration-20261027".equals(System.getenv("APPROVAL_SCOPE")))
            throw new IllegalStateException("Missing approval scope");
        Path directory=Path.of(args[2]).toAbsolutePath();
        if(!directory.equals(Path.of(System.getenv("APPROVED_MIGRATION_DIRECTORY")).toAbsolutePath()))
            throw new IllegalStateException("Unexpected SQL directory");
        for(var entry:HASHES.entrySet()) {
            String actual=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(directory.resolve(entry.getKey()))));
            if(!actual.equals(entry.getValue())) throw new IllegalStateException("Frozen candidate hash mismatch");
        }
        String url="jdbc:mysql://127.0.0.1:3308/northstar_english?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true&connectTimeout=3000&socketTimeout=30000";
        String password=System.getenv("DB_MIGRATION_PASSWORD");
        try(var connection=DriverManager.getConnection(url,"northstar_migrator",password)) {identity(connection);}
        Callback callback=new Callback() {
            public boolean supports(Event event,Context context) {return event==Event.BEFORE_MIGRATE || event==Event.BEFORE_EACH_MIGRATE || event.name().contains("MIGRATE_STATEMENT") || event==Event.AFTER_EACH_MIGRATE;}
            public boolean canHandleInTransaction(Event event,Context context) {return false;}
            public String getCallbackName() {return "approved-source-identity-and-statement-evidence";}
            public void handle(Event event,Context context) {
                if(event==Event.BEFORE_MIGRATE || event==Event.BEFORE_EACH_MIGRATE) {
                    try {identity(context.getConnection());} catch(SQLException error) {throw new IllegalStateException("Source identity guard failed");}
                }
                System.out.println("CALLBACK "+event.name()+" migration="+(context.getMigrationInfo()==null?"none":context.getMigrationInfo().getVersion()));
                if(context.getStatement()!=null)System.out.println("SQL "+context.getStatement().getSql());
            }
        };
        var configuration=Flyway.configure().dataSource(url,"northstar_migrator",password)
            .locations("filesystem:"+directory).cleanDisabled(true).baselineOnMigrate(false).validateOnMigrate(true).callbacks(callback);
        if(!args[1].equals("validate"))configuration.target(args[1]);
        var flyway=configuration.load();
        if(args[1].equals("validate"))flyway.validate();else flyway.migrate();
        System.out.println("APPROVED PERSONAL MIGRATION PASS "+args[1]);
    }
}
