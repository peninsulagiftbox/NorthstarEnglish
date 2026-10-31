package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.boot.builder.SpringApplicationBuilder;
import local.northstar.NorthstarApplication;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

/** All content/authorization metadata here is explicitly synthetic and isolated, not human acceptance. */
@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class AudioIntegrationTest {
    final ContentPublicationIntegrationTest f=new ContentPublicationIntegrationTest();
    JsonNode materials;String base;final HttpClient http=HttpClient.newHttpClient();
    @AfterEach void removeSyntheticCatalogRows()throws Exception {
        if(f.db==null)return;
        f.tx.executeWithoutResult(status->{
            f.db.update("DELETE sr FROM study_resume sr JOIN lesson_version v ON v.id=sr.version_id AND v.lesson_id=sr.lesson_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE aa FROM audio_alignment aa JOIN lesson_version v ON v.id=aa.version_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE la FROM lesson_audio la JOIN lesson_version v ON v.id=la.version_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE cv FROM content_validation cv JOIN lesson_version v ON v.id=cv.version_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE e FROM exercise e JOIN lesson_version v ON v.id=e.version_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE s FROM sentence s JOIN lesson_version v ON v.id=s.lesson_version_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE FROM sentence_identity WHERE lesson_id LIKE 'c1-%'");
            f.db.update("DELETE a FROM audio_asset a JOIN lesson_version v ON v.id=a.lesson_version_id WHERE v.lesson_id LIKE 'c1-%'");
            f.db.update("DELETE FROM paragraph WHERE lesson_id LIKE 'c1-%'");
            f.db.update("DELETE FROM paragraph_identity WHERE lesson_id LIKE 'c1-%'");
            f.db.update("UPDATE lesson SET current_version_id=NULL WHERE id LIKE 'c1-%'");
            f.db.update("DELETE FROM lesson_version WHERE lesson_id LIKE 'c1-%'");
            f.db.update("DELETE FROM publication_audit WHERE lesson_id LIKE 'c1-%'");
            f.db.update("DELETE FROM content_license WHERE id LIKE 'c1-%'");
            f.db.update("DELETE FROM lesson WHERE id LIKE 'c1-%'");
        });
    }
    JsonNode material(String name){for(var a:materials.path("assets"))if(name.equals(a.path("name").asText()))return a;throw new AssertionError(name);}
    String create(String lesson,String version,int number,String name,int count,boolean shared)throws Exception {
        if(number==1)f.lesson(lesson,"original");f.fixture(lesson,version,number,"original_tts",count);
        var assets=new ArrayList<Map<String,Object>>();var payload=(ObjectNode)f.json.readTree(Files.readAllBytes(f.root.resolve("packages/"+version+"/lesson.json")));
        var main=material(name);String first=version+"-a1";
        for(int i=1;i<=count;i++) {
            var media=shared?main:material("independent-"+List.of(1,6,12).get(i-1));
            var segment=media.path("segments").get(shared?i-1:0);String asset=shared?first:version+"-a"+i;
            String text=segment.path("text").asText();int start=segment.path("startMs").asInt(),end=segment.path("endMs").asInt();
            f.db.update("UPDATE sentence SET audio_asset_id=?,start_ms=?,end_ms=?,text=? WHERE id=?",asset,start,end,text,version+"-s"+i);
            ((ObjectNode)payload.path("sentences").get(i-1)).put("audioAssetId",asset).put("startMs",start).put("endMs",end).put("text",text);
            if(!shared || i==1) {
                Path source=Path.of(System.getenv("NORTHSTAR_AUDIO_FIXTURES")).getParent().resolve(media.path("name").asText()+".mp3");String key="c1/"+version+"/"+asset+".mp3";Path target=f.root.resolve(key);Files.createDirectories(target.getParent());Files.copy(source,target);
                f.db.update("UPDATE audio_asset SET storage_key=?,byte_size=?,duration_ms=?,sha256=? WHERE id=?",key,media.path("bytes").asInt(),media.path("durationMs").asInt(),media.path("sha256").asText(),asset);
                assets.add(Map.of("id",asset,"licenseId",version+"-license","sourceKind","original_tts","storageKey",key,"mimeType","audio/mpeg","byteSize",media.path("bytes").asInt(),"durationMs",media.path("durationMs").asInt(),"sha256",media.path("sha256").asText()));
            }
        }
        if(shared) {
            f.db.update("DELETE FROM audio_asset WHERE lesson_version_id=? AND id<>?",version,first);
            f.db.update("INSERT INTO lesson_audio(version_id,asset_id) VALUES (?,?)",version,first);payload.put("fullAudioAssetId",first);
        }
        for(var a:assets) {
            String transcript=f.db.queryForList("SELECT text FROM sentence WHERE lesson_version_id=? AND audio_asset_id=? ORDER BY sequence_no",String.class,version,a.get("id")).stream().collect(java.util.stream.Collectors.joining("\n"))+"\n";
            f.db.update("INSERT INTO audio_alignment(id,version_id,asset_id,audio_sha256,transcript_sha256,timebase,tool,tool_version,parameters_json,status,reviewer,reviewed_at) VALUES (?,?,?,?,?,'asset_milliseconds','synthetic-rule-fixture','1','{\"humanReviewed\":false,\"testOnly\":true}','verified','synthetic-isolated-rule-test',UTC_TIMESTAMP(3))",a.get("id")+"-align",version,a.get("id"),a.get("sha256"),ContentPackage.sha256(transcript.getBytes(StandardCharsets.UTF_8)));
        }
        byte[] raw=(payload.toString()+"\n").getBytes(StandardCharsets.UTF_8);String hash=ContentPackage.sha256(raw);
        var manifest=f.json.createObjectNode().put("lessonId",lesson).put("versionId",version).put("lessonSha256",hash);manifest.set("audioAssets",f.json.valueToTree(assets));byte[] mr=(manifest.toString()+"\n").getBytes(StandardCharsets.UTF_8);
        Files.write(f.root.resolve("packages/"+version+"/lesson.json"),raw);Files.write(f.root.resolve("packages/"+version+"/manifest.json"),mr);
        f.db.update("UPDATE lesson_version SET payload_json=?,content_sha256=?,manifest_sha256=?,schema_version='northstar.local.audio.v1' WHERE id=?",payload.toString(),hash,ContentPackage.sha256(mr),version);
        if(version.equals("c1-shared-v1")) {
            f.db.update("UPDATE audio_alignment SET status='needs_review' WHERE version_id=?",version);
            assertEquals("ALIGNMENT_NOT_VERIFIED",f.service.validate(lesson,version,"synthetic-isolated-rule-test"));
            f.db.update("UPDATE audio_alignment SET status='verified' WHERE version_id=?",version);
        }
        assertEquals("VALIDATED",f.service.validate(lesson,version,"synthetic-isolated-rule-test"));
        String current=f.db.queryForObject("SELECT current_version_id FROM lesson WHERE id=?",String.class,lesson);
        assertEquals("PUBLISHED",f.service.execute(new ContentPublication.Request(UUID.randomUUID().toString(),"publish",lesson,version,current,hash,"synthetic-isolated-rule-test")).code());return hash;
    }
    HttpResponse<String> request(String path,String method,Object data,String revision)throws Exception {
        var b=HttpRequest.newBuilder(URI.create(base+path));
        if(data!=null){b.header("Origin","http://127.0.0.1:"+System.getenv("WEB_PORT")).header("X-Northstar-Request","local-workspace").header("Content-Type","application/json");if(revision!=null)b.header("If-Match",revision);b.method(method,HttpRequest.BodyPublishers.ofString(f.json.writeValueAsString(data)));}
        return http.send(b.build(),HttpResponse.BodyHandlers.ofString());
    }
    JsonNode get(String path,int status)throws Exception {var r=request(path,"GET",null,null);assertEquals(status,r.statusCode(),path+" "+r.body());return f.json.readTree(r.body());}
    @Test void newAudioProfileRequiresDecodedDurationAndKeepsLegacyProfileCompatible()throws Exception {
        f.setup();materials=f.json.readTree(Files.readAllBytes(Path.of(System.getenv("NORTHSTAR_AUDIO_FIXTURES"))));
        create("c1-duration-good","c1-duration-good-v1",1,"independent-1",1,true);
        f.lesson("c1-duration-bad","original");f.fixture("c1-duration-bad","c1-duration-bad-v1",1,"original_tts",1);
        f.db.update("UPDATE lesson_version SET schema_version='northstar.local.audio.v1' WHERE id='c1-duration-bad-v1'");
        assertEquals("MEDIA_DURATION_MISMATCH",f.service.validate("c1-duration-bad","c1-duration-bad-v1","synthetic-isolated-rule-test"));
        assertEquals("draft",f.db.queryForObject("SELECT publication_state FROM lesson_version WHERE id='c1-duration-bad-v1'",String.class));
    }
    @Test void rejectsFractionalPayloadCoordinatesRatherThanTruncating()throws Exception {
        f.setup();f.lesson("c1-numeric","original");f.fixture("c1-numeric","c1-numeric-v1",1,"original_tts",1);
        Path directory=f.root.resolve("packages/c1-numeric-v1");var payload=(ObjectNode)f.json.readTree(Files.readAllBytes(directory.resolve("lesson.json")));
        ((ObjectNode)payload.path("sentences").get(0)).put("startMs",0.5);
        byte[] raw=(payload.toString()+"\n").getBytes(StandardCharsets.UTF_8);String hash=ContentPackage.sha256(raw);
        var manifest=(ObjectNode)f.json.readTree(Files.readAllBytes(directory.resolve("manifest.json")));manifest.put("lessonSha256",hash);byte[] mr=(manifest.toString()+"\n").getBytes(StandardCharsets.UTF_8);
        Files.write(directory.resolve("lesson.json"),raw);Files.write(directory.resolve("manifest.json"),mr);
        f.db.update("UPDATE lesson_version SET payload_json=?,content_sha256=?,manifest_sha256=? WHERE id='c1-numeric-v1'",payload.toString(),hash,ContentPackage.sha256(mr));
        assertEquals("INTERVAL_INVALID",f.service.validate("c1-numeric","c1-numeric-v1","synthetic-isolated-rule-test"));
        assertEquals("draft",f.db.queryForObject("SELECT publication_state FROM lesson_version WHERE id='c1-numeric-v1'",String.class));
    }
    @Test void sharedAudioPublicationMediaFailuresAndExplicitResume()throws Exception {
        f.setup();materials=f.json.readTree(Files.readAllBytes(Path.of(System.getenv("NORTHSTAR_AUDIO_FIXTURES"))));
        var demo=f.db.queryForList("SELECT * FROM sentence WHERE lesson_id='demo-01' ORDER BY id");
        create("c1-shared","c1-shared-v1",1,"shared-v1",12,true);
        create("c1-shared","c1-shared-v2",2,"shared-v2",12,true);
        create("c1-independent","c1-independent-v1",1,"independent-1",3,false);
        String longHash=create("c1-long","c1-long-v1",1,"long-660s",1,true);
        assertThrows(org.springframework.dao.DataAccessException.class,()->f.db.update("INSERT INTO lesson_audio(version_id,asset_id) VALUES ('demo-01-v1','c1-shared-v1-a1')"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->f.db.update("UPDATE sentence SET audio_asset_id='c1-shared-v2-a1' WHERE id='c1-shared-v1-s1'"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->f.db.update("UPDATE sentence SET start_ms=-1 WHERE id='c1-shared-v1-s1'"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->f.db.update("UPDATE sentence SET end_ms=start_ms WHERE id='c1-shared-v1-s1'"));
        try(var app=new SpringApplicationBuilder(NorthstarApplication.class).run("--server.port=0")) {
            base="http://127.0.0.1:"+app.getEnvironment().getRequiredProperty("local.server.port")+"/api/v1";
            var lesson=get("/lessons/c1-shared?versionId=c1-shared-v1",200);assertEquals(12,lesson.path("sentences").size());assertEquals(1,lesson.path("audioAssets").size());assertEquals(800,lesson.path("sentences").get(0).path("startMs").asInt());
            assertNotEquals(lesson.path("fullAudioAssetId").asText(),get("/lessons/c1-shared",200).path("fullAudioAssetId").asText());
            String audio="/audio/c1-shared-v1-a1";
            var bytes=http.send(HttpRequest.newBuilder(URI.create(base+audio)).build(),HttpResponse.BodyHandlers.ofByteArray());assertEquals(200,bytes.statusCode());assertEquals(material("shared-v1").path("sha256").asText(),ContentPackage.sha256(bytes.body()));
            for(var entry:Map.of("bytes=0-31",206,"bytes=-32",206,"bytes=999999999-",416).entrySet())assertEquals(entry.getValue(),http.send(HttpRequest.newBuilder(URI.create(base+audio)).header("Range",entry.getKey()).build(),HttpResponse.BodyHandlers.discarding()).statusCode());
            String key=f.db.queryForObject("SELECT storage_key FROM audio_asset WHERE id='c1-shared-v1-a1'",String.class);Path file=f.root.resolve(key);byte[] original=Files.readAllBytes(file);
            for(String invalid:List.of("missing.mp3","../../outside.mp3","%2e%2e/outside.mp3")) {
                f.db.update("UPDATE audio_asset SET storage_key=? WHERE id='c1-shared-v1-a1'",invalid);assertEquals("AUDIO_UNAVAILABLE",get(audio,503).path("code").asText());assertEquals("unavailable",get("/lessons/c1-shared?versionId=c1-shared-v1",200).path("sentences").get(0).path("audio").path("status").asText());
            }
            f.db.update("UPDATE audio_asset SET storage_key=? WHERE id='c1-shared-v1-a1'",key);
            try {
                Files.write(file,"corrupt MPEG fixture".getBytes(StandardCharsets.UTF_8));f.db.update("UPDATE audio_asset SET byte_size=?,sha256=? WHERE id='c1-shared-v1-a1'",Files.size(file),ContentPackage.sha256(Files.readAllBytes(file)));get(audio,503);
                var before=f.db.queryForList("SELECT * FROM command_receipt ORDER BY event_id");
                var attempt=Map.of("eventId",UUID.randomUUID().toString(),"lessonId","c1-shared","versionId","c1-shared-v1","sentenceId","c1-shared-v1-s1","text","An original answer.","audioPlayed",true,"answerExposed",false,"clientOccurredAt",java.time.Instant.now().toString());
                assertEquals(503,request("/exercises/c1-shared-v1-s1-dictation/attempts","POST",attempt,null).statusCode());assertEquals(before,f.db.queryForList("SELECT * FROM command_receipt ORDER BY event_id"));assertEquals(0,f.db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='c1-shared'",Integer.class));
            } finally {Files.write(file,original);f.db.update("UPDATE audio_asset SET byte_size=?,sha256=? WHERE id='c1-shared-v1-a1'",original.length,ContentPackage.sha256(original));}
            // Tamper with bytes without updating the trusted hash, then restore.
            original[original.length/2]^=1;Files.write(file,original);get(audio,503);original[original.length/2]^=1;Files.write(file,original);assertEquals(200,request(audio,"GET",null,null).statusCode());
            Path hidden=file.resolveSibling("held.mp3");Files.move(file,hidden);
            try {get(audio,503);assertEquals("unavailable",get("/lessons/c1-shared?versionId=c1-shared-v1",200).path("audioAssets").get(0).path("status").asText());}
            finally {Files.move(hidden,file);}
            Path outside=Files.createTempFile("northstar-c1-outside-", ".mp3");Path link=file.resolveSibling("outside-link.mp3");Files.write(outside,original);Files.createSymbolicLink(link,outside);
            try {f.db.update("UPDATE audio_asset SET storage_key=? WHERE id='c1-shared-v1-a1'",key.replace(file.getFileName().toString(),link.getFileName().toString()));get(audio,503);}
            finally {f.db.update("UPDATE audio_asset SET storage_key=? WHERE id='c1-shared-v1-a1'",key);Files.deleteIfExists(link);Files.deleteIfExists(outside);}
            var beforeResume=f.db.queryForList("SELECT * FROM study_resume");
            var checkpoint=new LinkedHashMap<String,Object>(Map.of("lessonId","c1-long","versionId","c1-long-v1","sentenceId","c1-long-v1-s1","tab","text","showEnglish",true,"showTranslation",true,"playingSentenceId","c1-long-v1-s1","positionMs",5000,"playbackCoordinate","segment_offset_v1"));
            checkpoint.put("playbackMode","full");checkpoint.put("fullAssetId","c1-long-v1-a1");checkpoint.put("assetPositionMs",645000);
            var current=request("/study/resume","GET",null,null);String revision=current.statusCode()==204?"\"0\"":current.headers().firstValue("ETag").orElseThrow();
            var saved=request("/study/resume","PUT",checkpoint,revision);assertEquals(200,saved.statusCode(),saved.body());revision=saved.headers().firstValue("ETag").orElseThrow();var resume=get("/study/resume",200);assertEquals(5000,resume.path("positionMs").asInt());assertEquals(645000,resume.path("assetPositionMs").asInt());
            for(int invalid:List.of(10001,-1)){checkpoint.put("positionMs",invalid);assertEquals(400,request("/study/resume","PUT",checkpoint,revision).statusCode());}
            checkpoint.put("positionMs",10000);checkpoint.put("assetPositionMs",650000);assertEquals(200,request("/study/resume","PUT",checkpoint,revision).statusCode());
            checkpoint.put("versionId","c1-shared-v2");checkpoint.put("lessonId","c1-shared");checkpoint.put("sentenceId","c1-shared-v2-s1");checkpoint.put("playingSentenceId","c1-shared-v2-s1");assertEquals(400,request("/study/resume","PUT",checkpoint,"\""+get("/study/resume",200).path("rowVersion").asLong()+"\"").statusCode());
            String latest=request("/study/resume","GET",null,null).headers().firstValue("ETag").orElseThrow();
            checkpoint.put("lessonId","c1-long");checkpoint.put("versionId","c1-long-v1");checkpoint.put("sentenceId","c1-long-v1-s1");checkpoint.put("playingSentenceId","c1-long-v1-s1");checkpoint.put("positionMs",0);checkpoint.put("assetPositionMs",660049);
            assertEquals(400,request("/study/resume","PUT",checkpoint,latest).statusCode());
            checkpoint.put("assetPositionMs",645000);checkpoint.put("fullAssetId","c1-shared-v1-a1");assertEquals(400,request("/study/resume","PUT",checkpoint,latest).statusCode());
            // Original Demo checkpoint values restored exactly after the isolated resume probe.
            f.db.update("DELETE FROM study_resume");
            for(var row:beforeResume)throw new AssertionError("Expected clean isolated resume for this campaign");
            int start=f.db.queryForObject("SELECT start_ms FROM sentence WHERE id='c1-shared-v1-s2'",Integer.class);
            f.db.update("UPDATE sentence SET start_ms=0 WHERE id='c1-shared-v1-s2'");get("/lessons/c1-shared?versionId=c1-shared-v1",503);f.db.update("UPDATE sentence SET start_ms=? WHERE id='c1-shared-v1-s2'",start);
            assertEquals("WITHDRAWN",f.service.execute(new ContentPublication.Request(UUID.randomUUID().toString(),"withdraw","c1-long","c1-long-v1","c1-long-v1",longHash,"synthetic-isolated-rule-test")).code());get("/audio/c1-long-v1-a1",410);
            create("c1-long","c1-long-v2",2,"long-660s",1,true);
        }
        assertEquals(demo,f.db.queryForList("SELECT * FROM sentence WHERE lesson_id='demo-01' ORDER BY id"));
    }
}
