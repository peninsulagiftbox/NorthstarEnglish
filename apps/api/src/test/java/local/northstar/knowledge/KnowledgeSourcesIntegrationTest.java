package local.northstar.knowledge;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.time.*;
import java.util.*;
import local.northstar.NorthstarApplication;
import local.northstar.exercise.QuizSets;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Frozen registration feeds per-attempt knowledge evidence; browsing honors lesson visibility on real MySQL. */
@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class KnowledgeSourcesIntegrationTest {
    private static final String A="fixture-a",B="fixture-b",C="fixture-c",AV="fixture-a-v1",BV="fixture-b-v1",CV="fixture-c-v1";
    private static final String GUARD="Frozen knowledge relations are immutable";
    private static final String[] TRIGGERS={"knowledge_projection_no_insert","knowledge_projection_no_update","knowledge_projection_no_delete",
        "occurrence_no_insert","occurrence_no_update","occurrence_no_delete","legacy_link_no_insert","legacy_link_no_update","legacy_link_no_delete",
        "exercise_sentence_no_insert","exercise_sentence_no_update","exercise_sentence_no_delete",
        "exercise_knowledge_no_insert","exercise_knowledge_no_update","exercise_knowledge_no_delete",
        "knowledge_revision_no_update","knowledge_revision_no_delete",
        "attempt_knowledge_no_update","attempt_knowledge_no_delete",
        "quiz_set_no_delete","quiz_item_no_delete"};
    private final JsonMapper mapper=JsonMapper.builder().build();
    private final HttpClient http=HttpClient.newHttpClient();
    private JdbcTemplate admin;private String base;
    private String demoVersion,demoSentence,demoEvent,readEvent,quizEvent;

    @Test void registeredRelationsFreezeIntoAttemptEvidenceAndVisibility() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        assertNotEquals("3308",System.getenv("MYSQL_PORT"));
        var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0");
        try {
            admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"),admin.queryForObject("SELECT @@server_uuid",String.class));
            base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            fixture(A,2,12,Map.of(3,"The bank opens beside the garden gate.",7,"Parents look after the community garden.",
                9,"There is a bench near the gate.",12,"In spite of the rain, we met."));
            fixture(B,3,24,Map.of(5,"We sat on the bank of the river.",6,"The bank keeps the town's money safe."));
            negativeFixture();
            String setHash=quizSet();
            var cli=app.getBean(KnowledgeRegistrationCli.class);
            assertEquals("REGISTERED",cli.register(mapper.readTree(registerA())).get("code"));
            assertEquals("ALREADY_FROZEN",cli.register(mapper.readTree(registerA())).get("code"));
            assertEquals("REGISTERED",cli.register(mapper.readTree(registerB())).get("code"));
            String[] demo=demoContext();
            demoVersion=demo[0];demoSentence=demo[2];
            assertEquals("REGISTERED",cli.register(mapper.readTree(registerC(demo))).get("code"));
            assertTrue(admin.queryForObject("SELECT frozen FROM knowledge_projection WHERE version_id=?",Boolean.class,AV));
            sqlNegatives();
            browse();
            demoDictation();
            readingAttempt();
            quizSubmit(setHash);
            invalidQuizRollsBack();
            immutability();
        } finally {
            app.close();
            cleanup();
        }
    }

    private String[] demoContext() {
        String version=admin.queryForObject("SELECT version_id FROM knowledge_point WHERE lesson_id='demo-01' ORDER BY version_id DESC,id LIMIT 1",String.class);
        var point=admin.queryForMap("SELECT id,sentence_id FROM knowledge_point WHERE version_id=? ORDER BY id LIMIT 1",version);
        String sentence=point.get("sentence_id").toString();
        assertEquals(1,admin.queryForObject("SELECT COUNT(*) FROM exercise WHERE id=? AND kind='dictation' AND version_id=?",Integer.class,sentence+"-dictation",version),
            "seeded demo dictation exercise must exist");
        return new String[]{version,point.get("id").toString(),sentence};
    }

    private void sqlNegatives() {
        assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM knowledge_projection WHERE version_id=?",Integer.class,CV));
        assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update(
            "INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,usage_json) VALUES ('oc-fk-bad','kn-fk','rv-fk',?,?,'lesson',?,'{}')",C,CV,CV+"-p1"),
            "lesson scope must reject a bound paragraph");
        assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update(
            "INSERT INTO legacy_knowledge_link(knowledge_point_id,version_id,sentence_id,occurrence_id,concept_id,mapping_basis,reviewer) VALUES ('kc-kp-1',?,?,'oc-fk-s1','kn-fk','manual_review','automation-sources')",CV,CV+"-s2"),
            "legacy link must stay on the knowledge point sentence");
        assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update(
            "INSERT INTO exercise_knowledge(exercise_id,occurrence_id,version_id,concept_id,role) VALUES ('kc-quiz','oc-bank-a',?,'kn-bank-fin','target')",CV),
            "exercise knowledge must reject cross-version occurrences");
        assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM exercise_knowledge WHERE version_id=?",Integer.class,CV));
    }

    private void browse() throws Exception {
        var allResponse=send("/knowledge/concepts?limit=100",null);
        assertEquals(200,allResponse.statusCode(),allResponse.body());
        var all=json(allResponse);
        var ids=new ArrayList<String>();all.path("items").forEach(i->ids.add(i.path("id").asText()));
        assertEquals(List.of("kn-bank-fin","kn-bank-riv","kn-beside","kn-inspite-c","kn-inspite-p","kn-look-after","kn-there-is"),ids);
        assertEquals(2,find(all,"kn-bank-fin").path("lessonCount").asInt());
        var page=json(send("/knowledge/concepts?limit=1",null));
        assertEquals("kn-bank-fin",page.path("items").get(0).path("id").asText());
        assertEquals("kn-bank-fin",page.path("nextCursor").asText());
        assertEquals("kn-bank-riv",json(send("/knowledge/concepts?limit=1&cursor=kn-bank-fin",null)).path("items").get(0).path("id").asText());
        var detail=json(send("/knowledge/concepts/kn-bank-fin",null));
        assertEquals(1,detail.path("revisionNo").asInt());assertEquals(2,detail.path("lessons").size());
        var occ=json(send("/knowledge/concepts/kn-bank-fin/occurrences",null));
        assertEquals(2,occ.path("items").size());
        assertEquals("The bank opens beside the garden gate.",occ.path("items").get(0).path("sentenceText").asText());
        assertEquals(2,occ.path("items").get(0).path("exerciseCount").asInt());
        var thereResponse=send("/knowledge/concepts/kn-there-is/occurrences",null);
        assertEquals(200,thereResponse.statusCode(),thereResponse.body());
        var there=json(thereResponse);
        assertEquals(2,there.path("items").size());
        assertFalse(there.path("items").get(0).has("sentenceText"),"lesson-scope occurrence must not expose sentence fields");
        assertTrue(there.path("items").get(1).has("sentenceText"),thereResponse.body());
        admin.update("UPDATE lesson SET availability='withdrawn' WHERE id=?",B);
        var hidden=json(send("/knowledge/concepts/kn-bank-fin/occurrences",null)).path("items").get(1);
        assertTrue(hidden.path("restricted").asBoolean());
        assertFalse(hidden.has("usage"));assertFalse(hidden.has("title"));assertFalse(hidden.has("sentenceText"));assertFalse(hidden.has("exerciseCount"));
        assertEquals(1,json(send("/knowledge/concepts?limit=100",null)).path("items").valueStream().filter(i->i.path("id").asText().equals("kn-bank-fin")).findFirst().orElseThrow().path("lessonCount").asInt());
        admin.update("UPDATE lesson SET availability='available' WHERE id=?",B);
    }

    private void demoDictation() throws Exception {
        demoEvent=UUID.randomUUID().toString();
        String body="""
            {"eventId":"%s","lessonId":"demo-01","versionId":"%s","sentenceId":"%s","text":"zz qqq","answerExposed":false,"audioPlayed":true,"clientOccurredAt":"%s"}
            """
            .formatted(demoEvent,demoVersion,demoSentence,Instant.now().toString());
        var first=json(send("/exercises/"+demoSentence+"-dictation/attempts",body));
        assertFalse(first.path("result").path("correct").asBoolean());
        var rows=attemptRows(first.path("attemptId").asText());
        assertEquals(1,rows.size());assertEquals("target",rows.get(0).get("role"));
        var snapshot=mapper.readTree(rows.get(0).get("source_json").toString());
        assertEquals(demoEvent,snapshot.path("eventId").asText());assertEquals("beside",snapshot.path("concept").path("canonicalKey").asText());
        var replay=json(send("/exercises/"+demoSentence+"-dictation/attempts",body));
        assertEquals(first.path("attemptId").asText(),replay.path("attemptId").asText());
        assertEquals(1,admin.queryForObject("SELECT COUNT(*) FROM command_receipt WHERE event_id=?",Integer.class,demoEvent));
        assertEquals(1,attemptRows(first.path("attemptId").asText()).size());
    }

    private void readingAttempt() throws Exception {
        readEvent=UUID.randomUUID().toString();
        var response=json(send("/reading/ka-read-1/attempts","""
            {"eventId":"%s","lessonId":"%s","versionId":"%s","optionId":"ka-a","clientOccurredAt":"%s"}
            """
            .formatted(readEvent,A,AV,Instant.now().toString())));
        assertEquals("beside 表示在旁边。",response.path("result").path("explanation").asText(),"explanation must come from the frozen question payload");
        var rows=attemptRows(response.path("attemptId").asText());
        assertEquals(2,rows.size());
        var snapshot=mapper.readTree(rows.get(0).get("source_json").toString());
        assertEquals("bank",snapshot.path("concept").path("canonicalKey").asText());assertEquals(1,snapshot.path("concept").path("revisionNo").asInt());
        assertEquals(2,snapshot.path("sourceSentences").size());assertEquals("sentence",snapshot.path("occurrence").path("scope").asText());
        assertEquals(Set.of("target","support"),Set.of(rows.get(0).get("role"),rows.get(1).get("role")));
    }

    private void quizSubmit(String setHash) throws Exception {
        quizEvent=UUID.randomUUID().toString();
        var body=mapper.createObjectNode().put("protocolVersion","quiz-submit-v2").put("lessonId",A).put("versionId",AV)
            .put("setId","set-a").put("setHash",setHash).put("eventId",quizEvent).put("clientOccurredAt",Instant.now().toString())
            .put("conceptId","client-forged-concept");
        body.putObject("answers").put("ka-quiz-1","ka1-a").put("ka-quiz-2","ka2-b").put("ka-quiz-3","ka3-b");
        var response=json(send("/quiz/sets/set-a/attempts",mapper.writeValueAsString(body)));
        assertEquals(2,response.path("correctCount").asInt());assertEquals(3,response.path("totalCount").asInt());
        String runId=admin.queryForObject("SELECT id FROM quiz_run WHERE event_id=?",String.class,quizEvent);
        assertTrue(QuizSets.verifiedRun(admin,runId));
        String child=UUID.nameUUIDFromBytes((quizEvent+":ka-quiz-1").getBytes(java.nio.charset.StandardCharsets.UTF_8)).toString();
        String attemptId=admin.queryForObject("SELECT id FROM exercise_attempt WHERE event_id=?",String.class,child);
        assertEquals(2,attemptRows(attemptId).size(),"wrong quiz answer on the two-target exercise freezes both relations");
        assertEquals(4,admin.queryForObject("SELECT COUNT(*) FROM attempt_knowledge ak JOIN exercise_attempt a ON a.id=ak.attempt_id "
            +"JOIN quiz_answer qa ON qa.attempt_id=a.id JOIN quiz_run r ON r.id=qa.run_id WHERE r.event_id=?",Integer.class,quizEvent));
        var report=json(send("/reports?lessonId="+A+"&versionId="+AV,null));
        assertEquals(1,report.path("metrics").path("quiz").path("verifiedRuns").asInt());
        assertTrue(report.path("quizRuns").get(0).path("verified").asBoolean());
    }

    private void invalidQuizRollsBack() throws Exception {
        String event=UUID.randomUUID().toString();
        var body=mapper.createObjectNode().put("protocolVersion","quiz-submit-v2").put("lessonId",A).put("versionId",AV)
            .put("setId","set-a").put("setHash",quizSetHash()).put("eventId",event).put("clientOccurredAt",Instant.now().toString());
        body.putObject("answers").put("ka-quiz-1","ka1-zzz").put("ka-quiz-2","ka2-b").put("ka-quiz-3","ka3-b");
        assertEquals(422,send("/quiz/sets/set-a/attempts",mapper.writeValueAsString(body)).statusCode());
        assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE event_id LIKE ?",Integer.class,event+"%"));
        assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM command_receipt WHERE event_id=?",Integer.class,event));
        assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM quiz_run WHERE event_id=?",Integer.class,event));
    }

    private void immutability() throws Exception {
        String evidence="SELECT ak.attempt_id,ak.occurrence_id,ak.role,CAST(ak.source_json AS CHAR CHARACTER SET utf8mb4) AS source_json,ak.source_sha256 "
            +"FROM attempt_knowledge ak JOIN exercise_attempt a ON a.id=ak.attempt_id WHERE a.event_id=? ORDER BY ak.occurrence_id";
        var before=admin.queryForList(evidence,demoEvent);
        admin.update("INSERT INTO knowledge_concept_revision(id,concept_id,revision_no,display_name,explanation,source_ref,reviewer,review_status,reviewed_at) "
            +"VALUES ('rv-bank-fin-2','kn-bank-fin',2,'bank — revised sense','revised explanation','fixture','automation-sources','confirmed',UTC_TIMESTAMP(3))");
        assertEquals(2,json(send("/knowledge/concepts/kn-bank-fin",null)).path("revisionNo").asInt());
        assertEquals(before,admin.queryForList(evidence,demoEvent),"attempt evidence must stay byte-identical after a newer revision");
    }

    private List<Map<String,Object>> attemptRows(String attemptId) {
        return admin.queryForList("SELECT role,CAST(source_json AS CHAR CHARACTER SET utf8mb4) AS source_json FROM attempt_knowledge WHERE attempt_id=? ORDER BY occurrence_id",attemptId);
    }

    private String registerA() {
        return """
            {"versionId":"%s","reviewer":"automation-sources","concepts":[
              {"id":"kn-bank-fin","kind":"vocabulary","canonicalKey":"bank","senseKey":"money","revisions":[{"id":"rv-bank-fin","revisionNo":1,"displayName":"bank — financial institution","explanation":"存款与银行机构含义","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]},
              {"id":"kn-look-after","kind":"collocation","canonicalKey":"look after","senseKey":"care","revisions":[{"id":"rv-look-after","revisionNo":1,"displayName":"look after","explanation":"照料","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]},
              {"id":"kn-there-is","kind":"pattern","canonicalKey":"there is","senseKey":"existence","revisions":[{"id":"rv-there-is","revisionNo":1,"displayName":"there is","explanation":"存在句型","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]},
              {"id":"kn-inspite-c","kind":"collocation","canonicalKey":"in spite of","senseKey":"despite","revisions":[{"id":"rv-inspite-c","revisionNo":1,"displayName":"in spite of","explanation":"尽管","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]},
              {"id":"kn-inspite-p","kind":"pattern","canonicalKey":"in spite of","senseKey":"concession","revisions":[{"id":"rv-inspite-p","revisionNo":1,"displayName":"in spite of","explanation":"让步结构","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]}],
             "occurrences":[
              {"id":"oc-bank-a","revisionId":"rv-bank-fin","scope":"sentence","sentenceId":"%s-s3","usage":{"note":"opens beside the garden gate"}},
              {"id":"oc-look-a","revisionId":"rv-look-after","scope":"sentence","sentenceId":"%s-s7","usage":{}},
              {"id":"oc-there-is-s9","revisionId":"rv-there-is","scope":"sentence","sentenceId":"%s-s9","usage":{}},
              {"id":"oc-there-is-lesson","revisionId":"rv-there-is","scope":"lesson","usage":{"note":"whole lesson"}},
              {"id":"oc-inspite-c","revisionId":"rv-inspite-c","scope":"sentence","sentenceId":"%s-s12","usage":{}},
              {"id":"oc-inspite-p","revisionId":"rv-inspite-p","scope":"sentence","sentenceId":"%s-s12","usage":{}}],
             "exerciseSentences":[
              {"exerciseId":"ka-read-1","sentenceId":"%s-s3","role":"primary"},{"exerciseId":"ka-read-1","sentenceId":"%s-s4","role":"supporting"},
              {"exerciseId":"ka-quiz-1","sentenceId":"%s-s9","role":"primary"},{"exerciseId":"ka-quiz-1","sentenceId":"%s-s3","role":"supporting"},
              {"exerciseId":"ka-quiz-2","sentenceId":"%s-s7","role":"primary"},{"exerciseId":"ka-quiz-3","sentenceId":"%s-s12","role":"primary"}],
             "exerciseKnowledge":[
              {"exerciseId":"ka-read-1","occurrenceId":"oc-bank-a","role":"target"},{"exerciseId":"ka-read-1","occurrenceId":"oc-there-is-lesson","role":"support"},
              {"exerciseId":"ka-quiz-1","occurrenceId":"oc-bank-a","role":"target"},{"exerciseId":"ka-quiz-1","occurrenceId":"oc-there-is-s9","role":"target"},
              {"exerciseId":"ka-quiz-2","occurrenceId":"oc-look-a","role":"target"},{"exerciseId":"ka-quiz-3","occurrenceId":"oc-inspite-c","role":"target"}]}
            """.formatted(AV,AV,AV,AV,AV,AV,AV,AV,AV,AV,AV,AV);
    }

    private String registerB() {
        return """
            {"versionId":"%s","reviewer":"automation-sources","concepts":[
              {"id":"kn-bank-riv","kind":"vocabulary","canonicalKey":"bank","senseKey":"river-edge","revisions":[{"id":"rv-bank-riv","revisionNo":1,"displayName":"bank — riverside","explanation":"河岸含义","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]}],
             "occurrences":[
              {"id":"oc-bank-b-fin","revisionId":"rv-bank-fin","scope":"sentence","sentenceId":"%s-s6","usage":{}},
              {"id":"oc-bank-riv","revisionId":"rv-bank-riv","scope":"sentence","sentenceId":"%s-s5","usage":{}}],
             "exerciseSentences":[{"exerciseId":"kb-read-1","sentenceId":"%s-s5","role":"primary"}],
             "exerciseKnowledge":[{"exerciseId":"kb-read-1","occurrenceId":"oc-bank-riv","role":"target"}]}
            """.formatted(BV,BV,BV,BV);
    }

    private String registerC(String[] demo) {
        return """
            {"versionId":"%s","reviewer":"automation-sources","concepts":[
              {"id":"kn-beside","kind":"vocabulary","canonicalKey":"beside","senseKey":"next-to","revisions":[{"id":"rv-beside","revisionNo":1,"displayName":"beside","explanation":"在旁边","sourceRef":"fixture","reviewStatus":"confirmed","reviewedAt":"2026-10-31T00:00:00Z"}]}],
             "occurrences":[{"id":"oc-beside-demo","revisionId":"rv-beside","scope":"sentence","sentenceId":"%s","usage":{}}],
             "legacyLinks":[{"knowledgePointId":"%s","occurrenceId":"oc-beside-demo","mappingBasis":"synthetic_fixture_reviewed"}],
             "exerciseSentences":[{"exerciseId":"%s-dictation","sentenceId":"%s","role":"primary"}],
             "exerciseKnowledge":[{"exerciseId":"%s-dictation","occurrenceId":"oc-beside-demo","role":"target"}]}
            """.formatted(demo[0],demo[2],demo[1],demo[2],demo[2],demo[2]);
    }

    private void fixture(String id,int paragraphs,int count,Map<Integer,String> texts) throws Exception {
        byte[] tone=java.nio.file.Files.readAllBytes(java.nio.file.Path.of(Objects.requireNonNull(System.getenv("NORTHSTAR_TEST_AUDIO"))));
        admin.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,'original',?,'confirmed','{}')",id+"-license","self-authored knowledge fixture "+id+" text and synthetic tone");
        admin.update("INSERT INTO lesson(id,slug,kind,availability) VALUES (?,?,'original_demo','available')",id,id);
        String version=id+"-v1";
        var payload=mapper.createObjectNode().put("id",id).put("versionId",version).put("title","Knowledge Fixture "+id.toUpperCase())
            .put("explanationLabel","本地预置测试讲解").put("audioLabel","原创合成测试音 · 非朗读/非发音示范");
        String hash=local.northstar.catalog.ContentPackage.sha256(payload.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
        admin.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,publication_state,release_ready) VALUES (?,?,1,?,?,?,?,'published',TRUE)",
            version,id,id+"-license",hash,hash,payload.toString());
        admin.update("UPDATE lesson SET current_version_id=? WHERE id=?",version,id);
        for(int n=1;n<=paragraphs;n++) {
            String identity=UUID.randomUUID().toString();
            admin.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,id,identity);
            admin.update("INSERT INTO paragraph(id,version_id,stable_key,sequence_no,lesson_id,identity_id) VALUES (?,?,?,?,?,?)",version+"-p"+n,version,"paragraph-"+n,n,id,identity);
        }
        for(int n=1;n<=count;n++) {
            String identity=UUID.randomUUID().toString();
            admin.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,id,identity);
            String asset=version+"-a"+n,key=id+"/version-1/sounds/utterance-"+n+".mp3";
            java.nio.file.Path target=java.nio.file.Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"),key);
            java.nio.file.Files.createDirectories(target.getParent());java.nio.file.Files.write(target,tone);
            admin.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,'original_tts',?,'audio/mpeg',?,2000,?,'ready')",
                asset,version,id+"-license",key,tone.length,local.northstar.catalog.ContentPackage.sha256(tone));
            admin.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,?,?,'Tester',?,'原创测试句','本地预置讲解','test',?,0,2000,?,?)",
                version+"-s"+n,id,version,"line-"+n,n,texts.getOrDefault(n,"Test line "+n+" of "+id+"."),asset,version+"-p"+((n-1)/(count/paragraphs)+1),identity);
        }
    }

    private void negativeFixture() throws Exception {
        fixture(C,1,2,Map.of());
        admin.update("UPDATE content_license SET review_status='pending_review' WHERE id=?",C+"-license");
        admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('kc-kp-1',?,?,?,'fk','fk','fk','fk')",C,CV,CV+"-s1");
        admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('kc-quiz',?,?,?,'quiz_choice','quiz_choice_v1')",C,CV,CV+"-s1");
        admin.update("INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES ('kn-fk','vocabulary','fkw','sense')");
        admin.update("INSERT INTO knowledge_concept_revision(id,concept_id,revision_no,display_name,explanation,source_ref,reviewer,review_status,reviewed_at) VALUES ('rv-fk','kn-fk',1,'fkw','x','fixture','automation-sources','confirmed',UTC_TIMESTAMP(3))");
        admin.update("INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json) VALUES ('oc-fk-s1','kn-fk','rv-fk',?,?,'sentence',?,?,'{}')",C,CV,CV+"-p1",CV+"-s1");
        admin.update("INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json) VALUES ('oc-fk-s2','kn-fk','rv-fk',?,?,'sentence',?,?,'{}')",C,CV,CV+"-p1",CV+"-s2");
    }

    private void exercises() {
        admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('ka-kp-3',?,?,?,'bank','bank','bank','bank')",A,AV,AV+"-s3");
        admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('ka-kp-7',?,?,?,'look after','look after','look after','look after')",A,AV,AV+"-s7");
        admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('ka-kp-9',?,?,?,'there is','there is','there is','there is')",A,AV,AV+"-s9");
        admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('ka-kp-12',?,?,?,'in spite of','in spite of','in spite of','in spite of')",A,AV,AV+"-s12");
        admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES ('kb-kp-5',?,?,?,'bank','bank','bank','bank')",B,BV,BV+"-s5");
        admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('ka-read-1',?,?,?,'reading_choice','reading_choice_v1')",A,AV,AV+"-s3");
        admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('ka-quiz-1',?,?,?,'quiz_choice','quiz_choice_v1')",A,AV,AV+"-s9");
        admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('ka-quiz-2',?,?,?,'quiz_choice','quiz_choice_v1')",A,AV,AV+"-s7");
        admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('ka-quiz-3',?,?,?,'quiz_choice','quiz_choice_v1')",A,AV,AV+"-s12");
        admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES ('kb-read-1',?,?,?,'reading_choice','reading_choice_v1')",B,BV,BV+"-s5");
        readingQuestion("ka-read-1","ka-kp-3",AV,"s3","ka-b","beside 表示在旁边。","ka-a","ka-b","ka-c");
        readingQuestion("kb-read-1","kb-kp-5",BV,"s5","kb-a","river bank 表示河岸。","kb-a","kb-b","kb-c");
        quizQuestion("ka-quiz-1","ka-kp-9",AV,"s9","ka1-a","ka1-b","ka1-c","ka1-b");
        quizQuestion("ka-quiz-2","ka-kp-7",AV,"s7","ka2-a","ka2-b","ka2-c","ka2-b");
        quizQuestion("ka-quiz-3","ka-kp-12",AV,"s12","ka3-a","ka3-b","ka3-c","ka3-b");
    }

    private void readingQuestion(String exercise,String point,String version,String suffix,String answerKey,String explanation,String... options) {
        var payload=mapper.createObjectNode().put("id",exercise).put("prompt","选择正确含义").put("answerKey",answerKey).put("explanation",explanation);
        var array=payload.putArray("options");
        for(String option:options)array.add(mapper.createObjectNode().put("id",option).put("text",option+" text"));
        admin.update("INSERT INTO reading_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",exercise,version,version+"-"+suffix,point,payload.toString());
        for(String option:options)admin.update("INSERT INTO reading_option(id,exercise_id) VALUES (?,?)",option,exercise);
    }

    private void quizQuestion(String exercise,String point,String version,String suffix,String... options) {
        var payload=mapper.createObjectNode().put("id",exercise).put("prompt","选择正确答案").put("answerKey",options[3]);
        var array=payload.putArray("options");
        for(int i=0;i<3;i++)array.add(mapper.createObjectNode().put("id",options[i]).put("text","option "+(char)('a'+i)));
        admin.update("INSERT INTO quiz_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",exercise,version,version+"-"+suffix,point,payload.toString());
    }

    private String quizSet() {
        exercises();
        admin.update("INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES ('set-a',?,'practice','quiz_choice_v1','version_content')",AV);
        List<String> items=List.of("ka-quiz-1","ka-quiz-2","ka-quiz-3");
        for(int i=0;i<items.size();i++) {
            String exercise=items.get(i);
            var row=admin.queryForMap("SELECT sentence_id,knowledge_point_id FROM quiz_question WHERE exercise_id=?",exercise);
            String sentence=row.get("sentence_id").toString(),point=row.get("knowledge_point_id").toString();
            String questionJson=mapper.writeValueAsString(mapper.readTree(admin.queryForObject("SELECT payload_json FROM quiz_question WHERE exercise_id=?",String.class,exercise)));
            admin.update("INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) VALUES ('set-a',?,?,?,?,?,?,?)",
                exercise,AV,sentence,point,i+1,questionJson,QuizSets.itemHash(Map.of("exercise_id",exercise,"ordinal",i+1,"sentence_id",sentence,"knowledge_point_id",point,"question_text",questionJson)));
            String stored=admin.queryForObject("SELECT CAST(question_json AS CHAR CHARACTER SET utf8mb4) FROM exercise_set_item WHERE set_id='set-a' AND exercise_id=?",String.class,exercise);
            admin.update("UPDATE exercise_set_item SET item_hash=? WHERE set_id='set-a' AND exercise_id=?",
                QuizSets.itemHash(Map.of("exercise_id",exercise,"ordinal",i+1,"sentence_id",sentence,"knowledge_point_id",point,"question_text",stored)),exercise);
        }
        String setHash=quizSetHash();
        admin.update("UPDATE exercise_set SET set_hash=?,frozen=TRUE WHERE id='set-a'",setHash);
        return setHash;
    }

    private String quizSetHash() {
        var items=admin.queryForList("SELECT i.*,CAST(i.question_json AS CHAR CHARACTER SET utf8mb4) AS question_text FROM exercise_set_item i WHERE set_id='set-a' ORDER BY ordinal");
        return QuizSets.setHash(AV,null,items);
    }

    private void cleanup() {
        for(var trigger:TRIGGERS)admin.execute("DROP TRIGGER IF EXISTS "+trigger);
        for(String version:List.of(AV,BV,CV)) {
            learningCleanup("a.version_id='"+version+"'");
            admin.update("DELETE FROM quiz_run WHERE version_id=?",version);
            admin.update("DELETE FROM quiz_progress WHERE version_id=?",version);
        }
        if(demoEvent!=null)learningCleanup("a.event_id='"+demoEvent+"'");
        if(readEvent!=null)admin.update("DELETE FROM command_receipt WHERE event_id=?",readEvent);
        if(quizEvent!=null) {
            admin.update("DELETE FROM command_receipt WHERE event_id=?",quizEvent);
            for(var exercise:List.of("ka-quiz-1","ka-quiz-2","ka-quiz-3"))
                admin.update("DELETE FROM command_receipt WHERE event_id=?",UUID.nameUUIDFromBytes((quizEvent+":"+exercise).getBytes(java.nio.charset.StandardCharsets.UTF_8)).toString());
        }
        admin.update("DELETE FROM reading_progress WHERE exercise_id IN ('ka-read-1','kb-read-1')");
        admin.update("DELETE FROM review_item WHERE id IN ('ka-kp-3-reading','kb-kp-5-reading')");
        if(demoSentence!=null) {
            String item=demoSentence+"-review";
            var prior=admin.queryForList("SELECT due_at,reps,row_version FROM review_item WHERE id=?",item);
            if(prior.size()==1)admin.update("UPDATE review_item SET due_at=?,reps=?,row_version=? WHERE id=?",prior.get(0).get("due_at"),prior.get(0).get("reps"),prior.get(0).get("row_version"),item);
            else admin.update("DELETE FROM review_item WHERE id=?",item);
        }
        for(String version:List.of(AV,BV,CV)) {
            admin.update("DELETE FROM review_item WHERE version_id=?",version);
            admin.update("DELETE FROM exercise_knowledge WHERE version_id=?",version);
            admin.update("DELETE FROM exercise_sentence WHERE version_id=?",version);
            admin.update("DELETE FROM legacy_knowledge_link WHERE version_id=?",version);
            admin.update("DELETE FROM knowledge_occurrence WHERE version_id=?",version);
            admin.update("DELETE FROM knowledge_projection WHERE version_id=?",version);
            admin.update("DELETE FROM exercise_set_item WHERE version_id=?",version);
            admin.update("DELETE FROM quiz_question WHERE version_id=?",version);
            admin.update("DELETE FROM reading_option WHERE exercise_id IN (SELECT id FROM exercise WHERE version_id=?)",version);
            admin.update("DELETE FROM reading_question WHERE version_id=?",version);
            admin.update("DELETE FROM exercise WHERE version_id=?",version);
            admin.update("DELETE FROM knowledge_point WHERE version_id=?",version);
            admin.update("DELETE FROM exercise_set WHERE version_id=?",version);
        }
        if(demoVersion!=null) {
            admin.update("DELETE FROM exercise_knowledge WHERE version_id=?",demoVersion);
            admin.update("DELETE FROM exercise_sentence WHERE version_id=?",demoVersion);
            admin.update("DELETE l FROM legacy_knowledge_link l JOIN knowledge_point k ON k.id=l.knowledge_point_id WHERE k.version_id=?",demoVersion);
            admin.update("DELETE FROM knowledge_occurrence WHERE version_id=?",demoVersion);
            admin.update("DELETE FROM knowledge_projection WHERE version_id=?",demoVersion);
        }
        admin.update("DELETE r FROM knowledge_concept_revision r JOIN knowledge_concept c ON c.id=r.concept_id WHERE c.id IN ('kn-bank-fin','kn-bank-riv','kn-beside','kn-inspite-c','kn-inspite-p','kn-look-after','kn-there-is','kn-fk')");
        admin.update("DELETE FROM knowledge_concept WHERE id IN ('kn-bank-fin','kn-bank-riv','kn-beside','kn-inspite-c','kn-inspite-p','kn-look-after','kn-there-is','kn-fk')");
        for(String id:List.of(A,B,C)) {
            String version=id+"-v1";
            admin.update("UPDATE lesson SET current_version_id=NULL WHERE id=?",id);
            admin.update("DELETE FROM sentence WHERE lesson_version_id=?",version);
            admin.update("DELETE FROM sentence_identity WHERE lesson_id=?",id);
            admin.update("DELETE FROM audio_asset WHERE lesson_version_id=?",version);
            admin.update("DELETE FROM paragraph WHERE version_id=?",version);
            admin.update("DELETE FROM paragraph_identity WHERE lesson_id=?",id);
            admin.update("DELETE FROM lesson_version WHERE id=?",version);
            admin.update("DELETE FROM lesson WHERE id=?",id);
            admin.update("DELETE FROM content_license WHERE id=?",id+"-license");
        }
        recreateTriggers();
    }

    private void learningCleanup(String attemptWhere) {
        admin.update("DELETE ak FROM attempt_knowledge ak JOIN exercise_attempt a ON a.id=ak.attempt_id WHERE "+attemptWhere);
        for(var table:List.of("review_source","learning_evidence","reading_answer","quiz_run_item","quiz_answer"))
            admin.update("DELETE t FROM "+table+" t JOIN exercise_attempt a ON a.id=t.attempt_id WHERE "+attemptWhere);
        admin.update("DELETE FROM exercise_attempt WHERE "+attemptWhere.replace("a.",""));
    }

    private void recreateTriggers() {
        admin.execute("CREATE TRIGGER knowledge_revision_no_update BEFORE UPDATE ON knowledge_concept_revision FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Knowledge concept revisions are append-only'; END");
        admin.execute("CREATE TRIGGER knowledge_revision_no_delete BEFORE DELETE ON knowledge_concept_revision FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Knowledge concept revisions are append-only'; END");
        admin.execute("CREATE TRIGGER attempt_knowledge_no_update BEFORE UPDATE ON attempt_knowledge FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Attempt knowledge snapshots are immutable'; END");
        admin.execute("CREATE TRIGGER attempt_knowledge_no_delete BEFORE DELETE ON attempt_knowledge FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Attempt knowledge snapshots are immutable'; END");
        admin.execute("CREATE TRIGGER quiz_set_no_delete BEFORE DELETE ON exercise_set FOR EACH ROW BEGIN IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz set is immutable'; END IF; END");
        admin.execute("CREATE TRIGGER quiz_item_no_delete BEFORE DELETE ON exercise_set_item FOR EACH ROW BEGIN IF (SELECT frozen FROM exercise_set WHERE id=OLD.set_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz items are immutable'; END IF; END");
        admin.execute("""
            CREATE TRIGGER knowledge_projection_no_insert BEFORE INSERT ON knowledge_projection FOR EACH ROW
            BEGIN IF NEW.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Projection freezes only after relations are registered'; END IF; END""");
        admin.execute("""
            CREATE TRIGGER knowledge_projection_no_update BEFORE UPDATE ON knowledge_projection FOR EACH ROW
            BEGIN IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge projection is immutable'; END IF; END""");
        admin.execute("""
            CREATE TRIGGER knowledge_projection_no_delete BEFORE DELETE ON knowledge_projection FOR EACH ROW
            BEGIN IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen knowledge projection is immutable'; END IF; END""");
        admin.execute("CREATE TRIGGER occurrence_no_insert BEFORE INSERT ON knowledge_occurrence FOR EACH ROW BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='"+GUARD+"'; END IF; END");
        admin.execute("CREATE TRIGGER occurrence_no_update BEFORE UPDATE ON knowledge_occurrence FOR EACH ROW BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) OR (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='"+GUARD+"'; END IF; END");
        admin.execute("CREATE TRIGGER occurrence_no_delete BEFORE DELETE ON knowledge_occurrence FOR EACH ROW BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='"+GUARD+"'; END IF; END");
        for(var table:List.of("legacy_knowledge_link","exercise_sentence","exercise_knowledge")) {
            String stem=table.equals("legacy_knowledge_link")?"legacy_link":table;
            admin.execute("CREATE TRIGGER "+stem+"_no_insert BEFORE INSERT ON "+table+" FOR EACH ROW BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='"+GUARD+"'; END IF; END");
            admin.execute("CREATE TRIGGER "+stem+"_no_update BEFORE UPDATE ON "+table+" FOR EACH ROW BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) OR (SELECT frozen FROM knowledge_projection WHERE version_id=NEW.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='"+GUARD+"'; END IF; END");
            admin.execute("CREATE TRIGGER "+stem+"_no_delete BEFORE DELETE ON "+table+" FOR EACH ROW BEGIN IF (SELECT frozen FROM knowledge_projection WHERE version_id=OLD.version_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='"+GUARD+"'; END IF; END");
        }
    }

    private JsonNode find(JsonNode page,String id) {
        for(var item:page.path("items"))if(item.path("id").asText().equals(id))return item;
        throw new AssertionError("missing concept "+id);
    }

    private JsonNode json(HttpResponse<String> response) throws Exception {return mapper.readTree(response.body());}
    private HttpResponse<String> send(String path,String body) throws Exception {
        return http.send(HttpRequest.newBuilder(URI.create(base+path)).header("Origin","http://127.0.0.1:3196")
            .header("X-Northstar-Request","local-workspace").header("Content-Type","application/json")
            .method(body==null?"GET":"POST",body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body)).build(),HttpResponse.BodyHandlers.ofString());
    }
}
