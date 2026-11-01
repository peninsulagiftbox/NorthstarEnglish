package local.northstar.knowledge;

import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import local.northstar.common.ApiProblems;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Read-only cross-lesson browsing; visibility mirrors the catalog read rules. */
@RestController
public class KnowledgeController {
    private static final String VISIBLE="l.availability='available' AND v.publication_state='published' AND (l.id='demo-01' OR lc.review_status='confirmed')";
    private final JdbcOperations db;
    private final JsonMapper mapper=JsonMapper.builder().build();
    public KnowledgeController(JdbcOperations db) {this.db=db;}
    private static final String LATEST_REVISION=" JOIN knowledge_concept_revision r ON r.concept_id=c.id AND r.review_status='confirmed'"
        +" AND r.revision_no=(SELECT MAX(x.revision_no) FROM knowledge_concept_revision x WHERE x.concept_id=c.id AND x.review_status='confirmed') ";
    // Occurrences from every confirmed revision stay browsable; row-level visibility keeps withdrawn lessons out of aggregates.
    private static final String CONFIRMED_OCCURRENCES=" JOIN knowledge_occurrence o ON o.concept_id=c.id "
        +"JOIN knowledge_concept_revision occRev ON occRev.id=o.revision_id AND occRev.review_status='confirmed' "
        +"JOIN lesson l ON l.id=o.lesson_id "
        +"JOIN lesson_version v ON v.id=o.version_id AND v.lesson_id=l.id "
        +"JOIN content_license lc ON lc.id=v.license_id ";
    private int limit(String value) {
        if(value==null) return 20;
        if(!value.matches("[0-9]{1,3}")) throw new Failure(422,"INVALID_LIMIT","分页大小无效。");
        int parsed=Integer.parseInt(value);
        if(parsed<1 || parsed>100) throw new Failure(422,"INVALID_LIMIT","分页大小必须在1到100之间。");
        return parsed;
    }
    private String cursor(String value) {
        if(value==null || value.isEmpty()) return null;
        if(!value.matches("[A-Za-z0-9_-]{1,64}")) throw new Failure(422,"INVALID_CURSOR","分页游标无效。");
        return value;
    }
    @GetMapping("/api/v1/knowledge/concepts")
    public Object concepts(@RequestParam(required=false) String lessonId,@RequestParam(required=false) String versionId,
            @RequestParam(required=false) String cursor,@RequestParam(required=false) String limit) {
        int size=limit(limit);String after=cursor(cursor);
        if(versionId!=null && !versionId.matches("[A-Za-z0-9_-]{1,64}")) throw notFound();
        if(lessonId!=null && !lessonId.matches("[A-Za-z0-9_-]{1,64}")) throw notFound();
        var args=new ArrayList<Object>();
        String filter="";
        if(after!=null) {filter+=" AND c.id>?";args.add(after);}
        if(versionId!=null) {filter+=" AND o.version_id=?";args.add(versionId);}
        if(lessonId!=null) {filter+=" AND o.lesson_id=?";args.add(lessonId);}
        var rows=db.queryForList("SELECT c.id,c.kind,c.canonical_key AS canonicalKey,c.sense_key AS senseKey,r.display_name AS displayName,"
            +"COUNT(DISTINCT o.lesson_id) AS lessonCount,MIN(o.id) AS firstOccurrenceId "
            +"FROM knowledge_concept c "+LATEST_REVISION+CONFIRMED_OCCURRENCES
            +"WHERE "+VISIBLE+filter
            +" GROUP BY c.id,c.kind,c.canonical_key,c.sense_key,r.display_name ORDER BY c.id LIMIT ?",append(args,size));
        var items=new ArrayList<Map<String,Object>>();
        for(var row:rows) items.add(row);
        String next=rows.size()==size?rows.getLast().get("id").toString():null;
        var result=new LinkedHashMap<String,Object>();
        result.put("items",items);result.put("nextCursor",next);
        return result;
    }
    @GetMapping("/api/v1/knowledge/concepts/{id}")
    public Object concept(@PathVariable String id) {
        if(!id.matches("[A-Za-z0-9_-]{1,64}")) throw notFound();
        var rows=db.queryForList("""
            SELECT c.id,c.kind,c.canonical_key AS canonicalKey,c.sense_key AS senseKey,
                   r.id AS revisionId,r.revision_no AS revisionNo,r.display_name AS displayName,r.explanation,
                   r.reviewer,r.reviewed_at AS reviewedAt
            FROM knowledge_concept c
            """+LATEST_REVISION+"WHERE c.id=?",id);
        if(rows.isEmpty()) throw notFound();
        var result=new LinkedHashMap<>(rows.getFirst());
        result.put("lessons",db.queryForList("""
            SELECT o.lesson_id AS lessonId,MAX(v.payload_json->>'$.title') AS title,
                   GROUP_CONCAT(DISTINCT o.version_id ORDER BY o.version_id SEPARATOR ',') AS versionIds,
                   COUNT(*) AS occurrenceCount
            FROM knowledge_occurrence o
            JOIN knowledge_concept_revision occRev ON occRev.id=o.revision_id AND occRev.review_status='confirmed'
            JOIN lesson_version v ON v.id=o.version_id JOIN lesson l ON l.id=o.lesson_id
            JOIN content_license lc ON lc.id=v.license_id
            """+"WHERE o.concept_id=? AND "+VISIBLE+" GROUP BY o.lesson_id ORDER BY o.lesson_id",id));
        result.remove("revisionId");
        return result;
    }
    @GetMapping("/api/v1/knowledge/concepts/{id}/occurrences")
    public Object occurrences(@PathVariable String id,@RequestParam(required=false) String lessonId,
            @RequestParam(required=false) String versionId,@RequestParam(required=false) String cursor,@RequestParam(required=false) String limit) {
        if(!id.matches("[A-Za-z0-9_-]{1,64}")) throw notFound();
        if(db.queryForList("SELECT id FROM knowledge_concept WHERE id=?",id).isEmpty()) throw notFound();
        int size=limit(limit);String after=cursor(cursor);
        if(versionId!=null && !versionId.matches("[A-Za-z0-9_-]{1,64}")) throw notFound();
        if(lessonId!=null && !lessonId.matches("[A-Za-z0-9_-]{1,64}")) throw notFound();
        var args=new ArrayList<Object>();args.add(id);
        String filter="";
        if(after!=null) {filter+=" AND o.id>?";args.add(after);}
        if(versionId!=null) {filter+=" AND o.version_id=?";args.add(versionId);}
        if(lessonId!=null) {filter+=" AND o.lesson_id=?";args.add(lessonId);}
        String when="("+VISIBLE+")";
        String query="SELECT o.id,o.scope,o.version_id AS versionId,o.lesson_id AS lessonId,"
                +when+" AS visible,"
                +"CASE WHEN "+when+" THEN v.payload_json->>'$.title' END AS title,"
                +"o.scope='sentence' AS sentenceScope,"
                +"CASE WHEN "+when+" AND o.scope='sentence' THEN s.sequence_no END AS sequence,"
                +"CASE WHEN "+when+" AND o.scope='sentence' THEN s.text END AS sentenceText,"
                +"CASE WHEN "+when+" THEN CAST(o.usage_json AS CHAR CHARACTER SET utf8mb4) END AS usageJson,"
                +"CASE WHEN "+when+" THEN (SELECT COUNT(*) FROM exercise_knowledge ek WHERE ek.occurrence_id=o.id) END AS exerciseCount,"
                +"CASE WHEN "+when+" THEN (SELECT COUNT(*) FROM attempt_knowledge ak JOIN exercise_attempt a ON a.id=ak.attempt_id WHERE ak.occurrence_id=o.id AND a.correct=FALSE) END AS wrongAttemptCount,"
                +"CASE WHEN "+when+" THEN o.created_at END AS createdAt "
                +"FROM knowledge_occurrence o "
                +"JOIN lesson_version v ON v.id=o.version_id JOIN lesson l ON l.id=o.lesson_id "
                +"JOIN content_license lc ON lc.id=v.license_id "
                +"LEFT JOIN sentence s ON s.id=o.sentence_id "
                +"WHERE o.concept_id=?"+filter+" ORDER BY o.id LIMIT ?";
        var rows=db.queryForList(query,append(args,size));
        var items=new ArrayList<Map<String,Object>>();
        for(var row:rows) {
            Object visibleValue=row.get("visible");
            boolean visible=Boolean.TRUE.equals(visibleValue)||visibleValue instanceof Number flags&&flags.intValue()!=0;
            row.put("visible",visible);
            if(!visible) {
                row.keySet().retainAll(List.of("id","scope","versionId","lessonId","visible"));
                row.put("restricted",true);
            } else {
                Object scopeValue=row.remove("sentenceScope");
                boolean sentenceScope=Boolean.TRUE.equals(scopeValue)||scopeValue instanceof Number count&&count.intValue()!=0;
                row.put("restricted",false);
                Object rawUsage=row.remove("usageJson");
                try {row.put("usage",rawUsage==null?null:mapper.readTree(rawUsage.toString()));}
                catch(Exception error) {row.put("usage",null);}
                if(!sentenceScope) {row.remove("sentenceText");row.remove("sequence");}
            }
            items.add(row);
        }
        String next=rows.size()==size?rows.getLast().get("id").toString():null;
        var result=new LinkedHashMap<String,Object>();
        result.put("items",items);result.put("nextCursor",next);
        return result;
    }
    private Object[] append(List<Object> args,Object extra) {args.add(extra);return args.toArray();}
    private ResponseStatusException notFound() {return new ResponseStatusException(HttpStatus.NOT_FOUND,"知识概念不存在。");}
    @ExceptionHandler(Failure.class)
    public ProblemDetail failure(Failure error,HttpServletRequest request) {return ApiProblems.problem(HttpStatus.valueOf(error.status),error.code,error.getMessage(),request.getRequestURI());}
    public static class Failure extends RuntimeException {
        final int status;final String code;
        Failure(int status,String code,String message) {super(message);this.status=status;this.code=code;}
    }
}
