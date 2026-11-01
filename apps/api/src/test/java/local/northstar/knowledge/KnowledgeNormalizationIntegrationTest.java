package local.northstar.knowledge;

import static org.junit.jupiter.api.Assertions.*;
import java.util.*;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

/** Real MySQL identity semantics for canonical keys plus reviewed-registration guardrails. */
@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class KnowledgeNormalizationIntegrationTest {
    private final JsonMapper mapper=JsonMapper.builder().build();
    private static final String VERSION="norm-knowledge";
    // NFD decomposition of "café": the canonical key must collapse to NFC before uniqueness applies.
    private static final String CAFE_NFD="cafe\u0301";
    @Test void normalizationAndRegistrationGuards() {
        assertEquals("don't",KnowledgeConcepts.canonicalKey("  don't \t "));
        assertEquals("café",KnowledgeConcepts.canonicalKey(CAFE_NFD));
        assertEquals("look after",KnowledgeConcepts.canonicalKey("look  after"));
        assertEquals("well-known",KnowledgeConcepts.canonicalKey("well-known"));
        assertEquals("Bank",KnowledgeConcepts.canonicalKey("Bank"));
        assertThrows(KnowledgeConcepts.Failure.class,()->KnowledgeConcepts.canonicalKey("   "));
        assertThrows(KnowledgeConcepts.Failure.class,()->KnowledgeConcepts.canonicalKey(null));
        assertThrows(KnowledgeConcepts.Failure.class,()->KnowledgeConcepts.canonicalKey("x".repeat(256)));
        assertEquals(255,KnowledgeConcepts.canonicalKey("x".repeat(255)).codePoints().count());
        var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0");
        try {
            var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
            admin.update("INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES (?,?,?,?)","norm-bank-upper","vocabulary","Bank","sense");
            admin.update("INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES (?,?,?,?)","norm-bank-lower","vocabulary","bank","sense");
            assertEquals(1,admin.queryForObject("SELECT COUNT(*) FROM knowledge_concept WHERE canonical_key='bank' AND kind='vocabulary'",Integer.class),"binary collation must distinguish case");
            fixtureLesson(admin);
            var cli=app.getBean(KnowledgeRegistrationCli.class);
            String revision=UUID.randomUUID().toString(),occurrence=UUID.randomUUID().toString();
            assertEquals("REGISTERED",cli.register(mapper.readTree(conceptRequest("norm-cafe",CAFE_NFD,revision))).get("code"));
            assertEquals("café",admin.queryForObject("SELECT canonical_key FROM knowledge_concept WHERE id='norm-cafe'",String.class));
            assertThrows(DuplicateKeyException.class,()->cli.register(mapper.readTree(conceptRequest("norm-cafe-2"," café ",UUID.randomUUID().toString()))),"NFC-equivalent keys must collide under the same kind and sense");
            assertThrows(KnowledgeConcepts.Failure.class,()->cli.register(mapper.readTree("""
                {"versionId":"%s","reviewer":"x","concepts":[{"id":"norm-empty","kind":"vocabulary","canonicalKey":"   ","senseKey":"s"}]}
                """.formatted(VERSION))));
            assertThrows(KnowledgeConcepts.Failure.class,()->cli.register(mapper.readTree("""
                {"versionId":"%s","reviewer":"x","concepts":[{"id":"norm-kind","kind":"phrase","canonicalKey":"look","senseKey":"s"}]}
                """.formatted(VERSION))));
            assertThrows(KnowledgeConcepts.Failure.class,()->cli.register(mapper.readTree("""
                {"versionId":"%s","reviewer":"x","concepts":[{"id":"norm-pending","kind":"vocabulary","canonicalKey":"pending","senseKey":"s",
                  "revisions":[{"revisionNo":1,"displayName":"p","explanation":"p","reviewStatus":"pending_review"}]}]}
                """.formatted(VERSION))));
            assertThrows(KnowledgeConcepts.Failure.class,()->cli.register(mapper.readTree("""
                {"versionId":"%s","reviewer":"x","occurrences":[{"revisionId":"%s","scope":"paragraph","paragraphId":"%s-p1","sentenceId":"%s-s1","usage":{}}]}
                """.formatted(VERSION,revision,VERSION,VERSION))));
            assertThrows(KnowledgeConcepts.Failure.class,()->cli.register(mapper.readTree("""
                {"versionId":"%s","reviewer":"x","occurrences":[{"revisionId":"%s","scope":"sentence","sentenceId":"fixture-other-sentence","usage":{}}]}
                """.formatted(VERSION,revision))));
            String contextRevision=UUID.randomUUID().toString();
            assertEquals("REGISTERED",cli.register(mapper.readTree(contextRequest(contextRevision,occurrence))).get("code"));
            assertThrows(DataAccessException.class,()->admin.update("UPDATE knowledge_projection SET relations_sha256='0' WHERE version_id=?",VERSION));
            assertThrows(DataAccessException.class,()->admin.update("INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,usage_json) VALUES (?,?,?,?,?,'lesson','{}')",UUID.randomUUID().toString(),"norm-ctx",contextRevision,"norm-knowledge",VERSION));
            assertThrows(DataAccessException.class,()->admin.update("DELETE FROM knowledge_occurrence WHERE id=?",occurrence));
        } finally {app.close();}
    }
    private String conceptRequest(String id,String rawKey,String revision) {
        return """
            {"versionId":"%s","reviewer":"automation-normalization",
             "concepts":[{"id":"%s","kind":"vocabulary","canonicalKey":%s,"senseKey":"sense",
               "revisions":[{"id":"%s","revisionNo":1,"displayName":"café","explanation":"coffee","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]}]}
            """.formatted(VERSION,id,mapper.writeValueAsString(rawKey),revision);
    }
    private String contextRequest(String revision,String occurrence) {
        return """
            {"versionId":"%s","reviewer":"automation-normalization",
             "concepts":[{"id":"norm-ctx","kind":"grammar","canonicalKey":"there is","senseKey":"existence",
               "revisions":[{"id":"%s","revisionNo":1,"displayName":"there is","explanation":"existence pattern","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]}],
             "occurrences":[{"id":"%s","revisionId":"%s","scope":"sentence","sentenceId":"%s-s1","usage":{"gloss":"存在"}}]}
            """.formatted(VERSION,revision,occurrence,revision,VERSION);
    }
    private void fixtureLesson(JdbcTemplate admin) {
        admin.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES ('norm-knowledge-license','original','self-authored normalization fixture','confirmed','{}')");
        admin.update("INSERT INTO lesson(id,slug,kind,availability) VALUES (?,?, 'original_demo','available')",VERSION,VERSION);
        admin.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,publication_state,release_ready) VALUES (?,?,1,?,?,?,?,'published',TRUE)",
                VERSION,VERSION,"norm-knowledge-license","0".repeat(64),"0".repeat(64),"{}");
        String paragraphIdentity=java.util.UUID.randomUUID().toString();
        admin.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",paragraphIdentity,VERSION,paragraphIdentity);
        admin.update("INSERT INTO paragraph(id,version_id,stable_key,sequence_no,lesson_id,identity_id) VALUES (?,?,?,1,?,?)",VERSION+"-p1",VERSION,"paragraph-1",VERSION,paragraphIdentity);
        byte[] tone;
        try {tone=java.nio.file.Files.readAllBytes(java.nio.file.Path.of(Objects.requireNonNull(System.getenv("NORTHSTAR_TEST_AUDIO"))));}
        catch(Exception error) {throw new IllegalStateException(error);}
        for(int n=1;n<=2;n++) {
            String key=VERSION+"/sounds/tone-"+n+".mp3";
            String identity=java.util.UUID.randomUUID().toString();
            admin.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,VERSION,identity);
            try {
                java.nio.file.Path target=java.nio.file.Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"),key);
                java.nio.file.Files.createDirectories(target.getParent());java.nio.file.Files.write(target,tone);
            } catch(Exception error) {throw new IllegalStateException(error);}
            admin.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,'original_tts',?,'audio/mpeg',?,2000,?,'ready')",
                    VERSION+"-a"+n,VERSION,"norm-knowledge-license",key,tone.length,local.northstar.catalog.ContentPackage.sha256(tone));
            admin.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,?,?,'Tester',?,'测试句','本地预置讲解','test',?,0,2000,?,?)",
                    VERSION+"-s"+n,VERSION,VERSION,"line-"+n,n,"There is a test sentence "+n+".",VERSION+"-a"+n,VERSION+"-p1",identity);
        }
    }
}
