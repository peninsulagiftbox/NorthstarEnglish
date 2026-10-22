package local.northstar.exercise;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import local.northstar.catalog.ContentPackage;
import local.northstar.common.ApiProblems;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.bind.annotation.*;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@RestController
public class ExerciseController {
    private final JdbcOperations jdbc;
    private final TransactionTemplate tx;
    private final ContentPackage content;
    private final JsonMapper mapper = JsonMapper.builder().build();
    public ExerciseController(JdbcOperations jdbc, PlatformTransactionManager manager, ContentPackage content) {
        this.jdbc=jdbc; this.tx=new TransactionTemplate(manager); this.content=content;
    }
    @PostMapping("/api/v1/exercises/{id}/attempts")
    public JsonNode attempt(@PathVariable String id,@Valid @RequestBody Attempt value) {
        return command(value.eventId, "attempt:"+id, value, () -> {
            timestamp(value.clientOccurredAt);
            var target=target(value.lessonId,value.versionId,value.sentenceId);
            if(!id.equals(value.sentenceId+"-dictation")) throw failure(422,"CONTEXT_MISMATCH","听写题目与目标句不匹配。");
            if(value.text.isBlank() || TokenAligner.tokens(value.text).isEmpty()) throw failure(422,"EMPTY_ANSWER","请输入非空英文听写。");
            if(!value.audioPlayed) throw failure(422,"AUDIO_NOT_PLAYED","请先播放本句音频，再正式提交。");
            try { content.checkedAudio(target.get("storage_key").toString(),((Number)target.get("byte_size")).longValue(),target.get("sha256").toString()); }
            catch(Exception error) { throw failure(503,"AUDIO_UNAVAILABLE","本句音源缺失或损坏，草稿保留；恢复音源后重试。"); }
            if(!"ready".equals(target.get("status"))) throw failure(503,"AUDIO_UNAVAILABLE","本句音频不可用。");
            var result=TokenAligner.align(target.get("text").toString(),value.text);
            String attemptId=UUID.randomUUID().toString(), evidenceId=UUID.randomUUID().toString();
            var response=mapper.valueToTree(Map.of("attemptId",attemptId,"eventId",value.eventId,"evidenceId",evidenceId,
                    "state","practiced","rawText",value.text,"standardText",target.get("text"),"result",result,
                    "answerExposed",value.answerExposed,"reviewItemId",result.correct()?"":value.sentenceId+"-review"));
            jdbc.update("INSERT INTO exercise_attempt(id,event_id,lesson_id,version_id,sentence_id,exercise_id,raw_text,correct,answer_exposed,algorithm_version,result_json,client_occurred_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    attemptId,value.eventId,value.lessonId,value.versionId,value.sentenceId,id,value.text,result.correct(),value.answerExposed,result.algorithmVersion(),mapper.writeValueAsString(result),value.clientOccurredAt);
            jdbc.update("INSERT INTO learning_evidence(id,attempt_id,event_id) VALUES (?,?,?)",evidenceId,attemptId,value.eventId);
            stage(value.sentenceId,value.versionId,"practiced",1);
            if(!result.correct()) {
                String itemId=value.sentenceId+"-review";
                jdbc.update("INSERT INTO review_item(id,sentence_id,version_id) VALUES (?,?,?) ON DUPLICATE KEY UPDATE id=id",itemId,value.sentenceId,value.versionId);
                jdbc.update("INSERT INTO review_source(attempt_id,item_id,reason,sentence_id,version_id) VALUES (?,?,'dictation_token_difference',?,?)",attemptId,itemId,value.sentenceId,value.versionId);
            }
            return response;
        });
    }
    @PostMapping("/api/v1/study/events")
    public JsonNode event(@Valid @RequestBody Event value) {
        return command(value.eventId,"study-event",value,() -> {
            timestamp(value.clientOccurredAt);
            target(value.lessonId,value.versionId,value.sentenceId);
            String state=switch(value.action) {case "start" -> "in_progress";case "skip" -> "skipped";case "pause" -> "paused";default -> throw failure(422,"INVALID_ACTION","只支持开始、跳过或暂停；不能直接上报练习完成。");};
            jdbc.update("INSERT INTO study_event(event_id,lesson_id,version_id,sentence_id,action,client_occurred_at) VALUES (?,?,?,?,?,?)",value.eventId,value.lessonId,value.versionId,value.sentenceId,value.action,value.clientOccurredAt);
            stage(value.sentenceId,value.versionId,state,0);
            return mapper.valueToTree(Map.of("eventId",value.eventId,"state",state));
        });
    }
    private void stage(String sentence,String version,String state,int increment) {
        jdbc.update("INSERT INTO study_stage(sentence_id,version_id,current_state,practice_count) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE current_state=?,practice_count=practice_count+?",sentence,version,state,increment,state,increment);
    }
    @GetMapping("/api/v1/study/stages")
    public Object stages(@RequestParam String lessonId,@RequestParam String versionId) {
        return jdbc.queryForList("SELECT s.id AS sentenceId,COALESCE(t.current_state,'not_started') AS state,COALESCE(t.practice_count,0) AS practiceCount FROM sentence s LEFT JOIN study_stage t ON t.sentence_id=s.id WHERE s.lesson_id=? AND s.lesson_version_id=? ORDER BY s.sequence_no",lessonId,versionId);
    }
    @GetMapping("/api/v1/reviews/items")
    public Object reviews() {
        return jdbc.queryForList("SELECT r.id,r.status,a.id AS attemptId,a.lesson_id AS lessonId,a.version_id AS versionId,a.sentence_id AS sentenceId,a.exercise_id AS exerciseId,a.raw_text AS rawText,s.sequence_no AS sequence,s.text AS standardText,rs.reason,a.recorded_at AS recordedAt FROM review_item r JOIN review_source rs ON rs.item_id=r.id JOIN exercise_attempt a ON a.id=rs.attempt_id JOIN sentence s ON s.id=a.sentence_id ORDER BY a.recorded_at DESC,a.id");
    }
    @GetMapping("/api/v1/drafts/{sentence}")
    public Object draft(@PathVariable String sentence,@RequestParam String lessonId,@RequestParam String versionId) {
        target(lessonId,versionId,sentence);
        var rows=jdbc.queryForList("SELECT raw_text AS text,row_version AS rowVersion FROM exercise_draft WHERE sentence_id=? AND lesson_id=? AND version_id=?",sentence,lessonId,versionId);
        return rows.isEmpty()?Map.of("text","","rowVersion",0):rows.getFirst();
    }
    @PutMapping("/api/v1/drafts/{sentence}")
    public Object saveDraft(@PathVariable String sentence,@Valid @RequestBody Draft value,@RequestHeader(value="If-Match",required=false) String match) {
        target(value.lessonId,value.versionId,sentence);
        if(match==null) throw failure(428,"REVISION_REQUIRED","保存草稿需要版本号。");
        if(!match.matches("\"[0-9]{1,16}\"")) throw failure(400,"INVALID_REVISION","版本号格式不正确。");
        long revision=Long.parseLong(match.substring(1,match.length()-1));
        if(revision==0) {
            try {jdbc.update("INSERT INTO exercise_draft(sentence_id,lesson_id,version_id,raw_text) VALUES (?,?,?,?)",sentence,value.lessonId,value.versionId,value.text);}
            catch(DuplicateKeyException error) {throw failure(412,"DRAFT_VERSION_CONFLICT","另一页面已保存此句草稿；保留本机文本，请比较两份草稿。");}
        } else if(jdbc.update("UPDATE exercise_draft SET raw_text=?,row_version=row_version+1,updated_at=UTC_TIMESTAMP(3) WHERE sentence_id=? AND lesson_id=? AND version_id=? AND row_version=?",value.text,sentence,value.lessonId,value.versionId,revision)!=1)
            throw failure(412,"DRAFT_VERSION_CONFLICT","草稿版本冲突；保留本机文本，请比较两份草稿。");
        return Map.of("rowVersion",revision+1);
    }
    private Map<String,Object> target(String lesson,String version,String sentence) {
        var rows=jdbc.queryForList("SELECT s.text,a.storage_key,a.byte_size,a.sha256,a.status FROM sentence s JOIN lesson l ON l.id=s.lesson_id JOIN audio_asset a ON a.id=s.audio_asset_id WHERE s.id=? AND s.lesson_id=? AND s.lesson_version_id=? AND l.availability='available'",sentence,lesson,version);
        if(rows.isEmpty()) throw failure(422,"CONTEXT_MISMATCH","课次、内容版本或句子不匹配。");
        return rows.getFirst();
    }
    private void timestamp(String value) {
        try { Instant.parse(value); } catch(Exception error) { throw failure(400,"INVALID_TIMESTAMP","客户端时间必须为 ISO-8601 时间。"); }
    }
    private JsonNode command(String eventId,String operation,Object value,java.util.function.Supplier<JsonNode> work) {
        try {UUID.fromString(eventId);} catch(Exception error) {throw failure(400,"INVALID_EVENT_ID","事件标识必须为 UUID。");}
        String hash;
        try {hash=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest((operation+":"+mapper.writeValueAsString(value)).getBytes(StandardCharsets.UTF_8)));}
        catch(Exception error) {throw new IllegalStateException(error);}
        var previous=replay(eventId,hash); if(previous!=null) return previous;
        try {
            return tx.execute(status -> {
                jdbc.update("INSERT INTO command_receipt(event_id,payload_hash) VALUES (?,?)",eventId,hash);
                JsonNode response=work.get();
                jdbc.update("UPDATE command_receipt SET response_json=? WHERE event_id=?",mapper.writeValueAsString(response),eventId);
                return response;
            });
        } catch(DuplicateKeyException error) {
            var replay=replay(eventId,hash); if(replay!=null) return replay;
            throw error;
        }
    }
    private JsonNode replay(String event,String hash) {
        var rows=jdbc.queryForList("SELECT payload_hash,response_json FROM command_receipt WHERE event_id=?",event);
        if(rows.isEmpty()) return null;
        var row=rows.getFirst();
        if(!hash.equals(row.get("payload_hash"))) throw failure(409,"IDEMPOTENCY_CONFLICT","相同事件标识不能提交不同内容。");
        return mapper.readTree(row.get("response_json").toString());
    }
    @ExceptionHandler(Failure.class)
    public ProblemDetail failure(Failure error,HttpServletRequest request) {return ApiProblems.problem(HttpStatus.valueOf(error.status),error.code,error.getMessage(),request.getRequestURI());}
    private static Failure failure(int status,String code,String message) {return new Failure(status,code,message);}
    private static class Failure extends RuntimeException {
        final int status;final String code;
        Failure(int status,String code,String message) {super(message);this.status=status;this.code=code;}
    }
    public record Attempt(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@NotNull @Size(max=10000) String text,@NotNull Boolean answerExposed,@NotNull Boolean audioPlayed,@NotBlank @Size(max=40) String clientOccurredAt) {}
    public record Event(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@NotBlank @Size(max=24) String action,@NotBlank @Size(max=40) String clientOccurredAt) {}
    public record Draft(@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotNull @Size(max=10000) String text) {}
}
