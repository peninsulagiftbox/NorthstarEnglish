package local.northstar.report;

import static org.junit.jupiter.api.Assertions.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.Instant;
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

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class QuizReportR1IntegrationTest {
    final JsonMapper json=JsonMapper.builder().build();
    final HttpClient http=HttpClient.newHttpClient();
    String base;
    JdbcTemplate db;
    record Submitted(String event,String run,String set,String hash,int correct,int total) {}

    @Test void boundFiltersHandleQuotedIdentifiersUnicodeAndCombinedUtcBoundaries()throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            db=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            String tag=UUID.randomUUID().toString().substring(0,8),lesson="r1'\\lesson-"+tag,version="r1'\\version-"+tag;
            specialFixture(lesson,version,tag);
            var submitted=submit(lesson,version);
            Instant at=db.queryForObject("SELECT submitted_at FROM quiz_run WHERE id=?",Timestamp.class,submitted.run).toInstant();
            for(var filter:List.of(Map.of("lessonId",lesson),Map.of("versionId",version),Map.of("setId",submitted.set),
                Map.of("lessonId",lesson,"versionId",version,"setId",submitted.set,"from",at.toString(),"to",at.plusMillis(1).toString()))) {
                var report=getReport(filter);assertEquals(1,report.path("quizRuns").size());assertEquals(submitted.run,report.path("quizRuns").get(0).path("id").asText());
                assertMetrics(report,1,0,1,1);assertTrue(report.path("quizRuns").get(0).path("verified").asBoolean());
            }
            for(String field:List.of("lessonId","versionId","setId"))for(String value:List.of("'","\\","\\' OR 1=1 -- ","' OR '1'='1","课程\\'測驗","not/a/valid-id","",submitted.set+"\\")) {
                var report=getReport(Map.of(field,value));assertEquals(0,report.path("quizRuns").size(),field+" must remain a literal");assertMetrics(report,0,0,0,0);
            }
            assertMetrics(getReport(Map.of("lessonId",lesson,"versionId","demo-01-v2")),0,0,0,0);
            assertMetrics(getReport(Map.of("setId",submitted.set,"to",at.toString())),0,0,0,0);
            assertMetrics(getReport(Map.of("setId",submitted.set,"from",at.plusMillis(1).toString())),0,0,0,0);
            assertMetrics(getReport(Map.of("setId",submitted.set,"to",at.plusMillis(1).toString())),1,0,1,1);
            for(String field:List.of("from","to"))for(String value:List.of("'","\\","2026-01-01T00:00:00Z' OR 1=1 --","时间","not-a-time")) {
                var response=get("/reports"+query(Map.of(field,value)));assertEquals(422,response.statusCode(),response.body());
            }
            System.out.println("R1_FILTER PASS quoted/backslash positive identifiers; 24 literal negative identifiers; UTC combination and invalid-time checks");
        }
    }

    @Test void inconsistentRunsAreExcludedByHistoryDetailsAndBothReportAggregates()throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            db=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            var target=submit("demo-01","demo-01-v2");var good=getReport(Map.of("setId",target.set));
            var receipt=db.queryForMap("SELECT payload_hash,response_json FROM command_receipt WHERE event_id=?",target.event);
            assertTrue(target.correct>0);assertGood(target);
            try {
                db.update("UPDATE quiz_run SET correct_count=0 WHERE id=?",target.run);
                assertBad(target,good,"wrong-correct-count");
            } finally {db.update("UPDATE quiz_run SET correct_count=? WHERE id=?",target.correct,target.run);}
            try {
                db.update("UPDATE quiz_run SET set_hash=? WHERE id=?","0".repeat(64),target.run);
                assertBad(target,good,"wrong-run-set-hash");
            } finally {db.update("UPDATE quiz_run SET set_hash=? WHERE id=?",target.hash,target.run);}
            try {
                db.update("UPDATE quiz_run_item SET set_hash=? WHERE run_id=?","0".repeat(64),target.run);
                assertBad(target,good,"wrong-item-set-hash");
            } finally {db.update("UPDATE quiz_run_item SET set_hash=? WHERE run_id=?",target.hash,target.run);}
            var item=db.queryForList("SELECT * FROM quiz_run_item WHERE run_id=? ORDER BY ordinal",target.run).getFirst();
            try {
                db.update("UPDATE quiz_run_item SET question_json=JSON_SET(question_json,'$.prompt','synthetic altered snapshot') WHERE run_id=? AND exercise_id=?",target.run,item.get("exercise_id"));
                assertBad(target,good,"snapshot-identity-mismatch");
            } finally {db.update("UPDATE quiz_run_item SET question_json=? WHERE run_id=? AND exercise_id=?",item.get("question_json"),target.run,item.get("exercise_id"));}
            try {
                db.update("UPDATE exercise_attempt SET correct=FALSE WHERE id=?",item.get("attempt_id"));
                assertBad(target,good,"attempt-correctness-mismatch");
            } finally {db.update("UPDATE exercise_attempt SET correct=TRUE WHERE id=?",item.get("attempt_id"));}
            try {
                db.update("DELETE FROM quiz_run_item WHERE run_id=? AND exercise_id=?",target.run,item.get("exercise_id"));
                assertBad(target,good,"missing-run-item");
            } finally {
                db.update("INSERT INTO quiz_run_item(run_id,exercise_id,version_id,sentence_id,set_id,set_hash,ordinal,question_json,attempt_id,option_id) VALUES (?,?,?,?,?,?,?,?,?,?)",item.get("run_id"),item.get("exercise_id"),item.get("version_id"),item.get("sentence_id"),item.get("set_id"),item.get("set_hash"),item.get("ordinal"),item.get("question_json"),item.get("attempt_id"),item.get("option_id"));
            }
            String extraExercise="r1-extra-"+UUID.randomUUID().toString().substring(0,8),extraAttempt=UUID.randomUUID().toString(),extraEvent=UUID.randomUUID().toString();
            try {
                db.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) SELECT ?,lesson_id,version_id,sentence_id,kind,algorithm_version FROM exercise WHERE id=?",extraExercise,item.get("exercise_id"));
                db.update("INSERT INTO command_receipt(event_id,payload_hash) VALUES (?,SHA2(?,256))",extraEvent,extraEvent);
                db.update("INSERT INTO exercise_attempt(id,event_id,lesson_id,version_id,sentence_id,exercise_id,raw_text,correct,answer_exposed,algorithm_version,result_json,client_occurred_at) SELECT ?,?,lesson_id,version_id,sentence_id,?,raw_text,correct,answer_exposed,algorithm_version,result_json,client_occurred_at FROM exercise_attempt WHERE id=?",extraAttempt,extraEvent,extraExercise,item.get("attempt_id"));
                db.update("INSERT INTO quiz_answer(run_id,exercise_id,attempt_id,version_id,sentence_id,option_id) VALUES (?,?,?,?,?,?)",target.run,extraExercise,extraAttempt,item.get("version_id"),item.get("sentence_id"),item.get("option_id"));
                assertBad(target,good,"extra-answer-without-run-item");
            } finally {
                db.update("DELETE FROM quiz_answer WHERE attempt_id=?",extraAttempt);db.update("DELETE FROM exercise_attempt WHERE id=?",extraAttempt);db.update("DELETE FROM command_receipt WHERE event_id=?",extraEvent);db.update("DELETE FROM exercise WHERE id=?",extraExercise);
            }
            assertGood(target);assertEquals(good.path("metrics").path("quiz"),getReport(Map.of("setId",target.set)).path("metrics").path("quiz"));
            assertEquals(receipt,db.queryForMap("SELECT payload_hash,response_json FROM command_receipt WHERE event_id=?",target.event),"Never rewrite existing receipts to pass verification");
        }
    }

    void assertBad(Submitted target,JsonNode before,String label)throws Exception {
        var history=body(get("/quiz/history?lessonId=demo-01&versionId=demo-01-v2"));
        assertFalse(find(history,target.run).path("verified").asBoolean(),label+" history");
        assertFalse(find(body(get("/quiz?lessonId=demo-01&versionId=demo-01-v2")).path("history"),target.run).path("verified").asBoolean(),label+" quiz");
        var report=getReport(Map.of("setId",target.set));var detail=find(report.path("quizRuns"),target.run);
        assertFalse(detail.path("verified").asBoolean(),label+" report detail");assertFalse(detail.has("accuracy"));
        var metrics=before.path("metrics").path("quiz");
        assertMetrics(report,metrics.path("verifiedRuns").asInt()-1,metrics.path("unverifiedRuns").asInt()+1,metrics.path("correct").asInt()-target.correct,metrics.path("total").asInt()-target.total);
        System.out.println("R1_VERIFY "+label+" PASS history/detail/aggregate agree");
    }
    void assertGood(Submitted target)throws Exception {assertTrue(find(body(get("/quiz/history?lessonId=demo-01&versionId=demo-01-v2")),target.run).path("verified").asBoolean());}
    void assertMetrics(JsonNode report,int verified,int unverified,int correct,int total) {
        var m=report.path("metrics").path("quiz");assertEquals(verified,m.path("verifiedRuns").asInt());assertEquals(verified,m.path("runs").asInt());assertEquals(unverified,m.path("unverifiedRuns").asInt());assertEquals(correct,m.path("correct").asInt());assertEquals(total,m.path("total").asInt());
        if(total==0)assertTrue(m.path("accuracy").isNull());else assertEquals((double)correct/total,m.path("accuracy").asDouble(),1e-12);
    }
    Submitted submit(String lesson,String version)throws Exception {
        var quiz=body(get("/quiz"+query(Map.of("lessonId",lesson,"versionId",version))));
        String event=UUID.randomUUID().toString();var answers=new LinkedHashMap<String,String>();for(var question:quiz.path("questions"))answers.put(question.path("id").asText(),question.path("id").asText()+"-a");
        var payload=Map.of("protocolVersion","quiz-submit-v2","eventId",event,"lessonId",lesson,"versionId",version,"setId",quiz.path("setId").asText(),"setHash",quiz.path("setHash").asText(),"answers",answers,"clientOccurredAt",Instant.now().toString());
        var response=http.send(HttpRequest.newBuilder(URI.create(base+"/quiz/sets/"+quiz.path("setId").asText()+"/attempts")).header("Origin","http://127.0.0.1:"+System.getenv("WEB_PORT")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(payload))).build(),HttpResponse.BodyHandlers.ofString());
        assertEquals(200,response.statusCode(),response.body());var result=json.readTree(response.body());return new Submitted(event,result.path("runId").asText(),quiz.path("setId").asText(),quiz.path("setHash").asText(),result.path("correctCount").asInt(),result.path("totalCount").asInt());
    }
    void specialFixture(String lesson,String version,String tag)throws Exception {
        String prefix="r1-"+tag,pi=UUID.randomUUID().toString(),si=UUID.randomUUID().toString();
        db.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,'original',?,'confirmed','{}')",prefix+"-license","self-authored:r1:"+tag);
        db.update("INSERT INTO lesson(id,slug,kind,availability) VALUES (?,?,'original','available')",lesson,lesson);
        db.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready,publication_state) VALUES (?,?,1,?,REPEAT('0',64),REPEAT('0',64),?,TRUE,'published')",version,lesson,prefix+"-license",json.writeValueAsString(Map.of("id",lesson,"versionId",version,"title","Original R1 parameter fixture","exercises",List.of())));
        db.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",pi,lesson,pi);db.update("INSERT INTO paragraph(id,version_id,lesson_id,identity_id,stable_key,sequence_no) VALUES (?,?,?,?,'p',1)",prefix+"-p",version,lesson,pi);
        db.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",si,lesson,si);
        String audioKey="r1-fixtures/"+prefix+".mp3",originalKey=db.queryForObject("SELECT storage_key FROM audio_asset WHERE id='demo-01-v2-a01'",String.class);
        var root=java.nio.file.Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"));java.nio.file.Files.createDirectories(root.resolve("r1-fixtures"));java.nio.file.Files.copy(root.resolve(originalKey),root.resolve(audioKey));
        db.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) SELECT ?,?,?,'original_recording',?,mime_type,byte_size,duration_ms,sha256,status FROM audio_asset WHERE id='demo-01-v2-a01'",prefix+"-a",version,prefix+"-license",audioKey);
        db.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) SELECT ?,?,?,'s',1,speaker,text,translation,explanation,focus,?,start_ms,end_ms,?,? FROM sentence WHERE id='demo-01-v2-s01'",prefix+"-s",lesson,version,prefix+"-a",prefix+"-p",si);
        db.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES (?,?,?,?,'r1','原创','本地预置讲解','Original fixture')",prefix+"-kp",lesson,version,prefix+"-s");
        db.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES (?,?,?,?,'quiz_choice','quiz_choice_v1')",prefix+"-q",lesson,version,prefix+"-s");
        String question=json.writeValueAsString(Map.of("id",prefix+"-q","prompt","Original parameter binding check","options",List.of(Map.of("id",prefix+"-q-a","text","A"),Map.of("id",prefix+"-q-b","text","B")),"answerKey",prefix+"-q-a"));
        db.update("INSERT INTO quiz_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",prefix+"-q",version,prefix+"-s",prefix+"-kp",question);
        QuizSets.freezeDefault(db,version);db.update("UPDATE lesson SET current_version_id=? WHERE id=?",version,lesson);
    }
    JsonNode getReport(Map<String,String> filter)throws Exception {return body(get("/reports"+query(filter)));}
    JsonNode find(JsonNode rows,String id) {for(var row:rows)if(row.path("id").asText().equals(id))return row;throw new AssertionError("Missing expected run");}
    JsonNode body(HttpResponse<String> response){assertEquals(200,response.statusCode(),response.body());return json.readTree(response.body());}
    HttpResponse<String> get(String path)throws Exception {return http.send(HttpRequest.newBuilder(URI.create(base+path)).build(),HttpResponse.BodyHandlers.ofString());}
    String query(Map<String,String> values) {return values.entrySet().stream().map(e->URLEncoder.encode(e.getKey(),StandardCharsets.UTF_8)+"="+URLEncoder.encode(e.getValue(),StandardCharsets.UTF_8)).collect(java.util.stream.Collectors.joining("&","?",""));}
}
