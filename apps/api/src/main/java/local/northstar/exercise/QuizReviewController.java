package local.northstar.exercise;

import java.nio.charset.StandardCharsets;
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
import tools.jackson.databind.node.ObjectNode;

@RestController
public class QuizReviewController {
    private final JdbcOperations jdbc;
    private final ExerciseController commands;
    private final JsonMapper mapper=JsonMapper.builder().build();
    private final Clock clock=Clock.systemUTC();
    public QuizReviewController(JdbcOperations jdbc,ExerciseController commands) {this.jdbc=jdbc;this.commands=commands;}
    private ResponseStatusException invalid(String text) {return new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,text);}
    private void context(String lesson,String version) {
        local.northstar.catalog.VersionAccess.require(jdbc,lesson,version);
        if(jdbc.queryForObject("SELECT COUNT(*) FROM lesson_version v JOIN lesson l ON l.id=v.lesson_id WHERE v.id=? AND l.id=? AND l.availability='available'",Integer.class,version,lesson)!=1)throw invalid("课程与版本不匹配。");
    }
    private void time(String value) {try {Instant.parse(value);}catch(Exception error){throw invalid("客户端时间必须包含时区。");}}
    @GetMapping("/api/v1/quiz")
    public Object quiz(@RequestParam String lessonId,@RequestParam String versionId) {
        context(lessonId,versionId);
        var questions=new ArrayList<JsonNode>();
        for(var row:jdbc.queryForList("SELECT payload_json FROM quiz_question WHERE version_id=? ORDER BY exercise_id",versionId)) {
            var q=(ObjectNode)mapper.readTree(row.get("payload_json").toString());q.remove(List.of("answerKey","explanation"));questions.add(q);
        }
        var history=jdbc.queryForList("SELECT id,correct_count AS correctCount,submitted_at AS submittedAt FROM quiz_run WHERE lesson_id=? AND version_id=? ORDER BY submitted_at DESC,id",lessonId,versionId);
        for(var run:history)run.put("answers",jdbc.queryForList("SELECT a.exercise_id AS exerciseId,a.sentence_id AS sentenceId,a.id AS attemptId,b.option_id AS optionId,a.correct,a.result_json AS resultJson FROM quiz_answer b JOIN exercise_attempt a ON a.id=b.attempt_id WHERE b.run_id=? ORDER BY a.exercise_id",run.get("id")));
        var states=jdbc.queryForList("SELECT current_state FROM quiz_progress WHERE version_id=?",versionId);
        return Map.of("questions",questions,"history",history,"state",states.isEmpty()?"not_started":states.getFirst().get("current_state"));
    }
    @PostMapping("/api/v1/quiz/attempts")
    public JsonNode submit(@Valid @RequestBody QuizSubmit value) {
        return commands.command(value.eventId,"quiz-submit",value,()->{
            context(value.lessonId,value.versionId);time(value.clientOccurredAt);
            var questions=jdbc.queryForList("SELECT * FROM quiz_question WHERE version_id=? ORDER BY exercise_id",value.versionId);
            if(questions.size()!=3 || value.answers.size()!=3 || !value.answers.keySet().equals(new HashSet<>(questions.stream().map(q->q.get("exercise_id").toString()).toList())))throw invalid("请完成本轮全部三题；跳过不生成作答。");
            var results=new ArrayList<Map<String,Object>>();int correctCount=0;
            for(var row:questions) {
                String id=row.get("exercise_id").toString(),selected=value.answers.get(id);
                JsonNode q=mapper.readTree(row.get("payload_json").toString());boolean valid=false;String selectedText="";
                for(JsonNode option:q.path("options"))if(option.path("id").asText().equals(selected)){valid=true;selectedText=option.path("text").asText();}
                if(!valid)throw invalid("选项不属于本题。");
                boolean correct=q.path("answerKey").asText().equals(selected);if(correct)correctCount++;
                results.add(Map.of("exerciseId",id,"optionId",selected,"selectedText",selectedText,"correct",correct,"answerKey",q.path("answerKey").asText(),"explanation",q.path("explanation").asText(),"sentenceId",row.get("sentence_id"),"knowledgePointId",row.get("knowledge_point_id"),"algorithmVersion","quiz_choice_v1"));
            }
            String run=UUID.randomUUID().toString();
            jdbc.update("INSERT INTO quiz_run(id,event_id,lesson_id,version_id,correct_count) VALUES (?,?,?,?,?)",run,value.eventId,value.lessonId,value.versionId,correctCount);
            for(var result:results) {
                String id=result.get("exerciseId").toString(),sentence=result.get("sentenceId").toString(),point=result.get("knowledgePointId").toString();
                String attempt=UUID.randomUUID().toString(),event=UUID.nameUUIDFromBytes((value.eventId+":"+id).getBytes(StandardCharsets.UTF_8)).toString();
                String resultJson=mapper.writeValueAsString(result);
                // Stable child events retain the parent command via quiz_run.event_id.
                jdbc.update("INSERT INTO command_receipt(event_id,payload_hash,response_json) VALUES (?,SHA2(?,256),?)",event,value.eventId+":"+id,resultJson);
                jdbc.update("INSERT INTO exercise_attempt(id,event_id,lesson_id,version_id,sentence_id,exercise_id,raw_text,correct,answer_exposed,algorithm_version,result_json,client_occurred_at) VALUES (?,?,?,?,?,?,?,?,FALSE,'quiz_choice_v1',?,?)",attempt,event,value.lessonId,value.versionId,sentence,id,result.get("selectedText"),result.get("correct"),resultJson,value.clientOccurredAt);
                jdbc.update("INSERT INTO quiz_answer(run_id,exercise_id,attempt_id,version_id,sentence_id,option_id) VALUES (?,?,?,?,?,?)",run,id,attempt,value.versionId,sentence,result.get("optionId"));
                jdbc.update("INSERT INTO learning_evidence(id,attempt_id,event_id) VALUES (?,?,?)",UUID.randomUUID().toString(),attempt,event);
                if(!(Boolean)result.get("correct")) {
                    String item=point+"-quiz";
                    jdbc.update("INSERT INTO review_item(id,sentence_id,version_id,target_key,card_kind,knowledge_point_id) VALUES (?,?,?,?,'quiz_choice',?) ON DUPLICATE KEY UPDATE due_at=LEAST(due_at,UTC_TIMESTAMP(3)),reps=0,row_version=row_version+1",item,sentence,value.versionId,point,point);
                    jdbc.update("INSERT INTO review_source(attempt_id,item_id,reason,sentence_id,version_id) VALUES (?,?,'quiz_choice_mismatch',?,?)",attempt,item,sentence,value.versionId);
                }
            }
            progress(value.versionId,"practiced");
            return mapper.valueToTree(Map.of("runId",run,"correctCount",correctCount,"answers",results));
        });
    }
    private void progress(String version,String state) {jdbc.update("INSERT INTO quiz_progress(version_id,current_state) VALUES (?,?) ON DUPLICATE KEY UPDATE current_state=?",version,state,state);}
    @PostMapping("/api/v1/quiz/events")
    public JsonNode event(@Valid @RequestBody QuizEvent value) {
        return commands.command(value.eventId,"quiz-event",value,()->{
            context(value.lessonId,value.versionId);time(value.clientOccurredAt);
            String state=switch(value.action){case "start"->"in_progress";case "skip"->"skipped";case "pause"->"paused";default->throw invalid("仅支持开始、暂停、跳过。");};
            progress(value.versionId,state);return mapper.valueToTree(Map.of("state",state));
        });
    }
    @GetMapping("/api/v1/reviews/due")
    public Object due(@RequestParam(defaultValue="false") boolean all) {
        var items=jdbc.queryForList("SELECT r.id,(r.due_at<=UTC_TIMESTAMP(3)) AS due,r.sentence_id AS sentenceId,r.version_id AS versionId,s.lesson_id AS lessonId,v.payload_json->>'$.title' AS lessonTitle,s.sequence_no AS sequence,s.translation AS prompt,r.card_kind AS cardKind,k.id AS knowledgePointId,r.due_at AS dueAt,r.row_version AS rowVersion,r.reps,r.scheduler_version AS schedulerVersion FROM review_item r JOIN sentence s ON s.id=r.sentence_id JOIN lesson_version v ON v.id=r.version_id LEFT JOIN knowledge_point k ON k.id=r.knowledge_point_id WHERE r.status='pending' AND r.owner_key='local'"+(all?"":" AND r.due_at<=UTC_TIMESTAMP(3)")+" ORDER BY r.due_at,r.id");
        for(var item:items) {
            item.put("sources",jdbc.queryForList("SELECT a.id AS attemptId,a.exercise_id AS exerciseId,rs.reason,a.recorded_at AS recordedAt FROM review_source rs JOIN exercise_attempt a ON a.id=rs.attempt_id WHERE rs.item_id=? ORDER BY a.recorded_at DESC,a.id",item.get("id")));
            item.put("history",jdbc.queryForList("SELECT event_id AS eventId,rating,origin,next_due_at AS nextDueAt,recorded_at AS recordedAt FROM review_result WHERE item_id=? ORDER BY recorded_at DESC,event_id",item.get("id")));
        }
        return items;
    }
    @GetMapping("/api/v1/reviews/{id}/answer")
    public Object answer(@PathVariable String id) {
        var rows=jdbc.queryForList("SELECT s.text,s.explanation FROM review_item r JOIN sentence s ON s.id=r.sentence_id WHERE r.id=? AND r.owner_key='local'",id);
        if(rows.isEmpty())throw new ResponseStatusException(HttpStatus.NOT_FOUND,"复习卡不存在。");
        var answer=rows.getFirst();
        answer.put("attempts",jdbc.queryForList("SELECT a.id AS attemptId,a.raw_text AS rawText,a.recorded_at AS recordedAt FROM review_source rs JOIN exercise_attempt a ON a.id=rs.attempt_id WHERE rs.item_id=? ORDER BY a.recorded_at DESC,a.id",id));
        return answer;
    }
    @PostMapping("/api/v1/reviews/{id}/results")
    public JsonNode rate(@PathVariable String id,@Valid @RequestBody ReviewRating value) {
        return commands.command(value.eventId,"review-rating:"+id,value,()->{
            context(value.lessonId,value.versionId);time(value.clientOccurredAt);
            var rows=jdbc.queryForList("SELECT * FROM review_item WHERE id=? AND owner_key='local' FOR UPDATE",id);
            if(rows.isEmpty())throw new ResponseStatusException(HttpStatus.NOT_FOUND,"复习卡不存在。");
            var row=rows.getFirst();
            if(!row.get("version_id").equals(value.versionId) || !row.get("sentence_id").equals(value.sentenceId) || !jdbc.queryForObject("SELECT lesson_id FROM lesson_version WHERE id=?",String.class,value.versionId).equals(value.lessonId))throw invalid("复习上下文不匹配。");
            if(((Number)row.get("row_version")).longValue()!=value.rowVersion)throw new ResponseStatusException(HttpStatus.CONFLICT,"此卡已被另一页面更新，请重新读取；原操作未计数。");
            Instant now=clock.instant(),due=row.get("due_at") instanceof Timestamp t ? t.toInstant() : ((LocalDateTime)row.get("due_at")).toInstant(ZoneOffset.UTC);
            if(due.isAfter(now))throw new ResponseStatusException(HttpStatus.CONFLICT,"此卡尚未到期，请到期后再复习。");
            if(!value.answerRevealed || !Set.of("again","good").contains(value.rating))throw invalid("请先翻卡，再选择真实的人工自评。");
            int reps=((Number)row.get("reps")).intValue();Instant next=SimpleScheduler.next(clock,value.rating,reps);
            jdbc.update("INSERT INTO review_result(event_id,item_id,rating,previous_due_at,next_due_at,previous_row_version,client_occurred_at) VALUES (?,?,?,?,?,?,?)",value.eventId,id,value.rating,Timestamp.from(due),Timestamp.from(next),value.rowVersion,value.clientOccurredAt);
            jdbc.update("UPDATE review_item SET due_at=?,reps=?,row_version=row_version+1 WHERE id=?",Timestamp.from(next),value.rating.equals("good")?reps+1:0,id);
            return mapper.valueToTree(Map.of("eventId",value.eventId,"nextDueAt",next.toString(),"rowVersion",value.rowVersion+1,"origin","self_rating","schedulerVersion","simple_v1"));
        });
    }
    @ExceptionHandler(ExerciseController.Failure.class)
    public ProblemDetail failure(ExerciseController.Failure error,HttpServletRequest request){return commands.failure(error,request);}
    public record QuizSubmit(@NotBlank String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotNull @Size(min=3,max=3) Map<@NotBlank String,@NotBlank String> answers,@NotBlank String clientOccurredAt) {}
    public record QuizEvent(@NotBlank String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank String action,@NotBlank String clientOccurredAt) {}
    public record ReviewRating(@NotBlank String eventId,@NotBlank String lessonId,@NotBlank String versionId,@NotBlank String sentenceId,@Min(1) long rowVersion,@NotBlank String rating,boolean answerRevealed,@NotBlank String clientOccurredAt) {}
}
