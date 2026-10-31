package local.northstar.exercise;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.json.JsonMapper;

/** Frozen content projection; creation is only called by explicit content initialization/validation. */
public final class QuizSets {
    private QuizSets() {}
    public static String sha(String text) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8))); }
        catch(java.security.NoSuchAlgorithmException error) { throw new IllegalStateException(error); }
    }
    private static String hex(Object text) { return HexFormat.of().withUpperCase().formatHex(text.toString().getBytes(StandardCharsets.UTF_8)); }
    public static String itemHash(Map<String,Object> row) {
        return sha(hex(row.get("exercise_id"))+":"+row.get("ordinal")+":"+hex(row.get("sentence_id"))+":"+hex(row.get("knowledge_point_id"))+":"+hex(row.get("question_text")));
    }
    public static String setHash(String version,Object context,List<Map<String,Object>> items) {
        return sha("quiz-set-v1:"+hex(version)+":practice:quiz_choice_v1:"+(context==null?"":hex(context))+":"+items.stream().map(QuizSets::itemHash).collect(java.util.stream.Collectors.joining()));
    }
    public static List<Map<String,Object>> items(JdbcOperations db,String set) {
        return db.queryForList("SELECT i.*,CAST(i.question_json AS CHAR CHARACTER SET utf8mb4) AS question_text,s.sequence_no AS sequence FROM exercise_set_item i JOIN sentence s ON s.id=i.sentence_id WHERE set_id=? ORDER BY ordinal",set);
    }
    public static Map<String,Object> load(JdbcOperations db,String version,String id) {
        var rows=id==null?db.queryForList("SELECT * FROM exercise_set WHERE version_id=? AND purpose='practice'",version):db.queryForList("SELECT * FROM exercise_set WHERE id=? AND version_id=?",id,version);
        if(rows.isEmpty())throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"此版本没有对应测验题集。");
        var set=rows.getFirst();var items=items(db,set.get("id").toString());validate(set,items);set.put("items",items);return set;
    }
    public static void validate(Map<String,Object> set,List<Map<String,Object>> items) {
        if(!Boolean.TRUE.equals(set.get("frozen")) || items.isEmpty() || items.size()>100)throw new IllegalStateException("Quiz set is not frozen or has invalid size");
        var mapper=JsonMapper.builder().build();int ordinal=0;
        for(var row:items) {
            if(((Number)row.get("ordinal")).intValue()!=++ordinal || !itemHash(row).equals(row.get("item_hash")))throw new IllegalStateException("Quiz item snapshot changed");
            var q=mapper.readTree(row.get("question_text").toString());var options=new HashSet<String>();
            for(var option:q.path("options"))if(!options.add(option.path("id").asText()) || option.path("id").asText().isBlank())throw new IllegalStateException("Quiz option identity invalid");
            if(!q.path("id").asText().equals(row.get("exercise_id")) || q.path("prompt").asText().isBlank() || options.size()<2 || !options.contains(q.path("answerKey").asText()))throw new IllegalStateException("Quiz question invalid");
        }
        if(!setHash(set.get("version_id").toString(),set.get("context_group_id"),items).equals(set.get("set_hash")))throw new IllegalStateException("Quiz set hash changed");
    }
    public static void freezeDefault(JdbcOperations db,String version) {
        if(db.queryForObject("SELECT COUNT(*) FROM exercise_set WHERE version_id=?",Integer.class,version)>0) { load(db,version,null);return; }
        var questions=db.queryForList("SELECT q.*,CAST(q.payload_json AS CHAR CHARACTER SET utf8mb4) AS question_text FROM quiz_question q WHERE version_id=? ORDER BY exercise_id",version);
        if(questions.isEmpty())return;
        if(questions.size()>100)throw new IllegalStateException("Quiz supports at most 100 questions");
        String id=UUID.randomUUID().toString();
        db.update("INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES (?,?,'practice','quiz_choice_v1','version_content')",id,version);
        int ordinal=0;
        for(var row:questions) {
            row.put("ordinal",++ordinal);
            db.update("INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) VALUES (?,?,?,?,?,?,?,?)",id,row.get("exercise_id"),version,row.get("sentence_id"),row.get("knowledge_point_id"),ordinal,row.get("question_text"),itemHash(row));
        }
        var items=items(db,id);
        db.update("UPDATE exercise_set SET set_hash=?,frozen=TRUE WHERE id=?",setHash(version,null,items),id);
        load(db,version,id);
    }
}
