package local.northstar.catalog;

import static org.junit.jupiter.api.Assertions.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

@EnabledIfEnvironmentVariable(named="NORTHSTAR_DB_TEST",matches="1")
class ContentPublicationIntegrationTest {
    final JsonMapper json=JsonMapper.builder().build();
    JdbcTemplate db;TransactionTemplate tx;Path root;ContentPublication service;
    void setup(){
        String port=System.getenv("MYSQL_PORT");assertNotEquals("3308",port);assertEquals("northstar_phase01_test",System.getenv("DB_NAME"));
        var ds=new DriverManagerDataSource("jdbc:mysql://127.0.0.1:"+port+"/northstar_phase01_test?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true&characterEncoding=UTF-8","northstar_migrator",System.getenv("DB_MIGRATION_PASSWORD"));
        db=new JdbcTemplate(ds);assertEquals(System.getenv("NORTHSTAR_EXPECTED_DB_UUID"),db.queryForObject("SELECT @@server_uuid",String.class));assertNotEquals("104d5d9d-cd3f-11f1-8da4-920f115cf5cb",System.getenv("NORTHSTAR_EXPECTED_DB_UUID"));
        tx=new TransactionTemplate(new DataSourceTransactionManager(ds));root=Path.of(System.getenv("NORTHSTAR_CONTENT_ROOT"));service=new ContentPublication(db,tx,root);
    }
    void license(String id,String type,String medium)throws Exception{
        var details=json.createObjectNode().put("id",id).put("sourceType",type).put("medium",medium).put("sourceRef","self-authored-test:"+id).put("reviewStatus","confirmed").put("reviewer","test-fixture-reviewer").put("proofRef","synthetic-rule-fixture-not-third-party-authorization").put("rightsScope","isolated rule validation only; no third-party content or rights claim");
        db.update("INSERT INTO content_license(id,source_type,source_ref,review_status,details_json) VALUES (?,?,?,'confirmed',?)",id,type,details.path("sourceRef").asText(),details.toString());
    }
    void lesson(String id,String kind)throws Exception {
        license(id+"-text",kind.equals("licensed")?"licensed":"original","text");
        db.update("INSERT INTO lesson(id,slug,kind,availability) VALUES (?,?,?,'available')",id,id,kind);
    }
    String fixture(String lesson,String version,int number,String audioKind,int count)throws Exception{
        String al=version+"-license";license(al,audioKind.equals("licensed_audio")?"licensed":"original","audio");
        var payload=json.createObjectNode().put("id",lesson).put("versionId",version).put("title","Self-authored publication fixture").put("version",number);
        var sentences=payload.putArray("sentences");payload.putArray("exercises");
        var manifest=json.createObjectNode().put("lessonId",lesson).put("versionId",version);var assets=manifest.putArray("audioAssets");
        byte[] audio=Files.readAllBytes(Path.of(System.getenv("NORTHSTAR_TEST_AUDIO")));
        db.update("INSERT INTO lesson_version(id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,release_ready) VALUES (?,?,?,?,?,?,?,TRUE)",version,lesson,number,lesson+"-text","0".repeat(64),"0".repeat(64),"{}");
        String pi=UUID.randomUUID().toString();db.update("INSERT INTO paragraph_identity(id,lesson_id,registry_key) VALUES (?,?,?)",pi,lesson,pi);
        db.update("INSERT INTO paragraph(id,version_id,lesson_id,identity_id,stable_key,sequence_no) VALUES (?,?,?,?,?,1)",version+"-p",version,lesson,pi,pi);
        for(int n=1;n<=count;n++){
            String id=version+"-s"+n,asset=version+"-a"+n,key="publication/"+version+"/"+n+".mp3",identity=UUID.randomUUID().toString();
            String text=switch(n){case 2->number==1?"I work today.":"I worked yesterday.";case 3->number==1?"I bring water and I move plants.":"I bring water.";case 4->number==1?"I check soil.":"I move plants.";case 5->number==1?"I water plants.":"I check soil and water plants.";default->"I place the original card beside the window.";};
            Path path=root.resolve(key);Files.createDirectories(path.getParent());Files.write(path,audio);
            db.update("INSERT INTO sentence_identity(id,lesson_id,registry_key) VALUES (?,?,?)",identity,lesson,identity);
            db.update("INSERT INTO audio_asset(id,lesson_version_id,license_id,source_kind,storage_key,mime_type,byte_size,duration_ms,sha256,status) VALUES (?,?,?,?,?,'audio/mpeg',?,2000,?,'ready')",asset,version,al,audioKind,key,audio.length,ContentPackage.sha256(audio));
            db.update("INSERT INTO sentence(id,lesson_id,lesson_version_id,stable_key,sequence_no,speaker,text,translation,explanation,focus,audio_asset_id,start_ms,end_ms,paragraph_id,identity_id) VALUES (?,?,?,?,?,'Writer',?,'原创句','本地预置讲解','original',?,0,2000,?,?)",id,lesson,version,"line-"+n,n,text,asset,version+"-p",identity);
            db.update("INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind) VALUES (?,?,?,?,'dictation')",id+"-dictation",lesson,version,id);
            sentences.addObject().put("id",id).put("speaker","Writer").put("text",text).put("translation","原创句").put("explanation","本地预置讲解").put("focus","original").put("audioAssetId",asset).put("startMs",0).put("endMs",2000);
            assets.addObject().put("id",asset).put("licenseId",al).put("sourceKind",audioKind).put("storageKey",key).put("mimeType","audio/mpeg").put("byteSize",audio.length).put("durationMs",2000).put("sha256",ContentPackage.sha256(audio));
        }
        byte[] raw=(payload.toString()+"\n").getBytes(StandardCharsets.UTF_8);String hash=ContentPackage.sha256(raw);manifest.put("lessonSha256",hash);
        byte[] mr=(manifest.toString()+"\n").getBytes(StandardCharsets.UTF_8);Path directory=root.resolve("packages/"+version);Files.createDirectories(directory);Files.write(directory.resolve("lesson.json"),raw);Files.write(directory.resolve("manifest.json"),mr);
        db.update("UPDATE lesson_version SET payload_json=?,content_sha256=?,manifest_sha256=? WHERE id=?",payload.toString(),hash,ContentPackage.sha256(mr),version);
        return hash;
    }
    ContentPublication.Request request(String lesson,String target,String expected,String hash){return new ContentPublication.Request(UUID.randomUUID().toString(),"publish",lesson,target,expected,hash,"fixture-reviewer");}
    @Test void lifecycleConcurrencyIdentitiesMappingsAndProtection()throws Exception{
        setup();var oldSentences=db.queryForList("SELECT * FROM sentence WHERE lesson_id='demo-01' ORDER BY id");
        var oldAttempts=db.queryForList("SELECT * FROM exercise_attempt ORDER BY id");var oldReviews=db.queryForList("SELECT * FROM review_result ORDER BY event_id");
        lesson("pub-main","original");String h1=fixture("pub-main","pub-v1",1,"original_recording",7),h2=fixture("pub-main","pub-v2",2,"original_recording",7),h3=fixture("pub-main","pub-v3",3,"original_recording",7);
        assertEquals("VERSION_NOT_VALIDATED",service.execute(request("pub-main","pub-v1",null,h1)).code());
        for(String version:List.of("pub-v1","pub-v2","pub-v3"))assertEquals("VALIDATED",service.validate("pub-main",version,"fixture-reviewer"));
        assertEquals("PUBLISHED",service.execute(request("pub-main","pub-v1",null,h1)).code());
        var a=request("pub-main","pub-v2","pub-v1",h2);var b=request("pub-main","pub-v3","pub-v1",h3);
        var barrier=new CyclicBarrier(2);List<ContentPublication.Result> results;
        try(var pool=Executors.newFixedThreadPool(2)){
            var fa=pool.submit(()->{barrier.await();return service.execute(a);});var fb=pool.submit(()->{barrier.await();return service.execute(b);});results=List.of(fa.get(30,TimeUnit.SECONDS),fb.get(30,TimeUnit.SECONDS));
        }
        assertEquals(1,results.stream().filter(r->r.code().equals("PUBLISHED")).count());assertEquals(1,results.stream().filter(r->r.code().equals("CURRENT_VERSION_CONFLICT")).count());
        System.out.println("CAS_RESULTS "+json.writeValueAsString(results));
        for(var pair:List.of(Map.entry(a,results.get(0)),Map.entry(b,results.get(1))))assertEquals(pair.getValue(),service.execute(pair.getKey()));
        assertEquals(2,db.queryForObject("SELECT COUNT(*) FROM publication_audit WHERE operation_id IN (?,?)",Integer.class,a.operationId(),b.operationId()));
        assertEquals("OPERATION_CONFLICT",service.execute(new ContentPublication.Request(a.operationId(),a.action(),a.lessonId(),a.targetVersionId(),"wrong",a.contentSha256(),a.actor())).code());
        String current=db.queryForObject("SELECT current_version_id FROM lesson WHERE id='pub-main'",String.class);
        assertEquals("VERSION_LESSON_MISMATCH",service.execute(request("pub-main","demo-01-v1",current,h1)).code());
        assertEquals("VERSION_LESSON_MISMATCH",service.execute(request("pub-main","missing",current,h1)).code());
        assertEquals("CONTENT_HASH_MISMATCH",service.execute(request("pub-main","pub-v1",current,"0".repeat(64))).code());
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("UPDATE sentence SET identity_id=(SELECT identity_id FROM (SELECT identity_id FROM sentence WHERE id='demo-01-v1-s01') x) WHERE id='pub-v1-s1'"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("UPDATE sentence SET identity_id=(SELECT identity_id FROM (SELECT identity_id FROM sentence WHERE id='pub-v1-s1') x) WHERE id='pub-v1-s2'"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("UPDATE paragraph SET identity_id=(SELECT identity_id FROM (SELECT identity_id FROM paragraph WHERE id='af61b21b-371a-4550-85a2-8301db66a325') x) WHERE id='pub-v1-p'"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("INSERT INTO paragraph(id,version_id,lesson_id,identity_id,stable_key,sequence_no) SELECT 'pub-duplicate-p',version_id,lesson_id,identity_id,'different-position',2 FROM paragraph WHERE id='pub-v1-p'"));
        var commands=new local.northstar.exercise.ExerciseController(db,new DataSourceTransactionManager(db.getDataSource()),new ContentPackage(root.toString()));
        String event=UUID.randomUUID().toString();
        var attempt=new local.northstar.exercise.ExerciseController.Attempt(event,"pub-main","pub-v1","pub-v1-s1","I place the original card beside the window.",false,true,java.time.Instant.now().toString());
        var receipt=commands.attempt("pub-v1-s1-dictation",attempt);assertTrue(receipt.path("result").path("correct").asBoolean());
        var wrong=new local.northstar.exercise.ExerciseController.Attempt(UUID.randomUUID().toString(),"pub-main","pub-v1","pub-v1-s2","I worked tomorrow.",false,true,java.time.Instant.now().toString());
        commands.attempt("pub-v1-s2-dictation",wrong);
        var reviews=new local.northstar.exercise.QuizReviewController(db,commands,new local.northstar.exercise.QuizFault());
        var rating=new local.northstar.exercise.QuizReviewController.ReviewRating(UUID.randomUUID().toString(),"pub-main","pub-v1","pub-v1-s2",1,"good",true,java.time.Instant.now().toString());
        reviews.rate("pub-v1-s2-review",rating);
        oldAttempts=db.queryForList("SELECT * FROM exercise_attempt ORDER BY id");oldReviews=db.queryForList("SELECT * FROM review_result ORDER BY event_id");
        // Identical stable identity still does not move any evidence.
        db.update("UPDATE sentence SET identity_id=(SELECT identity_id FROM (SELECT identity_id FROM sentence WHERE id='pub-v1-s1') x) WHERE id='pub-v2-s1'");
        ContentIdentities.confirm(db,tx,"pub-main","pub-v1","pub-v2","equivalent","pub-eq","fixture-human-role","explicit synthetic review","identical original text and audio",List.of(new ContentIdentities.Edge("pub-v1-s1","pub-v2-s1")));
        ContentIdentities.confirm(db,tx,"pub-main","pub-v1","pub-v2","edited","pub-edit","fixture-human-role","explicit synthetic review","reviewed correction",List.of(new ContentIdentities.Edge("pub-v1-s2","pub-v2-s2")));
        ContentIdentities.confirm(db,tx,"pub-main","pub-v1","pub-v2","split","pub-split","fixture-human-role","explicit synthetic review","one to two",List.of(new ContentIdentities.Edge("pub-v1-s3","pub-v2-s3"),new ContentIdentities.Edge("pub-v1-s3","pub-v2-s4")));
        ContentIdentities.confirm(db,tx,"pub-main","pub-v1","pub-v2","merged","pub-merge","fixture-human-role","explicit synthetic review","two to one",List.of(new ContentIdentities.Edge("pub-v1-s4","pub-v2-s5"),new ContentIdentities.Edge("pub-v1-s5","pub-v2-s5")));
        ContentIdentities.confirm(db,tx,"pub-main","pub-v1","pub-v2","no_target","pub-delete","fixture-human-role","explicit synthetic review","deleted without substitute",List.of(new ContentIdentities.Edge("pub-v1-s6",null)));
        assertThrows(IllegalArgumentException.class,()->ContentIdentities.confirm(db,tx,"pub-main","pub-v1","pub-v2","split","bad","reviewer","fixture","invalid group",List.of(new ContentIdentities.Edge("pub-v1-s7","pub-v2-s7"))));
        assertThrows(org.springframework.dao.DataAccessException.class,()->ContentIdentities.confirm(db,tx,"pub-main","pub-v1","demo-01-v1","edited","cross","reviewer","fixture","cross lesson",List.of(new ContentIdentities.Edge("pub-v1-s7","demo-01-v1-s01"))));
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("INSERT INTO version_sentence_map(id,lesson_id,from_version_id,to_version_id,from_sentence_id,to_sentence_id,relation,mapping_status,mapping_group,reviewer,confirmation_source,reason) VALUES (?,'pub-main','pub-v1','pub-v2','pub-v1-s7','pub-v2-s7',NULL,'confirmed','invalid-null','fixture','synthetic','reject NULL relation')",UUID.randomUUID().toString()));
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("INSERT INTO version_sentence_map(id,lesson_id,from_version_id,to_version_id,from_sentence_id,to_sentence_id,relation,mapping_status,mapping_group,reviewer,confirmation_source,reason) VALUES (?,'pub-main','pub-v1','pub-v2','pub-v1-s6',NULL,NULL,'no_target','duplicate-null','fixture','synthetic','reject duplicate no-target')",UUID.randomUUID().toString()));
        System.out.println("MAPPING_RESULTS "+json.writeValueAsString(db.queryForList("SELECT relation,mapping_status,COUNT(*) AS edges FROM version_sentence_map WHERE lesson_id='pub-main' GROUP BY relation,mapping_status ORDER BY relation")));
        assertEquals("unmapped",new CatalogReader(db).versions("pub-main","pub-v1","pub-v1-s7").get("versions") instanceof List<?> rows?((Map<?,?>)rows.get(1)).get("mappingStatus"):null);
        assertEquals(oldAttempts,db.queryForList("SELECT * FROM exercise_attempt ORDER BY id"));assertEquals(oldReviews,db.queryForList("SELECT * FROM review_result ORDER BY event_id"));assertEquals(oldSentences,db.queryForList("SELECT * FROM sentence WHERE lesson_id='demo-01' ORDER BY id"));
        var withdraw=new ContentPublication.Request(UUID.randomUUID().toString(),"withdraw","pub-main",current,current,current.equals("pub-v2")?h2:h3,"fixture-reviewer");
        assertEquals("WITHDRAWN",service.execute(withdraw).code());assertEquals(service.execute(withdraw),service.execute(withdraw));assertNull(db.queryForObject("SELECT current_version_id FROM lesson WHERE id='pub-main'",String.class));
        assertEquals(410,assertThrows(VersionAccess.Failure.class,()->tx.executeWithoutResult(s->VersionAccess.require(db,"pub-main",current))).status);
        tx.executeWithoutResult(s->VersionAccess.require(db,"pub-main","pub-v1"));
        assertEquals(2,db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE lesson_id='pub-main'",Integer.class));
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE version_id IN ('pub-v2','pub-v3')",Integer.class));
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM study_stage WHERE version_id IN ('pub-v2','pub-v3')",Integer.class));
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM review_item WHERE version_id IN ('pub-v2','pub-v3')",Integer.class));
        var oldWithdrawal=new ContentPublication.Request(UUID.randomUUID().toString(),"withdraw","pub-main","pub-v1",null,h1,"fixture-reviewer");
        assertEquals("WITHDRAWN",service.execute(oldWithdrawal).code());
        assertEquals(receipt,commands.attempt("pub-v1-s1-dictation",attempt));
        var newAttempt=new local.northstar.exercise.ExerciseController.Attempt(UUID.randomUUID().toString(),"pub-main","pub-v1","pub-v1-s1",attempt.text(),false,true,java.time.Instant.now().toString());
        assertEquals(410,assertThrows(VersionAccess.Failure.class,()->commands.attempt("pub-v1-s1-dictation",newAttempt)).status);
        assertEquals(oldAttempts,db.queryForList("SELECT * FROM exercise_attempt ORDER BY id"));
        assertEquals(oldReviews,db.queryForList("SELECT * FROM review_result ORDER BY event_id"));
    }
    @Test void changedSnapshotMediaAndTransactionFailureCannotMoveCurrent()throws Exception {
        setup();lesson("pub-failure","original");String h=fixture("pub-failure","pub-failure-v1",1,"original_tts",1);
        assertEquals("VALIDATED",service.validate("pub-failure","pub-failure-v1","reviewer"));
        db.update("UPDATE sentence SET focus='changed' WHERE id='pub-failure-v1-s1'");
        assertEquals("CONTENT_PROJECTION_MISMATCH",service.execute(request("pub-failure","pub-failure-v1",null,h)).code());
        db.update("UPDATE sentence SET focus='original' WHERE id='pub-failure-v1-s1'");
        db.update("UPDATE sentence SET stable_key='changed' WHERE id='pub-failure-v1-s1'");
        assertEquals("CONTENT_SNAPSHOT_CHANGED",service.execute(request("pub-failure","pub-failure-v1",null,h)).code());
        db.update("UPDATE sentence SET stable_key='line-1' WHERE id='pub-failure-v1-s1'");
        Path media=root.resolve("publication/pub-failure-v1/1.mp3");byte[] bytes=Files.readAllBytes(media);Files.write(media,new byte[]{1,2,3});
        assertEquals("MEDIA_UNAVAILABLE",service.execute(request("pub-failure","pub-failure-v1",null,h)).code());Files.write(media,bytes);
        db.update("UPDATE content_license SET review_status='pending_review' WHERE id='pub-failure-v1-license'");
        assertEquals("LICENSE_NOT_CONFIRMED",service.execute(request("pub-failure","pub-failure-v1",null,h)).code());db.update("UPDATE content_license SET review_status='confirmed' WHERE id='pub-failure-v1-license'");
        var failedDb=new JdbcTemplate(db.getDataSource()) {
            boolean failed=false;
            @Override public int update(String sql,Object... args){if(!failed && sql.startsWith("UPDATE lesson SET current_version_id=")){failed=true;throw new org.springframework.dao.DataIntegrityViolationException("injected after publication-state write");}return super.update(sql,args);}
        };
        var request=request("pub-failure","pub-failure-v1",null,h);var result=new ContentPublication(failedDb,tx,root).execute(request);
        assertEquals("PUBLICATION_ROLLED_BACK",result.code());assertEquals(result,service.execute(request));
        assertNull(db.queryForObject("SELECT current_version_id FROM lesson WHERE id='pub-failure'",String.class));assertEquals("validated",db.queryForObject("SELECT publication_state FROM lesson_version WHERE id='pub-failure-v1'",String.class));
        assertEquals(1,db.queryForObject("SELECT COUNT(*) FROM publication_audit WHERE operation_id=?",Integer.class,request.operationId()));
        assertEquals("PUBLISHED",service.execute(request("pub-failure","pub-failure-v1",null,h)).code());
        lesson("pub-retry","original");String retryHash=fixture("pub-retry","pub-retry-v1",1,"original_tts",1);
        assertEquals("VALIDATED",service.validate("pub-retry","pub-retry-v1","reviewer"));
        var same=request("pub-retry","pub-retry-v1",null,retryHash);var barrier=new CyclicBarrier(2);
        try(var pool=Executors.newFixedThreadPool(2)){
            var first=pool.submit(()->{barrier.await();return service.execute(same);});var second=pool.submit(()->{barrier.await();return service.execute(same);});
            var result1=first.get(30,TimeUnit.SECONDS);var result2=second.get(30,TimeUnit.SECONDS);assertEquals("PUBLISHED",result1.code());assertEquals(result1,result2);
        }
        assertEquals(1,db.queryForObject("SELECT COUNT(*) FROM publication_audit WHERE operation_id=?",Integer.class,same.operationId()));
    }
    @Test void equivalentReferenceDoesNotBecomeNewVersionEvidence()throws Exception {
        setup();lesson("pub-hint","original");String h1=fixture("pub-hint","pub-hint-v1",1,"original_tts",1),h2=fixture("pub-hint","pub-hint-v2",2,"original_tts",1);
        db.update("UPDATE sentence SET identity_id=(SELECT identity_id FROM (SELECT identity_id FROM sentence WHERE id='pub-hint-v1-s1') x) WHERE id='pub-hint-v2-s1'");
        db.update("UPDATE lesson SET availability='draft' WHERE id='pub-hint'");
        assertEquals("VALIDATED",service.validate("pub-hint","pub-hint-v1","synthetic-reviewer"));assertEquals("VALIDATED",service.validate("pub-hint","pub-hint-v2","synthetic-reviewer"));
        assertEquals("PUBLISHED",service.execute(request("pub-hint","pub-hint-v1",null,h1)).code());
        assertEquals("available",db.queryForObject("SELECT availability FROM lesson WHERE id='pub-hint'",String.class));
        var commands=new local.northstar.exercise.ExerciseController(db,new DataSourceTransactionManager(db.getDataSource()),new ContentPackage(root.toString()));
        commands.attempt("pub-hint-v1-s1-dictation",new local.northstar.exercise.ExerciseController.Attempt(UUID.randomUUID().toString(),"pub-hint","pub-hint-v1","pub-hint-v1-s1","I place the original card beside the window.",false,true,java.time.Instant.now().toString()));
        ContentIdentities.confirm(db,tx,"pub-hint","pub-hint-v1","pub-hint-v2","equivalent","pub-hint-equivalent","synthetic-reviewer","synthetic mapping review fixture","same original text and same synthetic test audio",List.of(new ContentIdentities.Edge("pub-hint-v1-s1","pub-hint-v2-s1")));
        assertEquals("PUBLISHED",service.execute(request("pub-hint","pub-hint-v2","pub-hint-v1",h2)).code());
        assertTrue(new CatalogReader(db).lesson("pub-hint","pub-hint-v2").path("hasHistoricalEvidence").asBoolean());
        assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM exercise_attempt WHERE version_id='pub-hint-v2'",Integer.class));assertEquals(0,db.queryForObject("SELECT COUNT(*) FROM study_stage WHERE version_id='pub-hint-v2'",Integer.class));
        var export=new local.northstar.exportimport.ExportController(db);var envelope=export.export();var original=json.readTree(envelope.get("payloadJson"));
        var changed=original.deepCopy();var tables=changed.path("tables");var audit=(tools.jackson.databind.node.ArrayNode)tables.path("publication_audit").path("rows");audit.removeAll();
        String raw=changed.toString();var edited=Map.of("format","northstar.snapshot.v1","sha256",ContentPackage.sha256(raw.getBytes(StandardCharsets.UTF_8)),"payloadJson",raw);
        assertThrows(org.springframework.web.server.ResponseStatusException.class,()->export.preview(json.valueToTree(edited)));
    }
    @Test void withdrawnAudioRetainsOuter404VisibilityBoundaries()throws Exception {
        setup();lesson("pub-audio","original");String hash=fixture("pub-audio","pub-audio-v1",1,"original_tts",1);
        assertEquals("VALIDATED",service.validate("pub-audio","pub-audio-v1","synthetic-reviewer"));
        assertEquals("PUBLISHED",service.execute(request("pub-audio","pub-audio-v1",null,hash)).code());
        assertEquals("WITHDRAWN",service.execute(new ContentPublication.Request(UUID.randomUUID().toString(),"withdraw","pub-audio","pub-audio-v1","pub-audio-v1",hash,"synthetic-reviewer")).code());
        var controller=new CatalogController(db,new ContentPackage(root.toString()),new CatalogReader(db));
        assertEquals(410,assertThrows(VersionAccess.Failure.class,()->controller.audio("pub-audio-v1-a1")).status);
        tx.executeWithoutResult(status->{
            db.update("UPDATE lesson SET availability='withdrawn' WHERE id='pub-audio'");
            assertEquals(org.springframework.http.HttpStatus.NOT_FOUND,assertThrows(CatalogController.CatalogFailure.class,()->controller.audio("pub-audio-v1-a1")).status);
            status.setRollbackOnly();
        });
        for(String license:List.of("pub-audio-text","pub-audio-v1-license"))tx.executeWithoutResult(status->{
            db.update("UPDATE content_license SET review_status='pending_review' WHERE id=?",license);
            assertEquals(org.springframework.http.HttpStatus.NOT_FOUND,assertThrows(CatalogController.CatalogFailure.class,()->controller.audio("pub-audio-v1-a1")).status);
            status.setRollbackOnly();
        });
        assertEquals(410,assertThrows(VersionAccess.Failure.class,()->controller.audio("pub-audio-v1-a1")).status);
    }
    @Test void sourceMatrixAndFailedValidationNeverPublish()throws Exception{
        setup();int i=0;
        for(String kind:List.of("original_demo","original","licensed"))for(String audio:List.of("original_tts","original_recording","licensed_audio")){
            String id="pub-matrix-"+(++i);lesson(id,kind);String hash=fixture(id,id+"-v1",1,audio,1);
            assertEquals("VALIDATED",service.validate(id,id+"-v1","fixture-reviewer"),kind+" / "+audio);
            assertEquals("PUBLISHED",service.execute(request(id,id+"-v1",null,hash)).code());
        }
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("UPDATE lesson SET kind='unknown' WHERE id='pub-matrix-1'"));
        assertThrows(org.springframework.dao.DataAccessException.class,()->db.update("UPDATE audio_asset SET source_kind='unknown' WHERE id='pub-matrix-1-v1-a1'"));
        lesson("pub-invalid","original");String hash=fixture("pub-invalid","pub-invalid-v1",1,"original_tts",1);
        db.update("UPDATE content_license SET source_type='licensed' WHERE id='pub-invalid-v1-license'");
        assertEquals("LICENSE_NOT_CONFIRMED",service.validate("pub-invalid","pub-invalid-v1","fixture-reviewer"));
        db.update("UPDATE content_license SET source_type='original' WHERE id='pub-invalid-v1-license'");
        Files.writeString(root.resolve("packages/pub-invalid-v1/lesson.json"),"{}");assertEquals("CONTENT_HASH_MISMATCH",service.validate("pub-invalid","pub-invalid-v1","fixture-reviewer"));
        assertNull(db.queryForObject("SELECT current_version_id FROM lesson WHERE id='pub-invalid'",String.class));
        assertEquals("VERSION_NOT_VALIDATED",service.execute(request("pub-invalid","pub-invalid-v1",null,hash)).code());
        lesson("pub-unsupported","original");fixture("pub-unsupported","pub-unsupported-v1",1,"original_tts",1);
        db.update("UPDATE lesson_version SET content_readiness='teaching_complete' WHERE id='pub-unsupported-v1'");
        assertEquals("PROFILE_NOT_SUPPORTED",service.validate("pub-unsupported","pub-unsupported-v1","fixture-reviewer"));
        lesson("pub-cli","original");fixture("pub-cli","pub-cli-v1",1,"original_recording",1);
    }
}
