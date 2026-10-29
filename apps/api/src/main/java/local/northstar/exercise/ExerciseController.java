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
    private void readingContext(String lesson,String version) {
        local.northstar.catalog.VersionAccess.require(jdbc,lesson,version);
        if(jdbc.queryForObject("SELECT COUNT(*) FROM lesson_version v JOIN lesson l ON l.id=v.lesson_id WHERE v.id=? AND l.id=? AND l.availability='available'",Integer.class,version,lesson)!=1)
            throw failure(422,"CONTEXT_MISMATCH","课次与内容版本不匹配。");
    }
    @GetMapping("/api/v1/reading")
    public Object reading(@RequestParam String lessonId,@RequestParam String versionId) {
        readingContext(lessonId,versionId);
        var words=jdbc.queryForList("SELECT k.id,k.sentence_id AS sentenceId,s.sequence_no AS sequence,s.text AS sourceText,k.term,k.meaning,k.usage_note AS usageNote,k.example_text AS example,COALESCE(f.favorite,FALSE) AS favorite FROM knowledge_point k JOIN sentence s ON s.id=k.sentence_id LEFT JOIN vocabulary_favorite f ON f.knowledge_point_id=k.id WHERE k.id<>CONCAT(k.version_id,'-kp-please') AND k.lesson_id=? AND k.version_id=? ORDER BY s.sequence_no,k.id",lessonId,versionId);
        for(var word:words) word.put("favorite",((Number)word.get("favorite")).intValue()!=0);
        var questions=new ArrayList<Object>();
        for(var row:jdbc.queryForList("SELECT r.exercise_id,r.payload_json,r.knowledge_point_id,r.sentence_id,COALESCE(p.current_state,'not_started') AS state FROM reading_question r JOIN exercise e ON e.id=r.exercise_id LEFT JOIN reading_progress p ON p.exercise_id=e.id WHERE e.lesson_id=? AND e.version_id=? ORDER BY e.id",lessonId,versionId)) {
            var question=(tools.jackson.databind.node.ObjectNode)mapper.readTree(row.get("payload_json").toString());
            question.remove(List.of("answerKey","explanation"));
            question.put("knowledgePointId",row.get("knowledge_point_id").toString());
            question.put("sentenceId",row.get("sentence_id").toString());
            question.put("state",row.get("state").toString());
            question.set("history",mapper.valueToTree(jdbc.queryForList("SELECT a.id AS attemptId,a.event_id AS eventId,b.option_id AS optionId,a.correct,a.result_json AS resultJson,a.recorded_at AS recordedAt FROM exercise_attempt a JOIN reading_answer b ON b.attempt_id=a.id WHERE a.exercise_id=? ORDER BY a.recorded_at DESC,a.id",row.get("exercise_id"))));
            questions.add(question);
        }
        return Map.of("vocabulary",words,"questions",questions);
    }
    @PutMapping("/api/v1/knowledge/{id}/favorite")
    @org.springframework.transaction.annotation.Transactional
    public Object favorite(@PathVariable String id,@Valid @RequestBody Favorite value) {
        readingContext(value.lessonId,value.versionId);
        if(jdbc.queryForObject("SELECT COUNT(*) FROM knowledge_point WHERE id=? AND lesson_id=? AND version_id=?",Integer.class,id,value.lessonId,value.versionId)!=1) throw failure(422,"CONTEXT_MISMATCH","词条不属于当前课程版本。");
        jdbc.update("INSERT INTO vocabulary_favorite(knowledge_point_id,favorite) VALUES (?,?) ON DUPLICATE KEY UPDATE favorite=?,updated_at=UTC_TIMESTAMP(3)",id,value.favorite,value.favorite);
        return Map.of("favorite",value.favorite);
    }
    private Map<String,Object> readingTarget(String id,String lesson,String version) {
        readingContext(lesson,version);
        var rows=jdbc.queryForList("SELECT r.payload_json,r.sentence_id,r.knowledge_point_id FROM reading_question r JOIN exercise e ON e.id=r.exercise_id WHERE e.id=? AND e.lesson_id=? AND e.version_id=?",id,lesson,version);
        if(rows.isEmpty()) throw failure(422,"CONTEXT_MISMATCH","阅读题不属于当前课程版本。");
        return rows.getFirst();
    }
    @PostMapping("/api/v1/reading/{id}/attempts")
    public JsonNode readingAttempt(@PathVariable String id,@Valid @RequestBody ReadingAttempt value) {
        return command(value.eventId,"reading:"+id,value,() -> {
            timestamp(value.clientOccurredAt);
            var row=readingTarget(id,value.lessonId,value.versionId);
            var question=mapper.readTree(row.get("payload_json").toString());
            JsonNode selected=null,correctOption=null;
            for(JsonNode option:question.path("options")) {
                if(option.path("id").asText().equals(value.optionId)) selected=option;
                if(option.path("id").asText().equals(question.path("answerKey").asText())) correctOption=option;
            }
            if(selected==null) throw failure(422,"INVALID_OPTION","请选择本题的有效选项。");
            if(correctOption==null) throw new IllegalStateException("Reading answer missing");
            String sentence=row.get("sentence_id").toString(),knowledge=row.get("knowledge_point_id").toString();
            String standard=jdbc.queryForObject("SELECT text FROM sentence WHERE id=?",String.class,sentence);
            boolean correct=value.optionId.equals(question.path("answerKey").asText());
            var result=Map.of("correct",correct,"correctOptionId",correctOption.path("id").asText(),"correctText",correctOption.path("text").asText(),"sentenceId",sentence,"knowledgePointId",knowledge,"standardText",standard,"explanation","beside 表示 next to；第 6 句直接说明植物应放在蓝色长椅旁边。","algorithmVersion","reading_choice_v1");
            String attempt=UUID.randomUUID().toString(),evidence=UUID.randomUUID().toString();
            jdbc.update("INSERT INTO exercise_attempt(id,event_id,lesson_id,version_id,sentence_id,exercise_id,raw_text,correct,answer_exposed,algorithm_version,result_json,client_occurred_at) VALUES (?,?,?,?,?,?,?,?,TRUE,'reading_choice_v1',?,?)",attempt,value.eventId,value.lessonId,value.versionId,sentence,id,selected.path("text").asText(),correct,mapper.writeValueAsString(result),value.clientOccurredAt);
            jdbc.update("INSERT INTO reading_answer(attempt_id,exercise_id,option_id,version_id,sentence_id) VALUES (?,?,?,?,?)",attempt,id,value.optionId,value.versionId,sentence);
            jdbc.update("INSERT INTO learning_evidence(id,attempt_id,event_id) VALUES (?,?,?)",evidence,attempt,value.eventId);
            jdbc.update("INSERT INTO reading_progress(exercise_id,current_state) VALUES (?,'practiced') ON DUPLICATE KEY UPDATE current_state='practiced'",id);
            if(!correct) {
                jdbc.update("INSERT INTO review_item(id,sentence_id,version_id,target_key,card_kind,knowledge_point_id) VALUES (?,?,?,?,'reading_choice',?) ON DUPLICATE KEY UPDATE due_at=LEAST(due_at,UTC_TIMESTAMP(3)),reps=0,row_version=row_version+1",knowledge+"-reading",sentence,value.versionId,knowledge,knowledge);
                jdbc.update("INSERT INTO review_source(attempt_id,item_id,reason,sentence_id,version_id) VALUES (?,?,'reading_evidence_mismatch',?,?)",attempt,knowledge+"-reading",sentence,value.versionId);
            }
            return mapper.valueToTree(Map.of("attemptId",attempt,"eventId",value.eventId,"evidenceId",evidence,"state","practiced","result",result));
        });
    }
    @PostMapping("/api/v1/reading/{id}/events")
    public JsonNode readingEvent(@PathVariable String id,@Valid @RequestBody ReadingEvent value) {
        return command(value.eventId,"reading-event:"+id,value,() -> {
            timestamp(value.clientOccurredAt); readingTarget(id,value.lessonId,value.versionId);
            String state=switch(value.action) { case "start" -> "in_progress"; case "skip" -> "skipped"; case "pause" -> "paused"; default -> throw failure(422,"INVALID_ACTION","不能直接标记阅读练习完成。"); };
            jdbc.update("INSERT INTO reading_progress(exercise_id,current_state) VALUES (?,?) ON DUPLICATE KEY UPDATE current_state=?",id,state,state);
            return mapper.valueToTree(Map.of("eventId",value.eventId,"state",state));
        });
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
                jdbc.update("INSERT INTO review_item(id,sentence_id,version_id,target_key) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE due_at=LEAST(due_at,UTC_TIMESTAMP(3)),reps=0,row_version=row_version+1",itemId,value.sentenceId,value.versionId,value.sentenceId);
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
        return jdbc.queryForList("SELECT r.id,r.status,a.id AS attemptId,a.lesson_id AS lessonId,a.version_id AS versionId,a.sentence_id AS sentenceId,a.exercise_id AS exerciseId,e.kind,COALESCE(r.knowledge_point_id,rq.knowledge_point_id) AS knowledgePointId,ra.option_id AS optionId,a.raw_text AS rawText,s.sequence_no AS sequence,s.text AS standardText,rs.reason,a.recorded_at AS recordedAt FROM review_item r JOIN review_source rs ON rs.item_id=r.id JOIN exercise_attempt a ON a.id=rs.attempt_id JOIN exercise e ON e.id=a.exercise_id LEFT JOIN reading_question rq ON rq.exercise_id=e.id LEFT JOIN reading_answer ra ON ra.attempt_id=a.id JOIN sentence s ON s.id=a.sentence_id ORDER BY a.recorded_at DESC,a.id");
    }
    @GetMapping("/api/v1/drafts/{sentence}")
    public Object draft(@PathVariable String sentence,@RequestParam String lessonId,@RequestParam String versionId) {
        var rows=jdbc.queryForList("SELECT raw_text AS text,row_version AS rowVersion FROM exercise_draft WHERE sentence_id=? AND lesson_id=? AND version_id=?",sentence,lessonId,versionId);
        return rows.isEmpty()?Map.of("text","","rowVersion",0):rows.getFirst();
    }
    @PutMapping("/api/v1/drafts/{sentence}")
    @org.springframework.transaction.annotation.Transactional
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
        local.northstar.catalog.VersionAccess.require(jdbc,lesson,version);
        var rows=jdbc.queryForList("SELECT s.text,a.storage_key,a.byte_size,a.sha256,a.status FROM sentence s JOIN lesson l ON l.id=s.lesson_id JOIN audio_asset a ON a.id=s.audio_asset_id WHERE s.id=? AND s.lesson_id=? AND s.lesson_version_id=? AND l.availability='available'",sentence,lesson,version);
        if(rows.isEmpty()) throw failure(422,"CONTEXT_MISMATCH","课次、内容版本或句子不匹配。");
        return rows.getFirst();
    }
    private void timestamp(String value) {
        try { Instant.parse(value); } catch(Exception error) { throw failure(400,"INVALID_TIMESTAMP","客户端时间必须为 ISO-8601 时间。"); }
    }
    JsonNode command(String eventId,String operation,Object value,java.util.function.Supplier<JsonNode> work) {
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
    static class Failure extends RuntimeException {
        final int status;final String code;
        Failure(int status,String code,String message) {super(message);this.status=status;this.code=code;}
    }
    public record Attempt(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@NotNull @Size(max=10000) String text,@NotNull Boolean answerExposed,@NotNull Boolean audioPlayed,@NotBlank @Size(max=40) String clientOccurredAt) {}
    public record Event(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@NotBlank @Size(max=24) String action,@NotBlank @Size(max=40) String clientOccurredAt) {}
    public record Draft(@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotNull @Size(max=10000) String text) {}
    public record Favorite(@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotNull Boolean favorite) {}
    public record ReadingAttempt(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String optionId,@NotBlank @Size(max=40) String clientOccurredAt) {}
    public record ReadingEvent(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=24) String action,@NotBlank @Size(max=40) String clientOccurredAt) {}
}
