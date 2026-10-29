import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.*;
import java.util.*;
import org.flywaydb.core.Flyway;

/** Explicit reviewed 009.05 -> 009.15 maintenance only. No Spring, baseline, repair or learning DML. */
public final class ApprovedIdentityMigration {
    static final String SOURCE_UUID="104d5d9d-cd3f-11f1-8da4-920f115cf5cb";
    static final Map<String,String> FILES=Map.ofEntries(
        Map.entry("V001__local_settings_and_environment.sql","f1291a4607e23e745b7b892770d270b3ac895982db991867997db3a631b81441"),
        Map.entry("V002__catalog_content_versions.sql","1368dd578ad76f6ad4aca82b67fed40536c7622e2dcad3a32a0ae812d4cf1819"),
        Map.entry("V003__study_session_resume.sql","4c79354b485d894f64f9e9a9fc0905dab70a44c74fc8dbc4f1a229bcb4626b54"),
        Map.entry("V004__attempts_evidence_drafts_review_sources.sql","d3f3da71424d34019bccdb44126c4f501545fb321dea042bc5ff6d4efbae6c8f"),
        Map.entry("V005__knowledge_points_and_exercise_links.sql","b149048e7ce13e3c63c9beac9b05d73ba0604da8795f20a8c39e40b37365fa4d"),
        Map.entry("V006__recordings_and_writing_revisions.sql","5783b41c32d56cac63854af9905887c64a0b98467ecaf82d9f59442e7c08a8b3"),
        Map.entry("V007__quiz_runs_and_review_results.sql","0a2e3b98b4443d29d029dd0e2d427e9c11089399cfeef6d3f37a794742592d59"),
        Map.entry("V008__recording_preference.sql","cd5818104f70f3e2a6c699aa4355d87e9bdc70908b24f88cf8ebbac92c7cd9f1"),
        Map.entry("V009_01__paragraph_table.sql","991af047d2158c89ff9bf72e2c3d3ea4a90c4abd2fb5a6337ad46335b2c046e9"),
        Map.entry("V009_02__sentence_paragraph_column.sql","2cfea1ebc7a32a5b96f3bb818f19f6df20303079fe55266a574d86a731c79e0f"),
        Map.entry("V009_03__demo_paragraph_backfill.sql","b98470e3f598f6781f8ec4c0171b63602ae60e573bc03ce17c476a1fc66c35c5"),
        Map.entry("V009_04__sentence_paragraph_constraint.sql","6c9f791c225db2ceb0450dca7fd6762002ea22e3f662f864abc34710ec93ece1"),
        Map.entry("V009_05__lesson_catalog_order.sql","8b32932f9447faf37a27dd449eb11106130d20637c887ce0bd0b8d2f5bdefa32"),
        Map.entry("V009_06__content_identity_registries.sql","6a849bc0fbcf51f74f3e3e26affe1030b260c0ffd17020f2d8a217b63e947b7c"),
        Map.entry("V009_07__identity_context_columns.sql","4c6e6ea186b7802a8bd372b9b70dc726aea6776a820ea3353053d6f7006e9979"),
        Map.entry("V009_08__legacy_identity_registration.sql","2f6fcba0e46bed07341e486ed05456460e87ba88a331991c65c504aa08840fc0"),
        Map.entry("V009_09__identity_context_constraints.sql","e48f4a5a81faa21b6ba124799688e63f21d343a402b1b253c4bbd66914583c35"),
        Map.entry("V009_10__version_sentence_mapping.sql","1b3f522c824b219da270f140d587b4440392bdbf22df590fa019ec55a45aad6f"),
        Map.entry("V009_11__version_publication_lifecycle.sql","17276f3044bf36e7d7e61615ab1a3fb68a884dc59274b5cdbd9eec12dacd3e4b"),
        Map.entry("V009_12__publication_validation_and_audit.sql","cf1fd67964cad5b9e4f590fe83550d5d55838105cde40060b0ca43e3f426fed7"),
        Map.entry("V009_13__original_lesson_kind.sql","45d6e47a7a4e52f8804eb0ddd3252578d8e8cb48c33696480b4bdcb29e0c27da"),
        Map.entry("V009_14__original_recording_source.sql","da9fb5b91c4319599e2bb822940cb52ba9689aa135660776443566541e2c900f"),
        Map.entry("V009_15__mapping_null_safety.sql","73495895722f471dcb82e91d5b11348ac4e5a41d1cf0d2d69d89a747b5c9defd")
    );
    public static void main(String[] args)throws Exception {
        boolean rehearsal=args.length==2 && args[0].equals("--rehearse");
        String scope=rehearsal?"phase10b3-isolated-v00915-v1":"phase10b3-source-v00915-v1";
        if((!rehearsal && args.length!=1) || !scope.equals(System.getenv("NORTHSTAR_APPROVED_ACTION")))throw new IllegalStateException("Explicit approved scope required");
        int port=Integer.parseInt(System.getenv().getOrDefault("MYSQL_PORT","0"));
        String expected=System.getenv(rehearsal?"EXPECTED_TARGET_UUID":"EXPECTED_SOURCE_UUID");
        if(expected==null || (rehearsal?(port<3313 || port>3399 || expected.equals(SOURCE_UUID)):(port!=3308 || !expected.equals(SOURCE_UUID))))throw new IllegalStateException("Pinned database identity required");
        Path directory=Path.of(args[rehearsal?1:0]).toRealPath();
        try(var stream=Files.list(directory)) {
            var actual=stream.filter(p->p.getFileName().toString().matches("V.*\\.sql")).map(p->p.getFileName().toString()).collect(java.util.stream.Collectors.toSet());
            if(!actual.equals(FILES.keySet()))throw new IllegalStateException("Unexpected migration set");
        }
        for(var entry:FILES.entrySet())if(!entry.getValue().equals(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(directory.resolve(entry.getKey()))))))throw new IllegalStateException("Frozen migration bytes changed");
        String url="jdbc:mysql://127.0.0.1:"+port+"/northstar_english?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true";
        String password=System.getenv("DB_MIGRATION_PASSWORD");
        try(var connection=DriverManager.getConnection(url,"northstar_migrator",password);var statement=connection.createStatement()){
            connection.setReadOnly(true);
            try(var rs=statement.executeQuery("SELECT @@server_uuid,DATABASE(),(SELECT project_key FROM project_identity)")){
                if(!rs.next() || !expected.equals(rs.getString(1)) || !"northstar_english".equals(rs.getString(2)) || !"northstar-english-local-v1".equals(rs.getString(3)))throw new IllegalStateException("Database identity mismatch");
            }
            try(var rs=statement.executeQuery("SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1")){
                if(!rs.next() || !"009.05".equals(rs.getString(1)))throw new IllegalStateException("Source must be exactly 009.05");
            }
            try(var rs=statement.executeQuery("SELECT COUNT(*) FROM flyway_schema_history WHERE success=FALSE")){
                rs.next();if(rs.getInt(1)!=0)throw new IllegalStateException("Failed history present");
            }
            try(var rs=statement.executeQuery("SELECT COUNT(*) FROM lesson WHERE id<>'demo-01'")){
                rs.next();if(rs.getInt(1)!=0)throw new IllegalStateException("Unregistered historical lessons require separate identity review");
            }
        }
        var flyway=Flyway.configure().dataSource(url,"northstar_migrator",password).locations("filesystem:"+directory).target("009.15").cleanDisabled(true).baselineOnMigrate(false).validateOnMigrate(true).load();
        var pending=flyway.info().pending();var expectedVersions=new HashSet<String>();for(int i=6;i<=15;i++)expectedVersions.add("009."+String.format("%02d",i));
        var actualVersions=new HashSet<String>();for(var migration:pending)actualVersions.add(migration.getVersion().getVersion());
        if(pending.length!=10 || !actualVersions.equals(expectedVersions))throw new IllegalStateException("Only the ten frozen migrations may be pending");
        var result=flyway.migrate();if(result.migrationsExecuted!=10)throw new IllegalStateException("Unexpected migration execution count");flyway.validate();
        System.out.println("PASS: exactly ten frozen migrations applied to 009.15 and validated; rehearsal="+rehearsal);
    }
}
