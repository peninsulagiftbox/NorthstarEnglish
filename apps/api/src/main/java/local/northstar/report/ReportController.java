package local.northstar.report;

import java.util.*;
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
    public Map<String,Object> report() {
        var metrics = new LinkedHashMap<String,Object>();
        metrics.put("dictation", db.queryForMap("SELECT COUNT(*) AS submitted, COALESCE(SUM(correct),0) AS exactMatches, COALESCE(SUM(NOT answer_exposed),0) AS independentSubmitted, COALESCE(SUM(correct AND NOT answer_exposed),0) AS independentMatches FROM exercise_attempt a JOIN exercise e ON e.id=a.exercise_id WHERE e.kind='dictation'"));
        metrics.put("reading", db.queryForMap("SELECT COUNT(*) AS submitted, COALESCE(SUM(a.correct),0) AS correct FROM reading_answer r JOIN exercise_attempt a ON a.id=r.attempt_id"));
        metrics.put("recordings", db.queryForMap("SELECT COUNT(*) AS recorded, COALESCE(SUM(status='ready'),0) AS available, COALESCE(SUM(status='deleted'),0) AS deleted FROM personal_recording"));
        metrics.put("writing", db.queryForMap("SELECT COUNT(*) AS versions FROM writing_revision"));
        metrics.put("quiz", db.queryForMap("SELECT COUNT(*) AS runs, COALESCE(SUM(correct_count),0) AS correct, COUNT(*)*3 AS total FROM quiz_run"));
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
            "readingHistory",db.queryForList("SELECT a.id,a.lesson_id AS lessonId,a.version_id AS versionId,a.sentence_id AS sentenceId,a.exercise_id AS exerciseId,a.correct,a.recorded_at AS recordedAt,r.option_id AS optionId FROM reading_answer r JOIN exercise_attempt a ON a.id=r.attempt_id ORDER BY a.recorded_at DESC,a.id"),
            "measurementNote","真实提交与人工自评分列；没有客观延时复测或能力分数。");
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
