package local.northstar.catalog;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Local content operations only. This class never migrates, seeds or modifies learning records. */
public final class ContentPublication {
    private final JdbcTemplate db;
    private final TransactionTemplate tx;
    private final Path root;
    private final JsonMapper json=JsonMapper.builder().build();
    public record Request(String operationId,String action,String lessonId,String targetVersionId,String expectedCurrentId,String contentSha256,String actor) {}
    public record Result(String operationId,String code,String currentVersionId) {}
    public ContentPublication(JdbcTemplate db,TransactionTemplate tx,Path root){this.db=db;this.tx=tx;this.root=root.toAbsolutePath().normalize();}
    private static class Rejected extends RuntimeException {final String code;Rejected(String code){this.code=code;}}
    private static void check(boolean value,String code){if(!value)throw new Rejected(code);}
    private Map<String,Object> version(String lesson,String version,boolean lock){
        var rows=db.queryForList("SELECT * FROM lesson_version WHERE id=? AND lesson_id=?"+(lock?" FOR UPDATE":""),version,lesson);
        check(rows.size()==1,"VERSION_LESSON_MISMATCH");return rows.getFirst();
    }
    private Object canonical(Object value) {
        if(value instanceof Map<?,?> map){var result=new TreeMap<String,Object>();map.forEach((k,v)->result.put(k.toString(),canonical(v)));return result;}
        if(value instanceof List<?> list)return list.stream().map(this::canonical).toList();
        if(value instanceof JsonNode node)return canonical(json.convertValue(node,Object.class));
        return value;
    }
    private String hash(Object value){return ContentPackage.sha256(json.writeValueAsString(canonical(value)).getBytes(StandardCharsets.UTF_8));}
    public String snapshot(String version){
        var result=new TreeMap<String,Object>();
        result.put("version",db.queryForList("SELECT id,lesson_id,version_no,license_id,content_sha256,manifest_sha256,payload_json,content_readiness,schema_version FROM lesson_version WHERE id=?",version));
        for(String table:List.of("paragraph","sentence","audio_asset","exercise","knowledge_point","reading_question","reading_option","writing_task","writing_source","quiz_question")) {
            String where=switch(table){case "paragraph","exercise","knowledge_point","reading_question","writing_task","writing_source","quiz_question"->"version_id=?";case "reading_option"->"exercise_id IN (SELECT id FROM exercise WHERE version_id=?)";default->"lesson_version_id=?";};
            result.put(table,db.queryForList("SELECT * FROM "+table+" WHERE "+where+" ORDER BY "+(table.equals("reading_question")||table.equals("quiz_question")?"exercise_id":table.equals("writing_source")?"task_id,sentence_id":"id"),version));
        }
        return hash(result);
    }
    private JsonNode raw(String version,String file,String expected){
        try {
            check(version.matches("[A-Za-z0-9_-]{1,64}"),"INVALID_VERSION_ID");
            Path path=root.resolve("packages").resolve(version).resolve(file);
            check(Files.isRegularFile(path) && path.toRealPath().startsWith(root.toRealPath()),"CONTENT_FILE_MISSING");
            byte[] bytes=Files.readAllBytes(path);check(ContentPackage.sha256(bytes).equals(expected),"CONTENT_HASH_MISMATCH");return json.readTree(bytes);
        } catch(java.io.IOException e){throw new Rejected("CONTENT_FILE_MISSING");}
    }
    private void license(String id,String type,String medium){
        var rows=db.queryForList("SELECT * FROM content_license WHERE id=? FOR SHARE",id);check(rows.size()==1,"LICENSE_MISSING");var row=rows.getFirst();
        var details=json.readTree(row.get("details_json").toString());
        check(type.equals(row.get("source_type")) && "confirmed".equals(row.get("review_status")) && medium.equals(details.path("medium").asText()),"LICENSE_NOT_CONFIRMED");
        check(details.path("id").asText().equals(id) && details.path("sourceType").asText().equals(type) && details.path("reviewStatus").asText().equals("confirmed")
                && !details.path("sourceRef").asText().isBlank() && details.path("sourceRef").asText().equals(row.get("source_ref"))
                && !details.path("reviewer").asText().isBlank() && !details.path("proofRef").asText().isBlank() && !details.path("rightsScope").asText().isBlank(),"LICENSE_EVIDENCE_MISSING");
        if(details.has("expiresAt")) {
            try{check(java.time.Instant.parse(details.path("expiresAt").asText()).isAfter(java.time.Instant.now()),"LICENSE_EXPIRED");}
            catch(java.time.format.DateTimeParseException e){throw new Rejected("LICENSE_DATE_INVALID");}
        }
    }
    private void basic(Map<String,Object> v){
        String version=v.get("id").toString(),lesson=v.get("lesson_id").toString();
        check("basic_content".equals(v.get("content_readiness")) && "northstar.local.basic.v1".equals(v.get("schema_version")),"PROFILE_NOT_SUPPORTED");
        JsonNode payload=raw(version,"lesson.json",v.get("content_sha256").toString());
        JsonNode manifest=raw(version,"manifest.json",v.get("manifest_sha256").toString());
        check(payload.equals(json.readTree(v.get("payload_json").toString())) && lesson.equals(payload.path("id").asText()) && version.equals(payload.path("versionId").asText()),"CONTENT_PROJECTION_MISMATCH");
        check(!payload.has("learningPlan") && !payload.has("fullAudioAssetId") && !payload.path("title").asText().isBlank(),"PROFILE_NOT_SUPPORTED");
        check(version.equals(manifest.path("versionId").asText()) && lesson.equals(manifest.path("lessonId").asText()) && v.get("content_sha256").equals(manifest.path("lessonSha256").asText()),"MANIFEST_MISMATCH");
        String kind=db.queryForObject("SELECT kind FROM lesson WHERE id=?",String.class,lesson);
        check(Set.of("original_demo","original","licensed").contains(kind),"INVALID_LESSON_KIND");
        license(v.get("license_id").toString(),kind.equals("licensed")?"licensed":"original","text");
        check(Boolean.TRUE.equals(v.get("release_ready")),"RELEASE_NOT_READY");
        var paragraphs=db.queryForList("SELECT id,sequence_no FROM paragraph WHERE version_id=? ORDER BY sequence_no",version);check(!paragraphs.isEmpty(),"CONTENT_EMPTY");
        var positions=new HashMap<String,Integer>();int pn=0;
        for(var p:paragraphs){check(((Number)p.get("sequence_no")).intValue()==++pn,"PARAGRAPH_ORDER_INVALID");positions.put(p.get("id").toString(),pn);}
        var sentences=db.queryForList("SELECT * FROM sentence WHERE lesson_version_id=? ORDER BY sequence_no",version);
        check(!sentences.isEmpty() && sentences.size()<=1000 && payload.path("sentences").size()==sentences.size(),"CONTENT_EMPTY_OR_INCOMPLETE");
        int sequence=0,previous=0;
        for(var s:sentences){
            check(((Number)s.get("sequence_no")).intValue()==++sequence,"SENTENCE_ORDER_INVALID");
            Integer position=positions.get(s.get("paragraph_id").toString());check(position!=null && position>=previous,"PARAGRAPH_ORDER_INVALID");previous=position;
            JsonNode projected=payload.path("sentences").get(sequence-1);
            for(var pair:Map.of("id","id","text","text","translation","translation","speaker","speaker","explanation","explanation","focus","focus","audioAssetId","audio_asset_id").entrySet())
                check(projected.path(pair.getKey()).asText().equals(s.get(pair.getValue())),"CONTENT_PROJECTION_MISMATCH");
            check(projected.path("startMs").asInt(-1)==((Number)s.get("start_ms")).intValue() && projected.path("endMs").asInt(-1)==((Number)s.get("end_ms")).intValue(),"CONTENT_PROJECTION_MISMATCH");
            check(!s.get("text").toString().isBlank(),"EMPTY_SENTENCE");
        }
        var assets=db.queryForList("SELECT * FROM audio_asset WHERE lesson_version_id=? ORDER BY id",version);
        check(assets.size()==sentences.size() && manifest.path("audioAssets").size()==assets.size(),"MEDIA_MANIFEST_MISMATCH");
        for(var a:assets){
            String source=a.get("source_kind").toString();check(Set.of("original_tts","original_recording","licensed_audio").contains(source),"INVALID_AUDIO_KIND");
            license(a.get("license_id").toString(),source.equals("licensed_audio")?"licensed":"original","audio");
            JsonNode declared=null;for(var entry:manifest.path("audioAssets"))if(entry.path("id").asText().equals(a.get("id"))) {check(declared==null,"MEDIA_MANIFEST_MISMATCH");declared=entry;}
            check(declared!=null,"MEDIA_MANIFEST_MISMATCH");
            for(var pair:Map.of("id","id","licenseId","license_id","sourceKind","source_kind","storageKey","storage_key","sha256","sha256").entrySet())check(declared.path(pair.getKey()).asText().equals(a.get(pair.getValue())),"MEDIA_MANIFEST_MISMATCH");
            check(declared.path("byteSize").asLong()==((Number)a.get("byte_size")).longValue() && declared.path("durationMs").asInt()==((Number)a.get("duration_ms")).intValue(),"MEDIA_MANIFEST_MISMATCH");
            check("ready".equals(a.get("status")),"MEDIA_UNAVAILABLE");
            for(var s:sentences)if(s.get("audio_asset_id").equals(a.get("id")))check(((Number)s.get("start_ms")).intValue()==0 && ((Number)s.get("end_ms")).intValue()<=((Number)a.get("duration_ms")).intValue(),"INTERVAL_INVALID");
            try{new AudioResources(root).checked(a.get("storage_key").toString(),((Number)a.get("byte_size")).longValue(),a.get("sha256").toString());}catch(Exception e){throw new Rejected("MEDIA_UNAVAILABLE");}
        }
        // Validate existing choice answers, rather than accepting arbitrary JSON plans.
        for(String table:List.of("reading_question","quiz_question"))for(var q:db.queryForList("SELECT payload_json FROM "+table+" WHERE version_id=?",version)){
            var question=json.readTree(q.get("payload_json").toString());var options=new HashSet<String>();
            for(var option:question.path("options"))check(!option.path("text").asText().isBlank() && options.add(option.path("id").asText()),"INVALID_EXERCISE");
            check(options.size()>=2 && options.size()<=8 && options.contains(question.path("answerKey").asText()),"INVALID_EXERCISE");
        }
        check(db.queryForObject("SELECT COUNT(*) FROM quiz_question WHERE version_id=?",Integer.class,version)==0 || db.queryForObject("SELECT COUNT(*) FROM quiz_question WHERE version_id=?",Integer.class,version)==3,"UNSUPPORTED_QUIZ_SIZE");
    }
    /** Freezes a draft only after successful local basic validation. No lifecycle demotion or revalidation overwrite. */
    public String validate(String lesson,String version,String reviewer){
        if(reviewer==null || reviewer.isBlank())return "REVIEWER_REQUIRED";
        try{return tx.execute(status->{
            db.queryForList("SELECT id FROM lesson WHERE id=? FOR UPDATE",lesson);var v=version(lesson,version,true);
            check("draft".equals(v.get("publication_state")),"VERSION_NOT_DRAFT");basic(v);String digest=snapshot(version);
            db.update("INSERT INTO content_validation(version_id,snapshot_sha256,content_sha256,manifest_sha256,algorithm,reviewer) VALUES (?,?,?,?,'northstar.relational.v1',?)",version,digest,v.get("content_sha256"),v.get("manifest_sha256"),reviewer);
            db.update("UPDATE lesson_version SET publication_state='validated' WHERE id=?",version);return "VALIDATED";
        });}catch(Rejected e){return e.code;}
    }
    private Result replay(Request r,String hash){
        var rows=db.queryForList("SELECT request_sha256,response_json FROM publication_audit WHERE operation_id=?",r.operationId());
        if(rows.isEmpty())return null;
        if(!hash.equals(rows.getFirst().get("request_sha256")))return new Result(r.operationId(),"OPERATION_CONFLICT",null);
        return json.readValue(rows.getFirst().get("response_json").toString(),Result.class);
    }
    private void audit(Request r,String hash,Result result){db.update("INSERT INTO publication_audit(operation_id,request_sha256,action,lesson_id,target_version_id,expected_current_id,actual_current_id,content_sha256,result_code,response_json) VALUES (?,?,?,?,?,?,?,?,?,?)",r.operationId(),hash,r.action(),r.lessonId(),r.targetVersionId(),r.expectedCurrentId(),result.currentVersionId(),r.contentSha256(),result.code(),json.writeValueAsString(result));}
    public Result execute(Request r){
        try{check(UUID.fromString(r.operationId()).toString().equals(r.operationId()),"INVALID_OPERATION");
            check(Set.of("publish","withdraw").contains(r.action()) && r.actor()!=null && !r.actor().isBlank() && r.actor().length()<=128,"INVALID_OPERATION");
            for(String id:List.of(r.lessonId(),r.targetVersionId()))check(id.matches("[A-Za-z0-9_-]{1,64}"),"INVALID_ID");
            check(r.expectedCurrentId()==null || r.expectedCurrentId().matches("[A-Za-z0-9_-]{1,64}"),"INVALID_ID");check(r.contentSha256().matches("[a-f0-9]{64}"),"INVALID_HASH");
        }catch(RuntimeException e){return new Result(r.operationId(),"INVALID_REQUEST",null);}
        String hash=hash(json.valueToTree(r));Result old=replay(r,hash);if(old!=null)return old;
        try{return tx.execute(status->{
            // Serializes same-lesson state transitions, including withdrawn versus active learning locks.
            var lessons=db.queryForList("SELECT current_version_id,availability FROM lesson WHERE id=? FOR UPDATE",r.lessonId());
            Result existing=replay(r,hash);if(existing!=null)return existing;
            String current=lessons.isEmpty()?null:Objects.toString(lessons.getFirst().get("current_version_id"),null);
            Result result;
            try {
                check(!lessons.isEmpty(),"LESSON_NOT_FOUND");check(!"withdrawn".equals(lessons.getFirst().get("availability")),"LESSON_WITHDRAWN");check(Objects.equals(current,r.expectedCurrentId()),"CURRENT_VERSION_CONFLICT");
                var v=version(r.lessonId(),r.targetVersionId(),true);check(r.contentSha256().equals(v.get("content_sha256")),"CONTENT_HASH_MISMATCH");
                if(r.action().equals("publish")){
                    check("validated".equals(v.get("publication_state")),"VERSION_NOT_VALIDATED");basic(v);
                    var validation=db.queryForList("SELECT * FROM content_validation WHERE version_id=?",r.targetVersionId());
                    check(validation.size()==1 && snapshot(r.targetVersionId()).equals(validation.getFirst().get("snapshot_sha256")),"CONTENT_SNAPSHOT_CHANGED");
                    // All rejection checks precede mutation. Unexpected failures roll back the whole transaction.
                    db.update("UPDATE lesson_version SET publication_state='published',published_at=UTC_TIMESTAMP(3) WHERE id=?",r.targetVersionId());
                    check(db.update("UPDATE lesson SET current_version_id=?,availability='available' WHERE id=? AND current_version_id <=> ?",r.targetVersionId(),r.lessonId(),r.expectedCurrentId())==1,"CAS_INTERNAL_FAILURE");
                    result=new Result(r.operationId(),"PUBLISHED",r.targetVersionId());
                }else{
                    check("published".equals(v.get("publication_state")),"VERSION_NOT_PUBLISHED");
                    if(Objects.equals(current,r.targetVersionId()))db.update("UPDATE lesson SET current_version_id=NULL WHERE id=? AND current_version_id <=> ?",r.lessonId(),current);
                    db.update("UPDATE lesson_version SET publication_state='withdrawn' WHERE id=?",r.targetVersionId());
                    result=new Result(r.operationId(),"WITHDRAWN",Objects.equals(current,r.targetVersionId())?null:current);
                }
            }catch(Rejected e){if(e.code.equals("CAS_INTERNAL_FAILURE"))throw e;result=new Result(r.operationId(),e.code,current);}
            audit(r,hash,result);return result;
        });}catch(DuplicateKeyException e){var result=replay(r,hash);if(result!=null)return result;throw e;}
        catch(RuntimeException e){
            // Business transaction is already rolled back. Do not turn an unavailable DB into a fictitious audit success.
            return tx.execute(status->{
                var prior=replay(r,hash);if(prior!=null)return prior;
                var pointers=db.queryForList("SELECT current_version_id,availability FROM lesson WHERE id=? FOR UPDATE",r.lessonId());
                String actual=pointers.isEmpty()?null:Objects.toString(pointers.getFirst().get("current_version_id"),null);
                var failed=new Result(r.operationId(),"PUBLICATION_ROLLED_BACK",actual);audit(r,hash,failed);return failed;
            });
        }
    }
}
