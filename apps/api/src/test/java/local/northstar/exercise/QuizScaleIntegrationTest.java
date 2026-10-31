package local.northstar.exercise;
import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.time.*;
import java.util.*;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Real denominators at scale: 12- and 100-question sets submitted through the formal quiz-set API. */
@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class QuizScaleIntegrationTest {
    private final JsonMapper mapper=JsonMapper.builder().build();
    private final HttpClient client=HttpClient.newHttpClient();
    @Test void twelveQuestionSetSubmitsWithVerifiedRun() throws Exception {run(12);}
    @Test void hundredQuestionSetSubmitsCompletelyWithoutTruncation() throws Exception {run(100);}
    private void run(int count) throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        String version="demo-01-v"+count+"q";
        var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0");
        var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
        String parent=UUID.randomUUID().toString();
        try {
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            byte[] tone=java.nio.file.Files.readAllBytes(java.nio.file.Path.of(System.getenv("NORTHSTAR_TEST_AUDIO")));
            String toneHash=HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(tone));
            admin.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,?,?,?,?)",version+"-license","original","self-authored-test:quiz-scale","confirmed","{}");
            admin.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready,publication_state) VALUES (?,?,?,?,?,?,?,TRUE,'published')",version,"demo-01",900+count,version+"-license","0".repeat(64),"0".repeat(64),"{}");
            String pi=UUID.randomUUID().toString();
            admin.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",pi,"demo-01",pi);
            admin.update("INSERT INTO paragraph(id,version_id,lesson_id,identity_id,stable_key,sequence_no) VALUES (?,?,?,?,?,1)",version+"-p",version,"demo-01",pi,"scale-p");
            Map<String,String> answers=new LinkedHashMap<>();
            for(int i=1;i<=count;i++) {
                String exercise=version+"-quiz-"+i,sentence=version+"-s"+i,point=version+"-kp-"+i,asset=version+"-a"+i,identity=UUID.randomUUID().toString();
                java.nio.file.Path path=java.nio.file.Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"),"publication",version,i+".mp3");java.nio.file.Files.createDirectories(path.getParent());java.nio.file.Files.write(path,tone);
                admin.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,?,?,'audio/mpeg',?,2000,?,'ready')",asset,version,version+"-license","original_recording","publication/"+version+"/"+i+".mp3",tone.length,toneHash);
                admin.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,"demo-01",identity);
                admin.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,'scale-"+i+"',?,'Writer',?,'原创句','本地预置讲解','original',?,0,2000,?,?)",sentence,"demo-01",version,i,"第"+i+"句原文。",asset,version+"-p",identity);
                admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES (?,?,?,?, 'scale','scale','scale','scale')",point,"demo-01",version,sentence);
                admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES (?,?,?,?, 'quiz_choice','quiz_choice_v1')",exercise,"demo-01",version,sentence);
                String questionJson=mapper.writeValueAsString(Map.of("id",exercise,"prompt","第"+i+"题","options",List.of(Map.of("id",exercise+"-a","text","alpha"),Map.of("id",exercise+"-b","text","beta"),Map.of("id",exercise+"-c","text","gamma")),"answerKey",exercise+"-a"));
                admin.update("INSERT INTO quiz_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",exercise,version,sentence,point,questionJson);
                answers.put(exercise,exercise+"-a");
            }
            String setId=UUID.randomUUID().toString();
            admin.update("INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES (?,?,'practice','quiz_choice_v1','version_content')",setId,version);
            for(int i=1;i<=count;i++) {
                String exercise=version+"-quiz-"+i,sentence=version+"-s"+i,point=version+"-kp-"+i;
                String questionJson=mapper.writeValueAsString(mapper.readTree(admin.queryForObject("SELECT payload_json FROM quiz_question WHERE exercise_id=?",String.class,exercise)));
                admin.update("INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) VALUES (?,?,?,?,?,?,?,?)",setId,exercise,version,sentence,point,i,questionJson,QuizSets.itemHash(Map.of("exercise_id",exercise,"ordinal",i,"sentence_id",sentence,"knowledge_point_id",point,"question_text",questionJson)));
                String stored=admin.queryForObject("SELECT CAST(question_json AS CHAR CHARACTER SET utf8mb4) FROM exercise_set_item WHERE set_id=? AND exercise_id=?",String.class,setId,exercise);
                admin.update("UPDATE exercise_set_item SET item_hash=? WHERE set_id=? AND exercise_id=?",QuizSets.itemHash(Map.of("exercise_id",exercise,"ordinal",i,"sentence_id",sentence,"knowledge_point_id",point,"question_text",stored)),setId,exercise);
            }
            var items=admin.queryForList("SELECT i.*,CAST(i.question_json AS CHAR CHARACTER SET utf8mb4) AS question_text FROM exercise_set_item i WHERE set_id=? ORDER BY ordinal",setId);
            String setHash=QuizSets.setHash(version,null,items);
            admin.update("UPDATE exercise_set SET set_hash=?,frozen=TRUE WHERE id=?",setHash,setId);
            var quiz=json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null));
            assertEquals(count,quiz.path("totalCount").asInt());assertEquals(setHash,quiz.path("setHash").asText());
            assertThrows(org.springframework.dao.DataAccessException.class,()->admin.update("DELETE FROM exercise_set_item WHERE set_id=?",setId));
            long started=System.nanoTime();
            var body=new LinkedHashMap<String,Object>();body.put("protocolVersion","quiz-submit-v2");body.put("lessonId","demo-01");body.put("versionId",version);body.put("setId",setId);body.put("setHash",setHash);body.put("eventId",parent);body.put("clientOccurredAt",Instant.now().toString());body.put("answers",answers);
            String payload=mapper.writeValueAsString(body);
            var submitted=send(base+"/quiz/sets/"+setId+"/attempts","POST",payload);
            long elapsedMs=(System.nanoTime()-started)/1_000_000;
            assertEquals(200,submitted.statusCode(),submitted.body());
            assertEquals(count,json(submitted).path("correctCount").asInt());assertEquals(count,json(submitted).path("totalCount").asInt());
            assertEquals(count,admin.queryForObject("SELECT COUNT(*) FROM quiz_run_item WHERE run_id=(SELECT id FROM quiz_run WHERE event_id=?)",Integer.class,parent));
            assertEquals(count,admin.queryForObject("SELECT COUNT(*) FROM quiz_answer WHERE run_id=(SELECT id FROM quiz_run WHERE event_id=?)",Integer.class,parent));
            assertEquals(count,admin.queryForObject("SELECT total_count FROM quiz_run WHERE event_id=?",Integer.class,parent));
            assertEquals(count,admin.queryForObject("SELECT submitted_count FROM quiz_run WHERE event_id=?",Integer.class,parent));
            var history=json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null)).path("history");
            assertEquals(1,history.size());assertTrue(history.get(0).path("verified").asBoolean());assertEquals(count,history.get(0).path("answers").size());
            assertEquals(count,admin.queryForObject("SELECT COUNT(*) FROM learning_evidence v JOIN exercise_attempt a ON a.id=v.attempt_id WHERE a.version_id=?",Integer.class,version));
            System.out.println("QUIZ_SCALE count="+count+" elapsedMs="+elapsedMs+" requestBytes="+payload.getBytes(java.nio.charset.StandardCharsets.UTF_8).length+" responseBytes="+submitted.body().getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
        } finally {
            app.close();
            admin.update("DELETE i FROM quiz_run_item i JOIN quiz_run r ON r.id=i.run_id WHERE r.event_id=?",parent);
            var attempts=admin.queryForList("SELECT a.id,a.event_id FROM exercise_attempt a JOIN quiz_answer b ON b.attempt_id=a.id JOIN quiz_run r ON r.id=b.run_id WHERE r.event_id=?",parent);
            for(var a:attempts) {
                admin.update("DELETE FROM review_source WHERE attempt_id=?",a.get("id"));
                admin.update("DELETE FROM learning_evidence WHERE attempt_id=?",a.get("id"));
                admin.update("DELETE FROM quiz_answer WHERE attempt_id=?",a.get("id"));
                admin.update("DELETE FROM exercise_attempt WHERE id=?",a.get("id"));
                admin.update("DELETE FROM command_receipt WHERE event_id=?",a.get("event_id"));
            }
            admin.update("DELETE FROM quiz_run WHERE event_id=?",parent);admin.update("DELETE FROM command_receipt WHERE event_id=?",parent);
            admin.update("DELETE FROM quiz_progress WHERE version_id=?",version);
            admin.execute("DROP TRIGGER IF EXISTS quiz_item_no_delete");admin.execute("DROP TRIGGER IF EXISTS quiz_set_no_delete");
            admin.update("DELETE FROM exercise_set_item WHERE version_id=?",version);
            admin.update("DELETE FROM exercise_set WHERE version_id=?",version);
            admin.execute("CREATE TRIGGER quiz_set_no_delete BEFORE DELETE ON exercise_set FOR EACH ROW BEGIN IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz set is immutable'; END IF; END");
            admin.execute("CREATE TRIGGER quiz_item_no_delete BEFORE DELETE ON exercise_set_item FOR EACH ROW BEGIN IF (SELECT frozen FROM exercise_set WHERE id=OLD.set_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz items are immutable'; END IF; END");
            for(int i=1;i<=count;i++) {
                admin.update("DELETE FROM quiz_question WHERE exercise_id=?",version+"-quiz-"+i);
                admin.update("DELETE FROM exercise WHERE id=?",version+"-quiz-"+i);
                admin.update("DELETE FROM knowledge_point WHERE id=?",version+"-kp-"+i);
            }
            admin.update("DELETE FROM sentence WHERE lesson_version_id=?",version);
            admin.update("DELETE FROM sentence_identity WHERE lesson_id='demo-01' AND (id LIKE ? OR registry_key LIKE ?)",version+"%",version+"%");
            admin.update("DELETE FROM audio_asset WHERE lesson_version_id=?",version);
            admin.update("DELETE FROM paragraph WHERE id=?",version+"-p");
            admin.update("DELETE FROM paragraph_identity WHERE id=? OR registry_key=?",version+"-p",version+"-p");
            admin.update("DELETE FROM lesson_version WHERE id=?",version);
            admin.update("DELETE FROM content_license WHERE id=?",version+"-license");
        }
    }
    private JsonNode json(HttpResponse<String> r){return mapper.readTree(r.body());}
    private HttpResponse<String> send(String url,String method,String body)throws Exception{return client.send(HttpRequest.newBuilder(URI.create(url)).header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body)).build(),HttpResponse.BodyHandlers.ofString());}
}
