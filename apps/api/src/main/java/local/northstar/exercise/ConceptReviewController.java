package local.northstar.exercise;

import java.sql.Timestamp;
import java.time.*;
import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Cross-lesson concept review cards; visibility mirrors KnowledgeController so withdrawn lessons never leak content. */
@RestController
public class ConceptReviewController {
    private static final String VISIBLE="l.availability='available' AND v.publication_state='published' AND (l.id='demo-01' OR lc.review_status='confirmed')";
    private static final String LATEST_REVISION="JOIN knowledge_concept_revision rev ON rev.concept_id=c.id AND rev.review_status='confirmed'"
        +" AND rev.revision_no=(SELECT MAX(x.revision_no) FROM knowledge_concept_revision x WHERE x.concept_id=c.id AND x.review_status='confirmed')";
    private final JdbcOperations jdbc;
    private final ExerciseController commands;
    private final JsonMapper mapper=JsonMapper.builder().build();
    private final Clock clock=Clock.systemUTC();
    public ConceptReviewController(JdbcOperations jdbc,ExerciseController commands) {this.jdbc=jdbc;this.commands=commands;}
    private int limit(String value) {
        if(value==null) return 20;
        if(!value.matches("[0-9]{1,3}")) throw invalid("分页大小无效。");
        int parsed=Integer.parseInt(value);
        if(parsed<1 || parsed>100) throw invalid("分页大小必须在1到100之间。");
        return parsed;
    }
    private String cursor(String value) {
        if(value==null || value.isEmpty()) return null;
        if(!value.matches("[0-9a-fA-F-]{36}:[A-Za-z0-9_-]{1,36}")) throw invalid("分页游标无效。");
        return value;
    }
    private String[] cardCursor(String value) {
        if(value==null || value.isEmpty()) return null;
        if(!value.matches("[0-9]+:[0-9a-fA-F-]{36}")) throw invalid("分页游标无效。");
        int split=value.indexOf(':');
        return new String[]{value.substring(0,split),value.substring(split+1)};
    }
    private String cardCursorKey(Object dueAt,Object id) {
        long millis=dueAt instanceof Timestamp t ? t.getTime() : ((LocalDateTime)dueAt).toInstant(ZoneOffset.UTC).toEpochMilli();
        return millis+":"+id;
    }
    private ResponseStatusException notFound() {return new ResponseStatusException(HttpStatus.NOT_FOUND,"复习卡不存在。");}
    private ResponseStatusException conflict(String text) {return new ResponseStatusException(HttpStatus.CONFLICT,text);}
    private ResponseStatusException invalid(String text) {return new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,text);}
    private void time(String value) {try {Instant.parse(value);}catch(Exception error){throw invalid("客户端时间必须包含时区。");}}
    @GetMapping("/api/v1/concept-reviews/due")
    public Object due(@RequestParam(defaultValue="false") boolean all,@RequestParam(required=false) String cursor,@RequestParam(required=false) String limit) {
        int size=limit(limit);String[] after=cardCursor(cursor);
        var args=new ArrayList<Object>();
        String filter="";
        if(!all) {filter+=" AND r.due_at<=UTC_TIMESTAMP(3)";}
        if(after!=null) {filter+=" AND (r.due_at>FROM_UNIXTIME(?/1000) OR (r.due_at=FROM_UNIXTIME(?/1000) AND r.id>?))";args.add(Long.parseLong(after[0]));args.add(Long.parseLong(after[0]));args.add(after[1]);}
        var rows=jdbc.queryForList("SELECT r.id,(r.due_at<=UTC_TIMESTAMP(3)) AS due,r.due_at AS dueAt,r.reps,r.row_version AS rowVersion,"
            +"r.prompt_kind AS promptKind,r.protocol_version AS protocolVersion,r.scheduler_version AS schedulerVersion,"
            +"c.id AS conceptId,c.kind,c.canonical_key AS canonicalKey,c.sense_key AS senseKey,rev.display_name AS displayName,rev.explanation "
            +"FROM concept_review_card r JOIN knowledge_concept c ON c.id=r.concept_id "+LATEST_REVISION+" "
            +"WHERE r.status='pending' AND r.owner_key='local'"+filter+" ORDER BY r.due_at,r.id LIMIT ?",append(args,size));
        for(var row:rows) row.put("visibleSourceCount",visibleSourceCount(row.get("id").toString()));
        var result=new LinkedHashMap<String,Object>();
        result.put("items",rows);
        result.put("nextCursor",rows.size()==size?cardCursorKey(rows.getLast().get("dueAt"),rows.getLast().get("id")):null);
        return result;
    }
    private int visibleSourceCount(String cardId) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM concept_review_source s "
            +"JOIN exercise_attempt a ON a.id=s.attempt_id JOIN lesson l ON l.id=a.lesson_id "
            +"JOIN lesson_version v ON v.id=a.version_id AND v.lesson_id=l.id JOIN content_license lc ON lc.id=v.license_id "
            +"WHERE s.card_id=? AND "+VISIBLE,Integer.class,cardId);
    }
    @GetMapping("/api/v1/concept-reviews/{id}")
    public Object card(@PathVariable String id) {
        var rows=cardRows(id);
        if(rows.isEmpty()) throw notFound();
        var result=new LinkedHashMap<>(rows.getFirst());
        result.put("visibleSourceCount",visibleSourceCount(id));
        return result;
    }
    private List<Map<String,Object>> cardRows(String id) {
        return jdbc.queryForList("SELECT r.id,(r.due_at<=UTC_TIMESTAMP(3)) AS due,r.due_at AS dueAt,r.reps,r.row_version AS rowVersion,"
            +"r.prompt_kind AS promptKind,r.protocol_version AS protocolVersion,r.scheduler_version AS schedulerVersion,r.created_at AS createdAt,"
            +"c.id AS conceptId,c.kind,c.canonical_key AS canonicalKey,c.sense_key AS senseKey,rev.display_name AS displayName,rev.explanation "
            +"FROM concept_review_card r JOIN knowledge_concept c ON c.id=r.concept_id "+LATEST_REVISION+" "
            +"WHERE r.id=? AND r.owner_key='local'",id);
    }
    @GetMapping("/api/v1/concept-reviews/{id}/sources")
    public Object sources(@PathVariable String id,@RequestParam(required=false) String cursor,@RequestParam(required=false) String limit) {
        if(cardRows(id).isEmpty()) throw notFound();
        int size=limit(limit);String after=cursor(cursor);
        var args=new ArrayList<Object>();args.add(id);
        String filter="";
        if(after!=null) {
            int split=after.indexOf(':');
            filter+=" AND (s.attempt_id>? OR (s.attempt_id=? AND s.occurrence_id>?))";
            args.add(after.substring(0,split));args.add(after.substring(0,split));args.add(after.substring(split+1));
        }
        var rows=jdbc.queryForList("SELECT CONCAT(s.attempt_id,':',s.occurrence_id) AS cursorKey,s.attempt_id AS attemptId,s.occurrence_id AS occurrenceId,"
            +"a.lesson_id AS lessonId,a.version_id AS versionId,e.kind AS exerciseKind,a.correct AS correct,a.recorded_at AS recordedAt,"
            +"("+VISIBLE+") AS visible,"
            +"CASE WHEN "+VISIBLE+" THEN v.payload_json->>'$.title' END AS lessonTitle,"
            +"CASE WHEN "+VISIBLE+" THEN o.scope END AS scope,"
            +"CASE WHEN "+VISIBLE+" AND o.scope='sentence' THEN os.sequence_no END AS sequence,"
            +"CASE WHEN "+VISIBLE+" AND o.scope='sentence' THEN os.text END AS sentenceText "
            +"FROM concept_review_source s "
            +"JOIN attempt_knowledge ak ON ak.attempt_id=s.attempt_id AND ak.occurrence_id=s.occurrence_id AND ak.exercise_id=s.exercise_id AND ak.version_id=s.version_id AND ak.concept_id=s.concept_id "
            +"JOIN exercise_attempt a ON a.id=s.attempt_id JOIN exercise e ON e.id=s.exercise_id AND e.version_id=s.version_id "
            +"JOIN knowledge_occurrence o ON o.id=s.occurrence_id "
            +"JOIN lesson l ON l.id=a.lesson_id JOIN lesson_version v ON v.id=a.version_id AND v.lesson_id=l.id JOIN content_license lc ON lc.id=v.license_id "
            +"LEFT JOIN sentence os ON os.id=o.sentence_id AND os.lesson_version_id=o.version_id "
            +"WHERE s.card_id=?"+filter+" ORDER BY s.attempt_id,s.occurrence_id LIMIT ?",append(args,size));
        // Restricted rows lose their internal cursor key during response-field pruning.
        String nextCursor=rows.size()==size?rows.getLast().get("cursorKey").toString():null;
        var items=new ArrayList<Map<String,Object>>();
        for(var row:rows) {
            Object visibleValue=row.remove("visible");
            boolean visible=Boolean.TRUE.equals(visibleValue)||visibleValue instanceof Number flags&&flags.intValue()!=0;
            row.put("visible",visible);
            if(!visible) {
                row.keySet().retainAll(List.of("attemptId","occurrenceId","lessonId","versionId","recordedAt","visible"));
                row.put("restricted",true);
            } else row.put("restricted",false);
            items.add(row);
        }
        var result=new LinkedHashMap<String,Object>();
        result.put("items",items);
        result.put("nextCursor",nextCursor);
        return result;
    }
    @PostMapping("/api/v1/concept-reviews/{id}/results")
    public JsonNode rate(@PathVariable String id,@Valid @RequestBody ConceptRating value) {
        return commands.command(value.eventId,"concept-review-rating:"+id,value,()->{
            time(value.clientOccurredAt);
            if(!value.answerRevealed || !Set.of("again","good").contains(value.rating)) throw invalid("请先翻卡，再选择真实的人工自评。");
            var rows=jdbc.queryForList("SELECT * FROM concept_review_card WHERE id=? AND owner_key='local' FOR UPDATE",id);
            if(rows.isEmpty()) throw notFound();
            var row=rows.getFirst();
            if(!"pending".equals(row.get("status").toString())) throw conflict("此卡当前不可复习。");
            if(((Number)row.get("row_version")).longValue()!=value.rowVersion) throw conflict("此卡已被另一页面更新，请重新读取；原操作未计数。");
            Instant now=clock.instant(),due=row.get("due_at") instanceof Timestamp t ? t.toInstant() : ((LocalDateTime)row.get("due_at")).toInstant(ZoneOffset.UTC);
            if(due.isAfter(now)) throw conflict("此卡尚未到期，请到期后再复习。");
            int reps=((Number)row.get("reps")).intValue();Instant next=SimpleScheduler.next(clock,value.rating,reps);
            jdbc.update("INSERT INTO concept_review_result(event_id,card_id,rating,previous_due_at,next_due_at,previous_row_version,client_occurred_at) VALUES (?,?,?,?,?,?,?)",
                    value.eventId,id,value.rating,Timestamp.from(due),Timestamp.from(next),value.rowVersion,value.clientOccurredAt);
            if(jdbc.update("UPDATE concept_review_card SET due_at=?,reps=?,row_version=row_version+1,updated_at=UTC_TIMESTAMP(3) WHERE id=? AND row_version=?",
                    Timestamp.from(next),value.rating.equals("good")?reps+1:0,id,value.rowVersion)!=1) throw conflict("此卡已被另一页面更新，请重新读取；原操作未计数。");
            return mapper.valueToTree(Map.of("eventId",value.eventId,"nextDueAt",next.toString(),"rowVersion",value.rowVersion+1,"origin","self_rating","schedulerVersion","simple_v1"));
        });
    }
    @GetMapping("/api/v1/concept-reviews/{id}/results")
    public Object history(@PathVariable String id) {
        if(cardRows(id).isEmpty()) throw notFound();
        return jdbc.queryForList("SELECT event_id AS eventId,rating,origin,next_due_at AS nextDueAt,previous_due_at AS previousDueAt,"
            +"previous_row_version AS previousRowVersion,recorded_at AS recordedAt FROM concept_review_result WHERE card_id=? ORDER BY recorded_at DESC,event_id",id);
    }
    private Object[] append(List<Object> args,Object extra) {args.add(extra);return args.toArray();}
    @ExceptionHandler(ExerciseController.Failure.class)
    public ProblemDetail failure(ExerciseController.Failure error,HttpServletRequest request) {return local.northstar.common.ApiProblems.problem(HttpStatus.valueOf(error.status),error.code,error.getMessage(),request.getRequestURI());}
    public record ConceptRating(@NotBlank String eventId,@Min(1) long rowVersion,@NotBlank String rating,boolean answerRevealed,@NotBlank @Size(max=40) String clientOccurredAt) {}
}
