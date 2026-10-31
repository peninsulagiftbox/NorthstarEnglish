package local.northstar.exercise;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import local.northstar.NorthstarApplication;
import local.northstar.catalog.ContentSeeder;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class ReadingIntegrationTest {
    private final JsonMapper mapper=JsonMapper.builder().build();
    @Test void readingContextFavoritesEvidenceHistoryAndIdempotency() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            var jdbc=app.getBean(JdbcTemplate.class);
            var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
            var client=HttpClient.newHttpClient();
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            String question="demo-01-v2-reading-01",sentence="demo-01-v2-s06",word="demo-01-v2-kp-beside";
            var events=new ArrayList<String>();
            var favorite=jdbc.queryForList("SELECT * FROM vocabulary_favorite WHERE knowledge_point_id=?",word);
            var progress=jdbc.queryForList("SELECT * FROM reading_progress WHERE exercise_id=?",question);
            boolean hadReview=jdbc.queryForObject("SELECT COUNT(*) FROM review_item WHERE sentence_id=?",Integer.class,sentence)>0;
            int before=jdbc.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE exercise_id=?",Integer.class,question);
            try {
                var initial=mapper.readTree(send(client,base+"/reading?lessonId=demo-01&versionId=demo-01-v2","GET",null).body());
                assertEquals(6,initial.path("vocabulary").size());
                assertEquals("Where should Mia put the small plants?",initial.path("questions").get(0).path("prompt").asText());
                assertFalse(initial.path("questions").get(0).has("answerKey"));
                var fav=Map.of("lessonId","demo-01","versionId","demo-01-v2","favorite",true);
                assertEquals(200,send(client,base+"/knowledge/"+word+"/favorite","PUT",fav).statusCode());
                assertEquals(200,send(client,base+"/knowledge/"+word+"/favorite","PUT",fav).statusCode());
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM vocabulary_favorite WHERE knowledge_point_id=? AND favorite=TRUE",Integer.class,word));
                assertEquals(before,jdbc.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE exercise_id=?",Integer.class,question));
                assertEquals(422,send(client,base+"/knowledge/demo-01-v1-kp-beside/favorite","PUT",fav).statusCode());
                var body=new LinkedHashMap<String,Object>();
                body.put("eventId",UUID.randomUUID().toString()); events.add(body.get("eventId").toString());
                body.put("lessonId","wrong-course");body.put("versionId","demo-01-v2");body.put("optionId",question+"-b");body.put("clientOccurredAt","2026-10-23T04:00:00Z");
                String path=base+"/reading/"+question+"/attempts";
                assertEquals(422,send(client,path,"POST",body).statusCode());body.put("lessonId","demo-01");
                body.put("versionId","demo-01-v1");assertEquals(422,send(client,path,"POST",body).statusCode());body.put("versionId","demo-01-v2");
                body.put("optionId","demo-01-v1-reading-01-b");assertEquals(422,send(client,path,"POST",body).statusCode());body.put("optionId",question+"-b");
                String json=mapper.writeValueAsString(body);
                var a=client.sendAsync(request(path,"POST",json),HttpResponse.BodyHandlers.ofString());
                var b=client.sendAsync(request(path,"POST",json),HttpResponse.BodyHandlers.ofString());
                CompletableFuture.allOf(a,b).join();assertEquals(200,a.join().statusCode(),a.join().body());assertEquals(mapper.readTree(a.join().body()),mapper.readTree(b.join().body()));
                var result=mapper.readTree(a.join().body());assertFalse(result.path("result").path("correct").asBoolean());
                assertEquals(sentence,result.path("result").path("sentenceId").asText());assertEquals(word,result.path("result").path("knowledgePointId").asText());
                assertEquals("Next to the blue bench.",result.path("result").path("correctText").asText());
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM learning_evidence WHERE event_id=?",Integer.class,body.get("eventId")));
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM review_source WHERE attempt_id=? AND reason='reading_evidence_mismatch'",Integer.class,result.path("attemptId").asText()));
                body.put("optionId",question+"-a");assertEquals(409,send(client,path,"POST",body).statusCode());
                body.put("eventId",UUID.randomUUID().toString());events.add(body.get("eventId").toString());
                var good=send(client,path,"POST",body);assertEquals(200,good.statusCode(),good.body());assertTrue(mapper.readTree(good.body()).path("result").path("correct").asBoolean());
                assertEquals(before+2,jdbc.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE exercise_id=?",Integer.class,question));
                for(String action:List.of("skip","pause","start")) {
                    var event=new LinkedHashMap<String,Object>();event.put("eventId",UUID.randomUUID().toString());events.add(event.get("eventId").toString());
                    event.put("lessonId","demo-01");event.put("versionId","demo-01-v2");event.put("clientOccurredAt","2026-10-23T04:00:00Z");event.put("action",action);
                    assertEquals(200,send(client,base+"/reading/"+question+"/events","POST",event).statusCode());
                }
                var restored=mapper.readTree(send(client,base+"/reading?lessonId=demo-01&versionId=demo-01-v2","GET",null).body());
                assertEquals(before+2,restored.path("questions").get(0).path("history").size());
                assertEquals("in_progress",restored.path("questions").get(0).path("state").asText());
                assertTrue(restored.path("vocabulary").toString().contains("\"favorite\":true"));
                assertEquals(422,send(client,base+"/reading?lessonId=wrong-course&versionId=demo-01-v2","GET",null).statusCode());
                assertTrue(send(client,base+"/reviews/items","GET",null).body().contains("reading_evidence_mismatch"));
                String attempt=result.path("attemptId").asText();
                assertThrows(org.springframework.dao.DataAccessException.class,() -> jdbc.update("UPDATE reading_answer SET option_id=? WHERE attempt_id=?",question+"-a",attempt));
                assertEquals(0,app.getBean(Flyway.class).migrate().migrationsExecuted);
                app.getBean(ContentSeeder.class).seed();
            } finally {
                for(String event:events) {
                    admin.update("DELETE b FROM reading_answer b JOIN exercise_attempt a ON a.id=b.attempt_id WHERE a.event_id=?",event);
                    admin.update("DELETE s FROM review_source s JOIN exercise_attempt a ON a.id=s.attempt_id WHERE a.event_id=?",event);
                    admin.update("DELETE FROM learning_evidence WHERE event_id=?",event);
                    admin.update("DELETE FROM exercise_attempt WHERE event_id=?",event);
                    admin.update("DELETE FROM command_receipt WHERE event_id=?",event);
                }
                if(!hadReview) admin.update("DELETE FROM review_item WHERE sentence_id=?",sentence);
                admin.update("DELETE FROM reading_progress WHERE exercise_id=?",question);
                if(!progress.isEmpty()) admin.update("INSERT INTO reading_progress(exercise_id,current_state) VALUES (?,?)",question,progress.getFirst().get("current_state"));
                admin.update("DELETE FROM vocabulary_favorite WHERE knowledge_point_id=?",word);
                if(!favorite.isEmpty()) admin.update("INSERT INTO vocabulary_favorite(knowledge_point_id,favorite,updated_at) VALUES (?,?,?)",word,favorite.getFirst().get("favorite"),favorite.getFirst().get("updated_at"));
            }
        }
    }
    private HttpResponse<String> send(HttpClient client,String url,String method,Object body) throws Exception {return client.send(request(url,method,body==null?null:mapper.writeValueAsString(body)),HttpResponse.BodyHandlers.ofString());}
    private HttpRequest request(String url,String method,String json) {
        return HttpRequest.newBuilder(URI.create(url)).header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").method(method,json==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(json)).build();
    }
}
