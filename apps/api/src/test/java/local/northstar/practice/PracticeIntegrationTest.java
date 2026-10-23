package local.northstar.practice;

import static org.junit.jupiter.api.Assertions.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
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
class PracticeIntegrationTest {
    final JsonMapper mapper=JsonMapper.builder().build();
    final HttpClient client=HttpClient.newHttpClient();
    @Test void immutableRevisionsConcurrentNumberingRecordingEvidenceDeletionAndRestart() throws Exception {
        assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        Path root=Files.createTempDirectory("northstar-phase06-");
        String task="demo-01-v2-writing-01",sentence="demo-01-v2-s05";
        var events=new ArrayList<String>();var recordings=new ArrayList<String>();
        Map<String,Object> originalUpload=null;
        JdbcTemplate admin=null;List<Map<String,Object>> oldDraft=null,oldProgress=null;
        try {
            try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0","--northstar.recording-root="+root)) {
                var jdbc=app.getBean(JdbcTemplate.class);admin=new JdbcTemplate(app.getBean(Flyway.class).getConfiguration().getDataSource());
                String base="http://127.0.0.1:"+app.getEnvironment().getProperty("local.server.port")+"/api/v1";
                oldDraft=admin.queryForList("SELECT * FROM writing_draft WHERE task_id=?",task);
                oldProgress=admin.queryForList("SELECT * FROM practice_progress WHERE (target_key=? AND kind='writing') OR (target_key=? AND kind='speaking')",task,sentence);
                JsonNode initial=json(send(base+"/writing?lessonId=demo-01&versionId=demo-01-v2","GET",null));
                assertEquals(3,initial.path("sourceSentenceIds").size());long rv=initial.path("draft").path("rowVersion").asLong();
                var draft=new LinkedHashMap<String,Object>(Map.of("lessonId","demo-01","versionId","demo-01-v2","rowVersion",rv,"text","Please help. I can bring water."));
                assertEquals(200,send(base+"/writing/draft","PUT",draft).statusCode());
                assertEquals(412,send(base+"/writing/draft","PUT",draft).statusCode());
                rv++;
                var v1=new LinkedHashMap<String,Object>(Map.of("lessonId","demo-01","versionId","demo-01-v2","draftVersion",rv,"text",draft.get("text"),"eventId",event(events)));
                String body=mapper.writeValueAsString(v1);
                var a=client.sendAsync(req(base+"/writing/revisions","POST",body),HttpResponse.BodyHandlers.ofString());
                var b=client.sendAsync(req(base+"/writing/revisions","POST",body),HttpResponse.BodyHandlers.ofString());
                CompletableFuture.allOf(a,b).join();assertEquals(200,a.join().statusCode(),a.join().body());assertEquals(json(a.join()),json(b.join()));
                String v1id=json(a.join()).path("id").asText();int first=json(a.join()).path("versionNo").asInt();
                v1.put("text","changed");assertEquals(409,send(base+"/writing/revisions","POST",v1).statusCode());
                v1.put("eventId",event(events));assertEquals(412,send(base+"/writing/revisions","POST",v1).statusCode());
                draft.put("rowVersion",rv);draft.put("text","I can put plants beside the bench. Please help.");assertEquals(200,send(base+"/writing/draft","PUT",draft).statusCode());rv++;
                var v2=new LinkedHashMap<String,Object>(Map.of("lessonId","demo-01","versionId","demo-01-v2","draftVersion",rv,"text",draft.get("text"),"eventId",event(events),"parentRevisionId",v1id));
                var v3=new LinkedHashMap<>(v2);v3.put("eventId",event(events));
                a=client.sendAsync(req(base+"/writing/revisions","POST",mapper.writeValueAsString(v2)),HttpResponse.BodyHandlers.ofString());b=client.sendAsync(req(base+"/writing/revisions","POST",mapper.writeValueAsString(v3)),HttpResponse.BodyHandlers.ofString());
                CompletableFuture.allOf(a,b).join();assertEquals(200,a.join().statusCode(),a.join().body());assertEquals(200,b.join().statusCode(),b.join().body());
                assertEquals(Set.of(first+1,first+2),Set.of(json(a.join()).path("versionNo").asInt(),json(b.join()).path("versionNo").asInt()));
                assertEquals("Please help. I can bring water.",jdbc.queryForObject("SELECT raw_text FROM writing_revision WHERE id=?",String.class,v1id));
                assertThrows(org.springframework.dao.DataAccessException.class,()->jdbc.update("UPDATE writing_revision SET raw_text='bad' WHERE id=?",v1id));
                var cross=new LinkedHashMap<>(v2);cross.put("eventId",event(events));cross.put("versionId","demo-01-v1");assertEquals(412,send(base+"/writing/revisions","POST",cross).statusCode());
                // Structural container fixture only. Actual decoding/playback is covered by browser fake microphone.
                byte[] audio=new byte[64];audio[0]=0x1a;audio[1]=0x45;audio[2]=(byte)0xdf;audio[3]=(byte)0xa3;
                var upload=new LinkedHashMap<String,Object>(Map.of("eventId",event(events),"lessonId","demo-01","versionId","demo-01-v2","sentenceId",sentence,"createdAt","2026-10-23T08:00:00Z","mimeType","audio/webm;codecs=opus","durationMs",1000,"audioBase64",Base64.getEncoder().encodeToString(audio)));
                var uploaded=send(base+"/recordings","POST",upload);assertEquals(200,uploaded.statusCode(),uploaded.body());String id=json(uploaded).path("id").asText();recordings.add(id);originalUpload=Map.copyOf(upload);
                assertEquals(json(uploaded),json(send(base+"/recordings","POST",upload)));
                assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM learning_evidence WHERE event_id=?",Integer.class,upload.get("eventId")));
                var playback=new LinkedHashMap<String,Object>(Map.of("eventId",event(events),"lessonId","demo-01","versionId","demo-01-v2","sentenceId","demo-01-v2-s06","observedMs",500,"selfRating","satisfied"));
                assertEquals(422,send(base+"/recordings/"+id+"/playbacks","POST",playback).statusCode());playback.put("sentenceId",sentence);
                var played=send(base+"/recordings/"+id+"/playbacks","POST",playback);assertEquals(200,played.statusCode(),played.body());assertEquals(json(played),json(send(base+"/recordings/"+id+"/playbacks","POST",playback)));
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM learning_evidence WHERE event_id=?",Integer.class,playback.get("eventId")));
                var rating=new LinkedHashMap<String,Object>(Map.of("eventId",event(events),"lessonId","demo-01","versionId","demo-01-v2","sentenceId",sentence,"playbackEventId",playback.get("eventId"),"selfRating","satisfied"));
                var rated=send(base+"/recordings/"+id+"/ratings","POST",rating);assertEquals(200,rated.statusCode(),rated.body());assertEquals(json(rated),json(send(base+"/recordings/"+id+"/ratings","POST",rating)));
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM recording_observation WHERE recording_id=?",Integer.class,id));
                assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM learning_evidence WHERE event_id=?",Integer.class,rating.get("eventId")));
                rating.put("eventId",event(events));rating.put("sentenceId","demo-01-v2-s06");assertEquals(422,send(base+"/recordings/"+id+"/ratings","POST",rating).statusCode());

                upload.put("eventId",event(events));upload.put("sentenceId","demo-01-v1-s05");assertEquals(422,send(base+"/recordings","POST",upload).statusCode());upload.put("sentenceId",sentence);upload.put("mimeType","audio/mp4");assertEquals(415,send(base+"/recordings","POST",upload).statusCode());
                for(String action:List.of("skip","pause","start"))assertEquals(200,send(base+"/practice/events","POST",Map.of("eventId",event(events),"lessonId","demo-01","versionId","demo-01-v2","sentenceId",sentence,"kind","speaking","action",action)).statusCode());
                assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM recording_observation WHERE recording_id=?",Integer.class,id));
                assertEquals(422,send(base+"/recordings/"+id+"/delete","POST",Map.of("eventId",event(events),"confirmed",false)).statusCode());
            }
            // New process context reads the persisted revisions/file and reconciles pending metadata.
            admin.update("UPDATE personal_recording SET status='pending' WHERE id=?",recordings.getFirst());
            try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0","--northstar.recording-root="+root)) {
                String base="http://127.0.0.1:"+app.getEnvironment().getProperty("local.server.port")+"/api/v1";String id=recordings.getFirst();
                assertEquals("ready",admin.queryForObject("SELECT status FROM personal_recording WHERE id=?",String.class,id));
                Path file=root.resolve("northstar_phase01_test").resolve(id+".audio");byte[] original=Files.readAllBytes(file);Files.delete(file);
                app.getBean(RecordingController.class).reconcile();assertEquals("missing",admin.queryForObject("SELECT status FROM personal_recording WHERE id=?",String.class,id));
                assertEquals(404,send(base+"/recordings/"+id+"/audio","GET",null).statusCode());
                Files.write(file,original);Path orphan=file.resolveSibling("unknown.part");Files.write(orphan,new byte[32]);app.getBean(RecordingController.class).reconcile();assertTrue(Files.exists(orphan));
                assertEquals(404,send(base+"/recordings/"+UUID.randomUUID()+"/playbacks","POST",Map.of("eventId",event(events),"lessonId","demo-01","versionId","demo-01-v2","sentenceId",sentence,"observedMs",500,"selfRating","satisfied")).statusCode());
                assertTrue(json(send(base+"/writing?lessonId=demo-01&versionId=demo-01-v2","GET",null)).path("revisions").size()>=3);
                assertEquals(200,client.send(req(base+"/recordings/"+id+"/audio","GET",null),HttpResponse.BodyHandlers.ofByteArray()).statusCode());
                var deletion=Map.of("eventId",event(events),"confirmed",true);
                assertEquals(200,send(base+"/recordings/"+id+"/delete","POST",deletion).statusCode());assertEquals(200,send(base+"/recordings/"+id+"/delete","POST",deletion).statusCode());
                assertEquals(404,send(base+"/recordings/"+id+"/audio","GET",null).statusCode());assertFalse(Files.exists(root.resolve("northstar_phase01_test").resolve(id+".audio")));
                assertEquals(200,send(base+"/recordings","POST",originalUpload).statusCode());assertEquals("deleted",admin.queryForObject("SELECT status FROM personal_recording WHERE id=?",String.class,id));assertFalse(Files.exists(file));
            }
        } finally {
            if(admin!=null) {
                for(String event:events)admin.update("DELETE FROM learning_evidence WHERE event_id=?",event);
                for(String id:recordings){admin.update("DELETE FROM recording_observation WHERE recording_id=?",id);admin.update("DELETE FROM personal_recording WHERE id=?",id);}
                for(var event:events.reversed())admin.update("DELETE FROM writing_revision WHERE event_id=?",event);
                for(String event:events)admin.update("DELETE FROM command_receipt WHERE event_id=?",event);
                admin.update("DELETE FROM writing_draft WHERE task_id=?",task);
                if(oldDraft!=null && !oldDraft.isEmpty()){var d=oldDraft.getFirst();admin.update("INSERT INTO writing_draft(task_id,raw_text,row_version,next_revision,updated_at) VALUES (?,?,?,?,?)",task,d.get("raw_text"),d.get("row_version"),d.get("next_revision"),d.get("updated_at"));}
                admin.update("DELETE FROM practice_progress WHERE (target_key=? AND kind='writing') OR (target_key=? AND kind='speaking')",task,sentence);
                if(oldProgress!=null)for(var p:oldProgress)admin.update("INSERT INTO practice_progress(target_key,kind,current_state) VALUES (?,?,?)",p.get("target_key"),p.get("kind"),p.get("current_state"));
            }
            try(var paths=Files.walk(root)){for(Path p:paths.sorted(Comparator.reverseOrder()).toList())Files.deleteIfExists(p);}
        }
    }
    String event(List<String> events){String id=UUID.randomUUID().toString();events.add(id);return id;}
    JsonNode json(HttpResponse<String> response){return mapper.readTree(response.body());}
    HttpResponse<String> send(String url,String method,Object body)throws Exception{return client.send(req(url,method,body==null?null:mapper.writeValueAsString(body)),HttpResponse.BodyHandlers.ofString());}
    HttpRequest req(String url,String method,String body){return HttpRequest.newBuilder(URI.create(url)).header("Origin","http://127.0.0.1:"+System.getenv().getOrDefault("WEB_PORT","3100")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json").method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofString(body)).build();}
}
