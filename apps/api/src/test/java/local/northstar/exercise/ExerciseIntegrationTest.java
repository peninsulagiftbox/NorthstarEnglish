package local.northstar.exercise;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class ExerciseIntegrationTest {
    private final JsonMapper mapper=JsonMapper.builder().build();
    @Test void realMysqlTransactionsIdempotencyDraftsStagesAndSources() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            var jdbc=app.getBean(JdbcTemplate.class);var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            var client=HttpClient.newHttpClient();
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            String sentence="demo-01-v1-s06", attemptPath="/exercises/"+sentence+"-dictation/attempts";
            var events=new ArrayList<String>();
            var originalStage=jdbc.queryForList("SELECT * FROM study_stage WHERE sentence_id=?",sentence);
            var originalDraft=jdbc.queryForList("SELECT * FROM exercise_draft WHERE sentence_id=?",sentence);
            String asset=jdbc.queryForObject("SELECT audio_asset_id FROM sentence WHERE id=?",String.class,sentence);
            String originalStatus=jdbc.queryForObject("SELECT status FROM audio_asset WHERE id=?",String.class,asset);
            boolean originalReview=jdbc.queryForObject("SELECT COUNT(*) FROM review_item WHERE sentence_id=?",Integer.class,sentence)>0;
            try {
                var body=body(sentence);String event=UUID.randomUUID().toString();events.add(event);body.put("eventId",event);
                body.put("text","   ");assertEquals(422,send(client,base+attemptPath,"POST",body,null).statusCode());
                assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM command_receipt WHERE event_id=?",Integer.class,event));
                body.put("text","Please put them behind the blue bench.");body.put("audioPlayed",false);
                assertEquals(422,send(client,base+attemptPath,"POST",body,null).statusCode());body.put("audioPlayed",true);
                body.put("versionId","foreign-v1");assertEquals(422,send(client,base+attemptPath,"POST",body,null).statusCode());body.put("versionId","demo-01-v1");
                String json=mapper.writeValueAsString(body);
                var a=client.sendAsync(request(base+attemptPath,"POST",json,null),HttpResponse.BodyHandlers.ofString());
                var b=client.sendAsync(request(base+attemptPath,"POST",json,null),HttpResponse.BodyHandlers.ofString());
                CompletableFuture.allOf(a,b).join();assertEquals(200,a.join().statusCode(),a.join().body());assertEquals(mapper.readTree(a.join().body()),mapper.readTree(b.join().body()));
                var saved=mapper.readTree(a.join().body());assertEquals("practiced",saved.path("state").asText());
                assertEquals("beside",saved.path("result").path("edits").get(3).path("expected").asText());
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE event_id=?",Integer.class,event));
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM learning_evidence WHERE event_id=?",Integer.class,event));
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM review_source WHERE attempt_id=?",Integer.class,saved.path("attemptId").asText()));
                assertThrows(org.springframework.dao.DataAccessException.class,() -> jdbc.update("UPDATE exercise_attempt SET raw_text='changed' WHERE event_id=?",event));
                body.put("text","Different payload");assertEquals(409,send(client,base+attemptPath,"POST",body,null).statusCode());
                admin.update("UPDATE audio_asset SET status='missing' WHERE id=?",asset);
                assertEquals(200,client.send(request(base+attemptPath,"POST",json,null),HttpResponse.BodyHandlers.ofString()).statusCode());
                String missing=UUID.randomUUID().toString();events.add(missing);body.put("eventId",missing);
                assertEquals(503,send(client,base+attemptPath,"POST",body,null).statusCode());
                assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM command_receipt WHERE event_id=?",Integer.class,missing));
                admin.update("UPDATE audio_asset SET status=? WHERE id=?",originalStatus,asset);
                var good=body(sentence);String goodId=UUID.randomUUID().toString();events.add(goodId);good.put("eventId",goodId);good.put("text","please put them beside the blue bench!");
                assertTrue(mapper.readTree(send(client,base+attemptPath,"POST",good,null).body()).path("result").path("correct").asBoolean());
                int practiced=jdbc.queryForObject("SELECT practice_count FROM study_stage WHERE sentence_id=?",Integer.class,sentence);
                for(String action:List.of("skip","pause","start")) {
                    var command=new LinkedHashMap<String,Object>();String id=UUID.randomUUID().toString();events.add(id);
                    command.put("eventId",id);command.put("lessonId","demo-01");command.put("versionId","demo-01-v1");command.put("sentenceId",sentence);command.put("action",action);command.put("clientOccurredAt","2026-10-21T15:00:00Z");
                    var response=send(client,base+"/study/events","POST",command,null);assertEquals(200,response.statusCode(),response.body());
                    assertEquals(practiced,jdbc.queryForObject("SELECT practice_count FROM study_stage WHERE sentence_id=?",Integer.class,sentence));
                }
                long revision=originalDraft.isEmpty()?0:((Number)originalDraft.getFirst().get("row_version")).longValue();
                var draft=Map.of("lessonId","demo-01","versionId","demo-01-v1","text","Raw original draft.");
                assertEquals(428,send(client,base+"/drafts/"+sentence,"PUT",draft,null).statusCode());
                assertEquals(200,send(client,base+"/drafts/"+sentence,"PUT",draft,revision).statusCode());
                assertEquals(412,send(client,base+"/drafts/"+sentence,"PUT",draft,revision).statusCode());
                var read=client.send(HttpRequest.newBuilder(URI.create(base+"/drafts/"+sentence+"?lessonId=demo-01&versionId=demo-01-v1")).build(),HttpResponse.BodyHandlers.ofString());
                assertEquals("Raw original draft.",mapper.readTree(read.body()).path("text").asText());
                var reviews=client.send(HttpRequest.newBuilder(URI.create(base+"/reviews/items")).build(),HttpResponse.BodyHandlers.ofString());
                assertTrue(reviews.body().contains(saved.path("attemptId").asText()));
                assertEquals(0,app.getBean(Flyway.class).migrate().migrationsExecuted);
            } finally {
                admin.update("UPDATE audio_asset SET status=? WHERE id=?",originalStatus,asset);
                for(String id:events) {
                    admin.update("DELETE rs FROM review_source rs JOIN exercise_attempt a ON a.id=rs.attempt_id WHERE a.event_id=?",id);
                    admin.update("DELETE FROM learning_evidence WHERE event_id=?",id);
                    admin.update("DELETE FROM exercise_attempt WHERE event_id=?",id);
                    admin.update("DELETE FROM study_event WHERE event_id=?",id);
                    admin.update("DELETE FROM command_receipt WHERE event_id=?",id);
                }
                if(!originalReview) admin.update("DELETE FROM review_item WHERE sentence_id=?",sentence);
                admin.update("DELETE FROM study_stage WHERE sentence_id=?",sentence);
                if(!originalStage.isEmpty()) { var row=originalStage.getFirst();admin.update("INSERT INTO study_stage(sentence_id,version_id,current_state,practice_count) VALUES (?,?,?,?)",sentence,row.get("version_id"),row.get("current_state"),row.get("practice_count")); }
                admin.update("DELETE FROM exercise_draft WHERE sentence_id=?",sentence);
                if(!originalDraft.isEmpty()) { var row=originalDraft.getFirst();admin.update("INSERT INTO exercise_draft(sentence_id,lesson_id,version_id,raw_text,row_version,updated_at) VALUES (?,?,?,?,?,?)",sentence,row.get("lesson_id"),row.get("version_id"),row.get("raw_text"),row.get("row_version"),row.get("updated_at")); }
            }
        }
    }
    private Map<String,Object> body(String sentence) {
        var value=new LinkedHashMap<String,Object>();value.put("lessonId","demo-01");value.put("versionId","demo-01-v1");value.put("sentenceId",sentence);value.put("text","Please put them behind the blue bench.");value.put("audioPlayed",true);value.put("answerExposed",false);value.put("clientOccurredAt","2026-10-21T15:00:00Z");return value;
    }
    private HttpResponse<String> send(HttpClient client,String url,String method,Object body,Long revision) throws Exception {return client.send(request(url,method,mapper.writeValueAsString(body),revision),HttpResponse.BodyHandlers.ofString());}
    private HttpRequest request(String url,String method,String json,Long revision) {
        var builder=HttpRequest.newBuilder(URI.create(url)).header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json");
        if(revision!=null) builder.header("If-Match","\""+revision+"\"");
        return builder.method(method,HttpRequest.BodyPublishers.ofString(json)).build();
    }
}
