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
    /** Uses the fixed quiz_run alias r in history, detail and aggregate queries. */
    public static String verifiedRunClause() {
        return """
            r.total_count BETWEEN 1 AND 100 AND r.submitted_count=r.total_count
            AND EXISTS (SELECT 1 FROM exercise_set qs JOIN lesson_version v ON v.id=qs.version_id
                WHERE qs.id=r.set_id AND qs.version_id=r.version_id AND v.lesson_id=r.lesson_id
                AND qs.frozen=TRUE AND qs.set_hash=r.set_hash)
            AND (SELECT COUNT(*) FROM exercise_set_item si WHERE si.set_id=r.set_id)=r.total_count
            AND (SELECT COUNT(*) FROM quiz_run_item i WHERE i.run_id=r.id)=r.total_count
            AND (SELECT COUNT(*) FROM quiz_answer b WHERE b.run_id=r.id)=r.total_count
            AND (SELECT COUNT(DISTINCT a.id) FROM quiz_run_item i
                JOIN quiz_answer b ON b.run_id=i.run_id AND b.exercise_id=i.exercise_id
                    AND b.attempt_id=i.attempt_id AND b.version_id=i.version_id
                    AND b.sentence_id=i.sentence_id AND b.option_id=i.option_id
                JOIN exercise_attempt a ON a.id=i.attempt_id AND a.exercise_id=i.exercise_id
                    AND a.version_id=i.version_id AND a.sentence_id=i.sentence_id
                JOIN exercise_set_item si ON si.set_id=i.set_id AND si.exercise_id=i.exercise_id
                    AND si.version_id=i.version_id AND si.sentence_id=i.sentence_id
                WHERE i.run_id=r.id AND i.set_id=r.set_id AND i.set_hash=r.set_hash
                    AND i.version_id=r.version_id AND a.lesson_id=r.lesson_id
                    AND i.ordinal=si.ordinal AND i.question_json=si.question_json
                    AND JSON_CONTAINS(JSON_EXTRACT(i.question_json,'$.options'),JSON_OBJECT('id',i.option_id))
                    AND a.correct=(i.option_id=JSON_UNQUOTE(JSON_EXTRACT(i.question_json,'$.answerKey'))))=r.total_count
            AND r.correct_count=(SELECT COALESCE(SUM(a.correct),0) FROM quiz_run_item i
                JOIN exercise_attempt a ON a.id=i.attempt_id WHERE i.run_id=r.id)
            """;
    }
    public static boolean verifiedRun(JdbcOperations db,Object run) {
        return db.queryForObject("SELECT COUNT(*) FROM quiz_run r WHERE r.id=? AND "+verifiedRunClause(),Integer.class,run)==1;
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
