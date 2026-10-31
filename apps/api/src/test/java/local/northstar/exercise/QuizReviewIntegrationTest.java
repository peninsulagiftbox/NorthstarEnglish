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
            assertEquals(3,admin.queryForObject("SELECT COUNT(*) FROM quiz_run_item WHERE run_id=?",Integer.class,json(a.join()).path("runId").asText()));
            assertEquals(3,admin.queryForObject("SELECT total_count FROM quiz_run WHERE id=?",Integer.class,json(a.join()).path("runId").asText()));
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
            for(String parent:parents)admin.update("DELETE i FROM quiz_run_item i JOIN quiz_run r ON r.id=i.run_id WHERE r.event_id=?",parent);
            for(String parent:parents)admin.update("DELETE b FROM quiz_answer b JOIN quiz_run r ON r.id=b.run_id WHERE r.event_id=?",parent);
            for(String child:children){admin.update("DELETE s FROM review_source s JOIN exercise_attempt a ON a.id=s.attempt_id WHERE a.event_id=?",child);admin.update("DELETE FROM learning_evidence WHERE event_id=?",child);admin.update("DELETE FROM exercise_attempt WHERE event_id=?",child);admin.update("DELETE FROM command_receipt WHERE event_id=?",child);}
            for(String parent:parents){admin.update("DELETE FROM quiz_run WHERE event_id=?",parent);admin.update("DELETE FROM command_receipt WHERE event_id=?",parent);}
            for(var r:admin.queryForList("SELECT id FROM review_item WHERE version_id=? AND card_kind='quiz_choice'",version))if(original.stream().noneMatch(o->o.get("id").equals(r.get("id"))))admin.update("DELETE FROM review_item WHERE id=?",r.get("id"));
            for(var r:original)admin.update("UPDATE review_item SET due_at=?,reps=?,row_version=? WHERE id=?",r.get("due_at"),r.get("reps"),r.get("row_version"),r.get("id"));
            admin.update("DELETE FROM quiz_progress WHERE version_id=?",version);if(!progress.isEmpty())admin.update("INSERT INTO quiz_progress(version_id,current_state) VALUES (?,?)",version,progress.getFirst().get("current_state"));
        }
    }
    @Test void dynamicSetsRealDenominatorsRejectionsIdempotencyAndSnapshots() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        String version="demo-01-v2";
        var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0");
        var admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
        var originalItems=admin.queryForList("SELECT id FROM review_item WHERE version_id=? AND card_kind='quiz_choice'",version);
        var parents=new ArrayList<String>();var children=new ArrayList<String>();String extraSet=null;
        try {
            String base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            var quiz=json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null));
            String setId=quiz.path("setId").asText(),setHash=quiz.path("setHash").asText();
            assertEquals("quiz-submit-v2",quiz.path("protocolVersion").asText());assertEquals(3,quiz.path("totalCount").asInt());
            for(var question:quiz.path("questions")){assertFalse(question.has("answerKey"));assertFalse(question.has("explanation"));assertTrue(question.has("ordinal"));assertTrue(question.has("sequence"));}
            Map<String,String> partial=new LinkedHashMap<>();for(int i=1;i<=3;i++)partial.put(version+"-quiz-0"+i,i==1?version+"-quiz-01-a":version+"-quiz-0"+i+"-b");
            var body=new LinkedHashMap<String,Object>();body.put("protocolVersion","quiz-submit-v2");body.put("lessonId","demo-01");body.put("versionId",version);body.put("setId",setId);body.put("setHash",setHash);body.put("clientOccurredAt",Instant.now().toString());
            String missing=UUID.randomUUID().toString();body.put("eventId",missing);body.put("answers",Map.of(version+"-quiz-01",version+"-quiz-01-a"));
            assertEquals(422,send(base+"/quiz/sets/"+setId+"/attempts","POST",body).statusCode());
            assertEquals(0,admin.queryForObject("SELECT COUNT(*) FROM command_receipt WHERE event_id=?",Integer.class,missing));
            body.put("eventId",UUID.randomUUID().toString());body.put("answers",Map.of(version+"-quiz-01",version+"-quiz-01-a",version+"-quiz-02",version+"-quiz-02-a",version+"-quiz-03",version+"-quiz-03-a",version+"-quiz-09",version+"-quiz-09-a"));
            assertEquals(422,send(base+"/quiz/sets/"+setId+"/attempts","POST",body).statusCode());
            body.put("eventId",UUID.randomUUID().toString());body.put("answers",Map.of(version+"-quiz-01",version+"-quiz-01-z",version+"-quiz-02",version+"-quiz-02-a",version+"-quiz-03",version+"-quiz-03-a"));
            assertEquals(422,send(base+"/quiz/sets/"+setId+"/attempts","POST",body).statusCode());
            body.put("eventId",UUID.randomUUID().toString());body.put("setHash","deadbeef");body.put("answers",Map.of(version+"-quiz-01",version+"-quiz-01-a",version+"-quiz-02",version+"-quiz-02-a",version+"-quiz-03",version+"-quiz-03-a"));
            assertEquals(409,send(base+"/quiz/sets/"+setId+"/attempts","POST",body).statusCode());
            body.put("protocolVersion","quiz-submit-v1");body.put("setHash",setHash);
            assertEquals(422,send(base+"/quiz/sets/"+setId+"/attempts","POST",body).statusCode());
            body.put("protocolVersion","quiz-submit-v2");
            var before=json(send(base+"/reports","GET",null));
            String parent=UUID.randomUUID().toString();parents.add(parent);body.put("eventId",parent);body.put("answers",partial);
            var first=send(base+"/quiz/sets/"+setId+"/attempts","POST",body);assertEquals(200,first.statusCode(),first.body());
            String run=json(first).path("runId").asText();
            assertEquals(1,json(first).path("correctCount").asInt());assertEquals(3,json(first).path("totalCount").asInt());assertEquals(setId,json(first).path("setId").asText());assertEquals(setHash,json(first).path("setHash").asText());
            assertEquals(3,admin.queryForObject("SELECT COUNT(*) FROM quiz_run_item WHERE run_id=?",Integer.class,run));
            assertEquals(3,admin.queryForObject("SELECT total_count FROM quiz_run WHERE id=?",Integer.class,run));
            assertEquals(3,admin.queryForObject("SELECT submitted_count FROM quiz_run WHERE id=?",Integer.class,run));
            String payload=mapper.writeValueAsString(body);
            assertEquals(json(first),json(client.send(request(base+"/quiz/sets/"+setId+"/attempts","POST",payload),HttpResponse.BodyHandlers.ofString())));
            assertEquals(1,admin.queryForObject("SELECT COUNT(*) FROM quiz_run WHERE event_id=?",Integer.class,parent));
            body.put("answers",Map.of(version+"-quiz-01",version+"-quiz-01-a",version+"-quiz-02",version+"-quiz-02-a",version+"-quiz-03",version+"-quiz-03-a"));assertEquals(409,send(base+"/quiz/sets/"+setId+"/attempts","POST",body).statusCode());body.put("answers",partial);
            var refreshed=json(send(base+"/quiz?lessonId=demo-01&versionId="+version,"GET",null));
            var last=refreshed.path("history").get(0);assertEquals(3,last.path("totalCount").asInt());assertTrue(last.path("verified").asBoolean());
            assertTrue(last.path("answers").get(0).has("questionJson"));assertTrue(last.path("answers").get(0).path("sequence").asInt()>0);
            // Published five-question version: 1/3 (demo set) + 4/5 (this version) must aggregate to 5/8, never an average.
            String fiveVersion="demo-01-v5q";extraSet=null;
            byte[] tone=java.nio.file.Files.readAllBytes(java.nio.file.Path.of(System.getenv("NORTHSTAR_TEST_AUDIO")));
            String toneHash=HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(tone));
            admin.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,?,?,?,?)",fiveVersion+"-license","original","self-authored-test:quiz-denominator","confirmed","{}");
            admin.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready,publication_state) VALUES (?,?,?,?,?,?,?,TRUE,'published')",fiveVersion,"demo-01",5,fiveVersion+"-license","0".repeat(64),"0".repeat(64),"{}");
            String pi=UUID.randomUUID().toString();
            admin.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",pi,"demo-01",pi);
            admin.update("INSERT INTO paragraph(id,version_id,lesson_id,identity_id,stable_key,sequence_no) VALUES (?,?,?,?,?,1)",fiveVersion+"-p",fiveVersion,"demo-01",pi,"q5-p");
            var five=new LinkedHashMap<String,String>();
            for(int i=1;i<=5;i++) {
                String exercise=fiveVersion+"-quiz-"+i,sentence=fiveVersion+"-s"+i,point=fiveVersion+"-kp-"+i,asset=fiveVersion+"-a"+i,identity=UUID.randomUUID().toString();
                java.nio.file.Path path=java.nio.file.Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"),"publication",fiveVersion,i+".mp3");java.nio.file.Files.createDirectories(path.getParent());java.nio.file.Files.write(path,tone);
                admin.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,?,?,'audio/mpeg',?,2000,?,'ready')",asset,fiveVersion,fiveVersion+"-license","original_recording","publication/"+fiveVersion+"/"+i+".mp3",tone.length,toneHash);
                admin.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,"demo-01",identity);
                admin.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,'q5-"+i+"',?,'Writer',?, '原创句','本地预置讲解','original',?,0,2000,?,?)",sentence,"demo-01",fiveVersion,i,"第"+i+"句原文。",asset,fiveVersion+"-p",identity);
                admin.update("INSERT INTO knowledge_point(id,lesson_id,version_id,sentence_id,term,meaning,usage_note,example_text) VALUES (?,?,?,?, 'q5','q5','q5','q5')",point,"demo-01",fiveVersion,sentence);
                admin.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind,algorithm_version) VALUES (?,?,?,?, 'quiz_choice','quiz_choice_v1')",exercise,"demo-01",fiveVersion,sentence);
                String questionJson=mapper.writeValueAsString(Map.of("id",exercise,"prompt","第"+i+"题","options",List.of(Map.of("id",exercise+"-a","text","alpha"),Map.of("id",exercise+"-b","text","beta")),"answerKey",exercise+"-a"));
                admin.update("INSERT INTO quiz_question(exercise_id,version_id,sentence_id,knowledge_point_id,payload_json) VALUES (?,?,?,?,?)",exercise,fiveVersion,sentence,point,questionJson);
                five.put(exercise,i<=4?exercise+"-a":exercise+"-b");
            }
            extraSet=UUID.randomUUID().toString();
            admin.update("INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES (?,?,'practice','quiz_choice_v1','version_content')",extraSet,fiveVersion);
            for(int i=1;i<=5;i++) {
                String exercise=fiveVersion+"-quiz-"+i,sentence=fiveVersion+"-s"+i,point=fiveVersion+"-kp-"+i;
                String questionJson=mapper.writeValueAsString(mapper.readTree(admin.queryForObject("SELECT payload_json FROM quiz_question WHERE exercise_id=?",String.class,exercise)));
                admin.update("INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) VALUES (?,?,?,?,?,?,?,?)",extraSet,exercise,fiveVersion,sentence,point,i,questionJson,QuizSets.itemHash(Map.of("exercise_id",exercise,"ordinal",i,"sentence_id",sentence,"knowledge_point_id",point,"question_text",questionJson)));
                String stored=admin.queryForObject("SELECT CAST(question_json AS CHAR CHARACTER SET utf8mb4) FROM exercise_set_item WHERE set_id=? AND exercise_id=?",String.class,extraSet,exercise);
                admin.update("UPDATE exercise_set_item SET item_hash=? WHERE set_id=? AND exercise_id=?",QuizSets.itemHash(Map.of("exercise_id",exercise,"ordinal",i,"sentence_id",sentence,"knowledge_point_id",point,"question_text",stored)),extraSet,exercise);
            }
            var items=admin.queryForList("SELECT i.*,CAST(i.question_json AS CHAR CHARACTER SET utf8mb4) AS question_text FROM exercise_set_item i WHERE set_id=? ORDER BY ordinal",extraSet);
            String extraHash=QuizSets.setHash(fiveVersion,null,items);
            admin.update("UPDATE exercise_set SET set_hash=?,frozen=TRUE WHERE id=?",extraHash,extraSet);
            var fiveQuiz=json(send(base+"/quiz?lessonId=demo-01&versionId="+fiveVersion,"GET",null));
            assertEquals(5,fiveQuiz.path("totalCount").asInt());assertEquals(extraHash,fiveQuiz.path("setHash").asText());
            String big=UUID.randomUUID().toString();parents.add(big);
            var bigBody=new LinkedHashMap<String,Object>(body);bigBody.put("versionId",fiveVersion);bigBody.put("setId",extraSet);bigBody.put("setHash",extraHash);bigBody.put("eventId",big);bigBody.put("answers",five);
            var second=send(base+"/quiz/sets/"+extraSet+"/attempts","POST",bigBody);assertEquals(200,second.statusCode(),second.body());
            assertEquals(4,json(second).path("correctCount").asInt());assertEquals(5,json(second).path("totalCount").asInt());
            var after=json(send(base+"/reports","GET",null));
            assertEquals(before.path("metrics").path("quiz").path("verifiedRuns").asInt()+2,after.path("metrics").path("quiz").path("verifiedRuns").asInt());
            assertEquals(before.path("metrics").path("quiz").path("correct").asInt()+5,after.path("metrics").path("quiz").path("correct").asInt());
            assertEquals(before.path("metrics").path("quiz").path("total").asInt()+8,after.path("metrics").path("quiz").path("total").asInt());
            double accuracy=(before.path("metrics").path("quiz").path("correct").asInt()+5.0)/(before.path("metrics").path("quiz").path("total").asInt()+8);
            assertEquals(accuracy,after.path("metrics").path("quiz").path("accuracy").asDouble(),1e-9);
            // Unverified history must not enter numerator or denominator.
            String orphan=UUID.randomUUID().toString();
            admin.update("INSERT INTO command_receipt(event_id,payload_hash,response_json) VALUES (?,SHA2(?,256),NULL)",orphan,orphan);
            admin.update("INSERT INTO quiz_run(id,event_id,lesson_id,version_id,correct_count,total_count,submitted_count,set_id,set_hash,exposure_status,measurement_policy_version) VALUES (?,?, 'demo-01',?,0,5,5,?,?,'unknown','quiz_choice_v1')",orphan,orphan,version,setId,setHash);
            parents.add(orphan);
            var withOrphan=json(send(base+"/reports","GET",null));
            assertEquals(after.path("metrics").path("quiz").path("correct").asInt(),withOrphan.path("metrics").path("quiz").path("correct").asInt());
            assertEquals(after.path("metrics").path("quiz").path("total").asInt(),withOrphan.path("metrics").path("quiz").path("total").asInt());
            assertEquals(after.path("metrics").path("quiz").path("unverifiedRuns").asInt()+1,withOrphan.path("metrics").path("quiz").path("unverifiedRuns").asInt());
        } finally {
            app.close();
            for(String e:parents) {
                var attempts=admin.queryForList("SELECT a.id,a.event_id FROM exercise_attempt a JOIN quiz_answer b ON b.attempt_id=a.id JOIN quiz_run r ON r.id=b.run_id WHERE r.event_id=?",e);
                admin.update("DELETE i FROM quiz_run_item i JOIN quiz_run r ON r.id=i.run_id WHERE r.event_id=?",e);
                for(var a:attempts) {
                    admin.update("DELETE FROM review_source WHERE attempt_id=?",a.get("id"));
                    admin.update("DELETE FROM learning_evidence WHERE attempt_id=?",a.get("id"));
                    admin.update("DELETE FROM quiz_answer WHERE attempt_id=?",a.get("id"));
                    admin.update("DELETE FROM exercise_attempt WHERE id=?",a.get("id"));
                    admin.update("DELETE FROM command_receipt WHERE event_id=?",a.get("event_id"));
                }
                admin.update("DELETE FROM quiz_run WHERE event_id=?",e);admin.update("DELETE FROM command_receipt WHERE event_id=?",e);
            }
            for(var item:admin.queryForList("SELECT id FROM review_item WHERE version_id=? AND card_kind='quiz_choice'",version)) {
                String id=item.get("id").toString();
                if(originalItems.stream().noneMatch(o->o.get("id").toString().equals(id))) {
                    admin.update("DELETE FROM review_source WHERE item_id=?",id);admin.update("DELETE FROM review_item WHERE id=?",id);
                }
            }
            if(extraSet!=null) {
                admin.update("DELETE FROM quiz_progress WHERE version_id='demo-01-v5q'");
                admin.update("DELETE FROM review_item WHERE version_id='demo-01-v5q'");
                admin.execute("DROP TRIGGER IF EXISTS quiz_item_no_delete");admin.execute("DROP TRIGGER IF EXISTS quiz_set_no_delete");
                admin.update("DELETE FROM exercise_set_item WHERE set_id=?",extraSet);
                admin.update("DELETE FROM exercise_set WHERE id=?",extraSet);
                admin.execute("CREATE TRIGGER quiz_set_no_delete BEFORE DELETE ON exercise_set FOR EACH ROW BEGIN IF OLD.frozen THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz set is immutable'; END IF; END");
                admin.execute("CREATE TRIGGER quiz_item_no_delete BEFORE DELETE ON exercise_set_item FOR EACH ROW BEGIN IF (SELECT frozen FROM exercise_set WHERE id=OLD.set_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Frozen quiz items are immutable'; END IF; END");
                for(int i=1;i<=5;i++) {
                    admin.update("DELETE FROM quiz_question WHERE exercise_id=?","demo-01-v5q-quiz-"+i);
                    admin.update("DELETE FROM exercise WHERE id=?","demo-01-v5q-quiz-"+i);
                    admin.update("DELETE FROM knowledge_point WHERE id=?","demo-01-v5q-kp-"+i);
                }
                admin.update("DELETE FROM sentence WHERE lesson_version_id='demo-01-v5q'");
                admin.update("DELETE FROM sentence_identity WHERE lesson_id='demo-01' AND id LIKE 'demo-01-v5q%' OR registry_key LIKE 'demo-01-v5q%'");
                admin.update("DELETE FROM audio_asset WHERE lesson_version_id='demo-01-v5q'");
                admin.update("DELETE FROM paragraph WHERE id='demo-01-v5q-p'");
                admin.update("DELETE FROM paragraph_identity WHERE id='demo-01-v5q-p' OR registry_key='demo-01-v5q-p'");
                admin.update("DELETE FROM lesson_version WHERE id='demo-01-v5q'");
                admin.update("DELETE FROM content_license WHERE id='demo-01-v5q-license'");
            }
        }
    }
    private JsonNode json(HttpResponse<String> r){return mapper.readTree(r.body());}
    private HttpResponse<String> send(String url,String method,Object body)throws Exception{return client.send(request(url,method,body==null?null:mapper.writeValueAsString(body)),HttpResponse.BodyHandlers.ofString());}
    private HttpRequest request(String url,String method,String json){return HttpRequest.newBuilder(URI.create(url)).header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").method(method,json==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(json)).build();}
}
