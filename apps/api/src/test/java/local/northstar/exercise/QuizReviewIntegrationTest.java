package local.northstar.exercise;
import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.sql.Timestamp;
import java.time.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import local.northstar.NorthstarApplication;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class QuizReviewIntegrationTest {
    private final JsonMapper mapper=JsonMapper.builder().build();
    private final HttpClient client=HttpClient.newHttpClient();
    @Test void completeRunsEvidenceKnowledgeCardsCasIdempotencyAndRestart() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        String version="demo-01-v2",point=version+"-kp-beside",item=point+"-quiz";
        var parents=new ArrayList<String>();var events=new ArrayList<String>();var children=new ArrayList<String>();
        var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0");
        var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
        var original=admin.queryForList("SELECT * FROM review_item WHERE version_id=? AND card_kind='quiz_choice'",version);
        var progress=admin.queryForList("SELECT * FROM quiz_progress WHERE version_id=?",version);
        try {
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            JsonNode initial=json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null));
            int before=initial.path("history").size();assertEquals(3,initial.path("questions").size());assertFalse(initial.path("questions").get(0).has("answerKey"));
            Map<String,String> answers=new LinkedHashMap<>();for(int i=1;i<=3;i++)answers.put(version+"-quiz-0"+i,version+"-quiz-0"+i+"-b");
            var body=new LinkedHashMap<String,Object>();String parent=UUID.randomUUID().toString();parents.add(parent);
            body.put("eventId",parent);body.put("lessonId","demo-01");body.put("versionId",version);body.put("answers",answers);body.put("clientOccurredAt","2026-10-23T23:59:30Z");
            body.put("versionId","demo-01-v1");assertEquals(422,send(base+"/quiz/attempts","POST",body).statusCode());body.put("versionId",version);
            answers.put(version+"-quiz-02","foreign-option");assertEquals(422,send(base+"/quiz/attempts","POST",body).statusCode());answers.put(version+"-quiz-02",version+"-quiz-02-b");
            assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM command_receipt WHERE event_id=?",Integer.class,parent));
            String payload=mapper.writeValueAsString(body);
            var a=client.sendAsync(request(base+"/quiz/attempts","POST",payload),HttpResponse.BodyHandlers.ofString());
            var b=client.sendAsync(request(base+"/quiz/attempts","POST",payload),HttpResponse.BodyHandlers.ofString());
            CompletableFuture.allOf(a,b).join();assertEquals(200,a.join().statusCode(),a.join().body());assertEquals(json(a.join()),json(b.join()));
            for(String id:answers.keySet())children.add(UUID.nameUUIDFromBytes((parent+":"+id).getBytes(java.nio.charset.StandardCharsets.UTF_8)).toString());
            assertEquals(0,json(a.join()).path("correctCount").asInt());
            assertEquals(3,admin.queryForObject("SELECT COUNT(*) FROM quiz_answer WHERE run_id=?",Integer.class,json(a.join()).path("runId").asText()));
            assertEquals(2,admin.queryForObject("SELECT COUNT(*) FROM review_item WHERE version_id=? AND sentence_id=? AND card_kind='quiz_choice'",Integer.class,version,version+"-s06"));
            assertEquals(1,admin.queryForObject("SELECT COUNT(*) FROM review_item WHERE id=?",Integer.class,item));
            assertTrue(admin.queryForObject("SELECT COUNT(*) FROM review_source WHERE item_id=?",Integer.class,item)>=1);
            answers.replaceAll((k,v)->k+"-a");assertEquals(409,send(base+"/quiz/attempts","POST",body).statusCode());
            String second=UUID.randomUUID().toString();parents.add(second);body.put("eventId",second);
            var good=send(base+"/quiz/attempts","POST",body);assertEquals(200,good.statusCode(),good.body());assertEquals(3,json(good).path("correctCount").asInt());
            for(String id:answers.keySet())children.add(UUID.nameUUIDFromBytes((second+":"+id).getBytes(java.nio.charset.StandardCharsets.UTF_8)).toString());
            assertEquals(before+2,json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null)).path("history").size());
            for(String action:List.of("skip","pause","start")) {
                String event=UUID.randomUUID().toString();events.add(event);
                assertEquals(200,send(base+"/quiz/events","POST",Map.of("eventId",event,"lessonId","demo-01","versionId",version,"action",action,"clientOccurredAt",Instant.now().toString())).statusCode());
            }
            assertEquals(before+2,json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null)).path("history").size());
            var due=json(send(base+"/reviews/due","GET",null));JsonNode card=null;for(var c:due)if(c.path("id").asText().equals(item))card=c;
            assertNotNull(card);assertFalse(card.has("text"));assertFalse(card.has("standardText"));
            long row=card.path("rowVersion").asLong();String ratingEvent=UUID.randomUUID().toString();events.add(ratingEvent);
            var rating=new LinkedHashMap<String,Object>();rating.put("eventId",ratingEvent);rating.put("lessonId","demo-01");rating.put("versionId",version);rating.put("sentenceId",version+"-s06");rating.put("rowVersion",row);rating.put("rating","again");rating.put("answerRevealed",false);rating.put("clientOccurredAt",Instant.now().toString());
            String ratePath=base+"/reviews/"+item+"/results";
            assertEquals(422,send(ratePath,"POST",rating).statusCode());rating.put("answerRevealed",true);
            assertTrue(send(base+"/reviews/"+item+"/answer","GET",null).body().contains("Please put them"));
            Instant start=Instant.now();var rated=send(ratePath,"POST",rating);assertEquals(200,rated.statusCode(),rated.body());
            var ratedJson=json(rated);Instant next=Instant.parse(ratedJson.path("nextDueAt").asText());assertTrue(next.isAfter(start.plusSeconds(59)) && next.isBefore(Instant.now().plusSeconds(61)));
            assertEquals(ratedJson,json(send(ratePath,"POST",rating)));assertEquals("self_rating",ratedJson.path("origin").asText());
            rating.put("eventId",UUID.randomUUID().toString());events.add(rating.get("eventId").toString());assertEquals(409,send(ratePath,"POST",rating).statusCode());
            assertEquals(1,admin.queryForObject("SELECT COUNT(*) FROM review_result WHERE event_id=?",Integer.class,ratingEvent));
            // Force only this isolated test card due; verify good starts at one day and updates success streak.
            admin.update("UPDATE review_item SET due_at=UTC_TIMESTAMP(3) WHERE id=?",item);rating.put("rowVersion",row+1);rating.put("rating","good");
            var remembered=send(ratePath,"POST",rating);assertEquals(200,remembered.statusCode(),remembered.body());
            assertTrue(Instant.parse(json(remembered).path("nextDueAt").asText()).isAfter(Instant.now().plusSeconds(86398)));
            var snapshot=admin.queryForMap("SELECT due_at,reps,row_version FROM review_item WHERE id=?",item);
            assertThrows(org.springframework.dao.DataAccessException.class,()->app.getBean(JdbcTemplate.class).update("UPDATE review_result SET rating='again' WHERE event_id=?",ratingEvent));
            app.close();
            try(var restarted=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
                var db=restarted.getBean(JdbcTemplate.class);assertEquals(snapshot,db.queryForMap("SELECT due_at,reps,row_version FROM review_item WHERE id=?",item));
                assertEquals(before+2,db.queryForObject("SELECT COUNT(*) FROM quiz_run WHERE version_id=?",Integer.class,version));
                assertEquals(0,restarted.getBean(Flyway.class).migrate().migrationsExecuted);
            }
        } finally {
            app.close();
            for(String e:events){admin.update("DELETE FROM review_result WHERE event_id=?",e);admin.update("DELETE FROM command_receipt WHERE event_id=?",e);}
            for(String parent:parents)admin.update("DELETE b FROM quiz_answer b JOIN quiz_run r ON r.id=b.run_id WHERE r.event_id=?",parent);
            for(String child:children){admin.update("DELETE s FROM review_source s JOIN exercise_attempt a ON a.id=s.attempt_id WHERE a.event_id=?",child);admin.update("DELETE FROM learning_evidence WHERE event_id=?",child);admin.update("DELETE FROM exercise_attempt WHERE event_id=?",child);admin.update("DELETE FROM command_receipt WHERE event_id=?",child);}
            for(String parent:parents){admin.update("DELETE FROM quiz_run WHERE event_id=?",parent);admin.update("DELETE FROM command_receipt WHERE event_id=?",parent);}
            for(var r:admin.queryForList("SELECT id FROM review_item WHERE version_id=? AND card_kind='quiz_choice'",version))if(original.stream().noneMatch(o->o.get("id").equals(r.get("id"))))admin.update("DELETE FROM review_item WHERE id=?",r.get("id"));
            for(var r:original)admin.update("UPDATE review_item SET due_at=?,reps=?,row_version=? WHERE id=?",r.get("due_at"),r.get("reps"),r.get("row_version"),r.get("id"));
            admin.update("DELETE FROM quiz_progress WHERE version_id=?",version);if(!progress.isEmpty())admin.update("INSERT INTO quiz_progress(version_id,current_state) VALUES (?,?)",version,progress.getFirst().get("current_state"));
        }
    }
    private JsonNode json(HttpResponse<String> r){return mapper.readTree(r.body());}
    private HttpResponse<String> send(String url,String method,Object body)throws Exception{return client.send(request(url,method,body==null?null:mapper.writeValueAsString(body)),HttpResponse.BodyHandlers.ofString());}
    private HttpRequest request(String url,String method,String json){return HttpRequest.newBuilder(URI.create(url)).header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").method(method,json==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(json)).build();}
}
