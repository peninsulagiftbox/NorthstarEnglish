package local.northstar.report;

import java.util.*;
import java.time.Instant;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class ReportController {
    private final JdbcTemplate db;
    public ReportController(JdbcTemplate db) { this.db = db; }

    @GetMapping("/api/v1/reports")
    @Transactional(readOnly=true, isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> report(@RequestParam(required=false) String lessonId,@RequestParam(required=false) String versionId,
        @RequestParam(required=false) String from,@RequestParam(required=false) String to,
        @RequestParam(required=false) String setId,@RequestParam(required=false) String purpose) {
        if(purpose!=null && !purpose.equals("quiz"))throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"暂不支持该purpose的指标筛选。");
        Instant fromTime=instant(from,"from"),toTime=instant(to,"to");
        var metrics = new LinkedHashMap<String,Object>();
        metrics.put("dictation", db.queryForMap("SELECT COUNT(*) AS submitted, COALESCE(SUM(correct),0) AS exactMatches, COALESCE(SUM(NOT answer_exposed),0) AS independentSubmitted, COALESCE(SUM(correct AND NOT answer_exposed),0) AS independentMatches FROM exercise_attempt a JOIN exercise e ON e.id=a.exercise_id WHERE e.kind='dictation'"));
        metrics.put("reading", db.queryForMap("SELECT COUNT(*) AS submitted, COALESCE(SUM(a.correct),0) AS correct FROM reading_answer r JOIN exercise_attempt a ON a.id=r.attempt_id"));
        metrics.put("recordings", db.queryForMap("SELECT COUNT(*) AS recorded, COALESCE(SUM(status='ready'),0) AS available, COALESCE(SUM(status='deleted'),0) AS deleted FROM personal_recording"));
        metrics.put("writing", db.queryForMap("SELECT COUNT(*) AS versions FROM writing_revision"));
        String filter=quizFilter(lessonId,versionId,setId,fromTime,toTime);
        var quizRuns=new ArrayList<Map<String,Object>>();
        for(var run:db.queryForList("SELECT r.id,r.lesson_id AS lessonId,r.version_id AS versionId,r.set_id AS setId,r.set_hash AS setHash,r.correct_count AS correctCount,r.total_count AS totalCount,r.submitted_count AS submittedCount,r.submitted_at AS submittedAt"+(filter.isEmpty()?" FROM quiz_run r":" FROM quiz_run r"+filter)+" ORDER BY r.submitted_at,r.id")) {
            boolean verified=((Number)run.get("totalCount")).intValue()>0 && run.get("totalCount").equals(run.get("submittedCount")) && db.queryForObject("SELECT COUNT(*) FROM quiz_run_item WHERE run_id=?",Integer.class,run.get("id"))==((Number)run.get("totalCount")).intValue();
            run.put("verified",verified);
            if(verified)run.put("accuracy",((Number)run.get("correctCount")).doubleValue()/((Number)run.get("totalCount")).intValue());
            quizRuns.add(run);
        }
        metrics.put("quiz", quizMetrics(filter));
        var scope=new LinkedHashMap<String,Object>();
        if(lessonId!=null)scope.put("lessonId",lessonId);if(versionId!=null)scope.put("versionId",versionId);
        if(fromTime!=null)scope.put("from",fromTime.toString());if(toTime!=null)scope.put("to",toTime.toString());
        scope.put("purpose","quiz");scope.put("timeBasis","UTC,from包含,to不包含");scope.put("appliesTo","仅测验指标与逐run明细；其余指标未筛选。");
        metrics.put("review", db.queryForMap("SELECT COUNT(*) AS cards, COALESCE(SUM(due_at<=UTC_TIMESTAMP(3)),0) AS due FROM review_item"));
        metrics.put("selfRatings", db.queryForMap("SELECT COUNT(*) AS submitted FROM review_result"));
        var lessons = new ArrayList<Map<String,Object>>();
        for (var lesson : db.queryForList("SELECT v.id AS versionId,l.id AS lessonId,JSON_UNQUOTE(JSON_EXTRACT(v.payload_json,'$.title')) AS title FROM lesson_version v JOIN lesson l ON l.id=v.lesson_id WHERE l.availability='available' ORDER BY v.id")) {
            String version = lesson.get("versionId").toString();
            var paths = new ArrayList<Map<String,Object>>();
            boolean browsed = count("SELECT COUNT(*) FROM study_resume WHERE version_id=?",version)>0;
            paths.add(Map.of("tab","text","state",browsed?"browsing":"not_started","evidenceCount",0));
            paths.add(path("dictation", db.queryForList("SELECT current_state FROM study_stage WHERE version_id=?",version), count("SELECT COUNT(*) FROM exercise_attempt a JOIN exercise e ON e.id=a.exercise_id WHERE a.version_id=? AND e.kind='dictation'",version)));
            paths.add(path("vocabulary", db.queryForList("SELECT p.current_state FROM reading_progress p JOIN exercise e ON e.id=p.exercise_id WHERE e.version_id=?",version), count("SELECT COUNT(*) FROM reading_answer WHERE version_id=?",version)));
            paths.add(path("speaking", db.queryForList("SELECT p.current_state FROM practice_progress p JOIN sentence s ON s.id=p.target_key WHERE p.kind='speaking' AND s.lesson_version_id=?",version),count("SELECT COUNT(*) FROM learning_evidence e JOIN recording_observation o ON o.event_id=e.recording_event_id JOIN personal_recording r ON r.id=o.recording_id WHERE r.version_id=?",version)));
            paths.add(path("writing", db.queryForList("SELECT p.current_state FROM practice_progress p JOIN writing_task t ON t.id=p.target_key WHERE p.kind='writing' AND t.version_id=?",version),count("SELECT COUNT(*) FROM writing_revision r JOIN writing_task t ON t.id=r.task_id WHERE t.version_id=?",version)));
            paths.add(path("quiz", db.queryForList("SELECT current_state FROM quiz_progress WHERE version_id=?",version),count("SELECT COUNT(*) FROM quiz_run WHERE version_id=?",version)));
            lesson.put("paths",paths); lesson.put("practicedStages",paths.stream().filter(p->((Number)p.get("evidenceCount")).longValue()>0).count());
            lessons.add(lesson);
        }
        return Map.of("generatedAt",java.time.Instant.now().toString(),"metrics",metrics,"lessons",lessons,
            "quizScope",scope,"quizRuns",quizRuns,
            "readingHistory",db.queryForList("SELECT a.id,a.lesson_id AS lessonId,a.version_id AS versionId,a.sentence_id AS sentenceId,a.exercise_id AS exerciseId,a.correct,a.recorded_at AS recordedAt,r.option_id AS optionId FROM reading_answer r JOIN exercise_attempt a ON a.id=r.attempt_id ORDER BY a.recorded_at DESC,a.id"),
            "measurementNote","真实提交与人工自评分列；没有客观延时复测或能力分数。");
    }
    private Instant instant(String value,String field) {
        if(value==null)return null;
        try {return Instant.parse(value);}
        catch(Exception error) {throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,field+"必须是UTC时间。");}
    }
    private String quizFilter(String lessonId,String versionId,String setId,Instant fromTime,Instant toTime) {
        var clauses=new ArrayList<String>();
        if(lessonId!=null)clauses.add("r.lesson_id='"+lessonId.replace("'","''")+"'");
        if(versionId!=null)clauses.add("r.version_id='"+versionId.replace("'","''")+"'");
        if(setId!=null)clauses.add("r.set_id='"+setId.replace("'","''")+"'");
        var mysql=java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS").withZone(java.time.ZoneOffset.UTC);
        if(fromTime!=null)clauses.add("r.submitted_at>= '"+mysql.format(fromTime)+"'");
        if(toTime!=null)clauses.add("r.submitted_at< '"+mysql.format(toTime)+"'");
        return clauses.isEmpty()?"":" WHERE "+String.join(" AND ",clauses);
    }
    private Map<String,Object> quizMetrics(String filter) {
        String verifiedClause="r.total_count IS NOT NULL AND r.submitted_count=r.total_count AND (SELECT COUNT(*) FROM quiz_run_item i WHERE i.run_id=r.id)=r.total_count";
        var all=db.queryForMap("SELECT COUNT(*) AS runs FROM quiz_run r"+(filter.isEmpty()?"":filter));
        var verified=db.queryForMap("SELECT COUNT(*) AS verifiedRuns,COALESCE(SUM(r.correct_count),0) AS correct,COALESCE(SUM(r.total_count),0) AS total FROM quiz_run r"+(filter.isEmpty()?" WHERE "+verifiedClause:filter+" AND "+verifiedClause));
        long unverified=((Number)all.get("runs")).longValue()-((Number)verified.get("verifiedRuns")).longValue();
        var result=new LinkedHashMap<String,Object>();
        result.put("runs",verified.get("verifiedRuns"));result.put("correct",verified.get("correct"));result.put("total",verified.get("total"));
        result.put("verifiedRuns",verified.get("verifiedRuns"));result.put("unverifiedRuns",unverified);
        result.put("accuracy",((Number)verified.get("total")).longValue()==0?null:((Number)verified.get("correct")).doubleValue()/((Number)verified.get("total")).longValue());
        result.put("note",((Number)verified.get("total")).longValue()==0?"尚无测验数据":"分母为核验通过run的真实题目数总和；未核验历史不计入分子分母。");
        return result;
    }
    private long count(String sql,String version) { return db.queryForObject(sql,Long.class,version); }
    private Map<String,Object> path(String tab,List<Map<String,Object>> rows,long evidence) {
        var states=rows.stream().map(r->r.get("current_state").toString()).toList();
        String state="not_started";
        for(String candidate:List.of("in_progress","paused","skipped","practiced")) if(states.contains(candidate)){state=candidate;break;}
        // A current projection alone cannot manufacture a practiced fact.
        if(state.equals("practiced") && evidence==0)state="not_started";
        if(state.equals("not_started") && evidence>0)state="practiced";
        return Map.of("tab",tab,"state",state,"evidenceCount",evidence);
    }
    @PutMapping("/api/v1/settings")
    public Map<String,Object> save(@Valid @RequestBody Preferences value) {
        if(!Set.of(0.75,1.0,1.25,1.5).contains(value.defaultSpeed))throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"不支持的播放倍速。");
        int changed=db.update("UPDATE user_setting SET default_speed=?,show_translation=?,show_hints=?,shortcut_enabled=?,recording_enabled=?,row_version=row_version+1,updated_at=UTC_TIMESTAMP(3) WHERE owner_key='local' AND row_version=?",value.defaultSpeed,value.showTranslation,value.showHints,value.shortcutEnabled,value.recordingEnabled,value.rowVersion);
        if(changed!=1)throw new ResponseStatusException(HttpStatus.CONFLICT,"偏好已由另一页面更新，请重新读取后修改。");
        return Map.of("rowVersion",value.rowVersion+1);
    }
    public record Preferences(@NotNull Double defaultSpeed,@NotNull Boolean showTranslation,@NotNull Boolean showHints,@NotNull Boolean shortcutEnabled,@NotNull Boolean recordingEnabled,@NotNull @Min(0) Long rowVersion) {}
}
