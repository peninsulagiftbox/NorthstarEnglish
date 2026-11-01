package local.northstar.exercise;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.time.Instant;
import java.util.*;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class QuizAtomicIntegrationTest {
    static class InjectedFault extends QuizFault {
        String mode="off";
        @Override public void afterItem(int ordinal,int total) {
            if(mode.equals("first")&&ordinal==1 || mode.equals("last")&&ordinal==total)throw new IllegalStateException("test rollback: "+mode);
        }
        @Override public void beforeReceipt() {
            if(mode.equals("receipt"))throw new IllegalStateException("test rollback: receipt");
            if(mode.equals("commit"))TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void beforeCommit(boolean readOnly){throw new IllegalStateException("test rollback: commit");}
            });
        }
    }
    @TestConfiguration(proxyBeanMethods=false) static class FaultConfig {
        @Bean @Primary InjectedFault injectedFault(){return new InjectedFault();}
    }
    final JsonMapper json=JsonMapper.builder().build();
    final HttpClient client=HttpClient.newHttpClient();
    @Test void fourFailurePointsRollbackAllObjectsAndOriginalEventRetriesOnce()throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class,FaultConfig.class).run("--server.port=0")) {
            var db=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            var quiz=json.readTree(client.send(HttpRequest.newBuilder(URI.create(base+"/quiz?lessonId=demo-01&versionId=demo-01-v2")).build(),HttpResponse.BodyHandlers.ofString()).body());
            var fault=app.getBean(InjectedFault.class);
            for(String mode:List.of("first","last","receipt","commit")) {
                String event=UUID.randomUUID().toString();var body=new LinkedHashMap<String,Object>();
                body.put("protocolVersion","quiz-submit-v2");body.put("eventId",event);body.put("lessonId","demo-01");body.put("versionId","demo-01-v2");body.put("setId",quiz.path("setId").asText());body.put("setHash",quiz.path("setHash").asText());body.put("clientOccurredAt",Instant.now().toString());
                var answers=new LinkedHashMap<String,String>();for(var q:quiz.path("questions"))answers.put(q.path("id").asText(),q.path("id").asText()+"-b");body.put("answers",answers);
                var before=snapshot(db);fault.mode=mode;
                String path=base+"/quiz/sets/"+quiz.path("setId").asText()+"/attempts";
                var failed=post(path,body);assertEquals(500,failed.statusCode(),failed.body());
                assertEquals(before,snapshot(db),"Independent connection snapshot after "+mode);
                fault.mode="off";var retry=post(path,body);assertEquals(200,retry.statusCode(),retry.body());
                assertEquals(json.readTree(retry.body()),json.readTree(post(path,body).body()));
                assertEquals(1,db.queryForObject("SELECT COUNT(*) FROM quiz_run WHERE event_id=?",Integer.class,event));
                String run=json.readTree(retry.body()).path("runId").asText();
                for(String table:List.of("quiz_answer","quiz_run_item"))assertEquals(3,db.queryForObject("SELECT COUNT(*) FROM "+table+" WHERE run_id=?",Integer.class,run));
                assertEquals(3,db.queryForObject("SELECT COUNT(*) FROM learning_evidence e JOIN quiz_answer a ON a.attempt_id=e.attempt_id WHERE a.run_id=?",Integer.class,run));
                System.out.println("QUIZ_ATOMIC "+mode+" rollback=exact retryRuns=1 items=3");
            }
        }
    }
    @Test void historyAndReportsAgreeForIncompleteHistoricalRun()throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            var db=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            var set=db.queryForMap("SELECT id,set_hash FROM exercise_set WHERE version_id='demo-01-v2'");String event=UUID.randomUUID().toString();
            db.update("INSERT INTO command_receipt(event_id,payload_hash) VALUES (?,SHA2(?,256))",event,event);
            db.update("INSERT INTO quiz_run(id,event_id,lesson_id,version_id,correct_count,total_count,submitted_count,set_id,set_hash,exposure_status,measurement_policy_version) VALUES (?,?,'demo-01','demo-01-v2',0,3,3,?,?,'unknown','quiz_choice_v1')",event,event,set.get("id"),set.get("set_hash"));
            try {
                String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
                var history=json.readTree(client.send(HttpRequest.newBuilder(URI.create(base+"/quiz/history?lessonId=demo-01&versionId=demo-01-v2")).build(),HttpResponse.BodyHandlers.ofString()).body());
                JsonNode found=null;for(var run:history)if(run.path("id").asText().equals(event))found=run;
                assertNotNull(found);assertFalse(found.path("verified").asBoolean(),"Incomplete history must never be presented as verified");
                var report=json.readTree(client.send(HttpRequest.newBuilder(URI.create(base+"/reports?setId="+set.get("id"))).build(),HttpResponse.BodyHandlers.ofString()).body());
                assertEquals(set.get("id"),report.path("quizScope").path("setId").asText());
            } finally {db.update("DELETE FROM quiz_run WHERE id=?",event);db.update("DELETE FROM command_receipt WHERE event_id=?",event);}
        }
    }
    Map<String,Object> snapshot(JdbcTemplate db) {
        var all=new LinkedHashMap<String,Object>();
        for(String table:List.of("quiz_run","quiz_answer","quiz_run_item","exercise_attempt","learning_evidence","command_receipt","review_item","review_source","quiz_progress")) {
            var pk=db.queryForList("SELECT column_name FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name=? AND index_name='PRIMARY' ORDER BY seq_in_index",String.class,table);
            all.put(table,db.queryForList("SELECT * FROM "+table+" ORDER BY "+String.join(",",pk)));
        }
        return all;
    }
    HttpResponse<String> post(String path,Object body)throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(path)).header("Origin","http://127.0.0.1:"+System.getenv("WEB_PORT")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body))).build(),HttpResponse.BodyHandlers.ofString());
    }
}
