package local.northstar.study;

import java.util.Map;
import java.util.Set;
import java.util.UUID;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import local.northstar.common.ApiProblems;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.web.bind.annotation.*;

/** A browsing checkpoint only: never an exercise attempt or evidence of practice. */
@RestController
public class StudyController {
    private static final Set<String> TABS = Set.of("text", "dictation", "vocabulary", "speaking", "writing", "quiz");
    private final JdbcOperations jdbc;
    public StudyController(JdbcOperations jdbc) { this.jdbc = jdbc; }

    @GetMapping("/api/v1/study/resume")
    public ResponseEntity<?> resume() {
        var rows = jdbc.queryForList("SELECT session_id AS sessionId, lesson_id AS lessonId, version_id AS versionId, sentence_id AS sentenceId, tab_key AS tab, show_english AS showEnglish, show_translation AS showTranslation, row_version AS rowVersion FROM study_resume WHERE owner_key='local'");
        if (rows.isEmpty()) return ResponseEntity.noContent().build();
        var row = rows.getFirst();
        return ResponseEntity.ok().eTag("\"" + row.get("rowVersion") + "\"").body(row);
    }

    @PutMapping("/api/v1/study/resume")
    public ResponseEntity<?> save(@Valid @RequestBody Checkpoint checkpoint,
            @RequestHeader(value = "If-Match", required = false) String match) {
        if (match == null) throw new Failure(HttpStatus.PRECONDITION_REQUIRED, "REVISION_REQUIRED", "保存浏览位置需要版本号。");
        if (!match.matches("\"[0-9]{1,16}\"")) throw new Failure(HttpStatus.BAD_REQUEST, "INVALID_REVISION", "版本号格式不正确。");
        validate(checkpoint);
        long revision = Long.parseLong(match.substring(1, match.length() - 1));
        if (revision == 0) {
            try {
                jdbc.update("INSERT INTO study_resume(owner_key,session_id,lesson_id,version_id,sentence_id,tab_key,show_english,show_translation) VALUES ('local',?,?,?,?,?,?,?)",
                        UUID.randomUUID().toString(), checkpoint.lessonId, checkpoint.versionId, checkpoint.sentenceId,
                        checkpoint.tab, checkpoint.showEnglish, checkpoint.showTranslation);
            } catch (DuplicateKeyException exception) { throw conflict(); }
        } else {
            int changed = jdbc.update("UPDATE study_resume SET lesson_id=?,version_id=?,sentence_id=?,tab_key=?,show_english=?,show_translation=?,row_version=row_version+1,updated_at=UTC_TIMESTAMP(3) WHERE owner_key='local' AND row_version=?",
                    checkpoint.lessonId, checkpoint.versionId, checkpoint.sentenceId, checkpoint.tab,
                    checkpoint.showEnglish, checkpoint.showTranslation, revision);
            if (changed != 1) throw conflict();
        }
        // Return the committed revision, not a subsequent reader's potentially newer checkpoint.
        return ResponseEntity.ok().eTag("\"" + (revision + 1) + "\"").body(Map.of("rowVersion", revision + 1));
    }

    @PostMapping("/api/v1/study/sessions")
    public ResponseEntity<?> session(@Valid @RequestBody Checkpoint checkpoint,
            @RequestHeader(value = "If-Match", required = false) String match) {
        return save(checkpoint, match);
    }

    private void validate(Checkpoint value) {
        if (!TABS.contains(value.tab)) throw new Failure(HttpStatus.BAD_REQUEST, "INVALID_TAB", "学习页签不受支持。");
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM sentence s JOIN lesson l ON l.id=s.lesson_id WHERE s.id=? AND s.lesson_id=? AND s.lesson_version_id=? AND l.current_version_id=? AND l.availability='available'", Integer.class,
                value.sentenceId, value.lessonId, value.versionId, value.versionId);
        if (count == null || count != 1) throw new Failure(HttpStatus.NOT_FOUND, "CONTEXT_NOT_FOUND", "课次、内容版本或句子不匹配。");
    }

    private static Failure conflict() { return new Failure(HttpStatus.PRECONDITION_FAILED, "RESUME_CONFLICT", "另一页面已更新浏览位置，请重新载入后再保存。"); }
    @ExceptionHandler(Failure.class)
    public org.springframework.http.ProblemDetail failure(Failure error, HttpServletRequest request) {
        return ApiProblems.problem(error.status, error.code, error.getMessage(), request.getRequestURI());
    }
    private static class Failure extends RuntimeException {
        final HttpStatus status; final String code;
        Failure(HttpStatus status, String code, String detail) { super(detail); this.status = status; this.code = code; }
    }
    public record Checkpoint(@NotBlank @Size(max=64) String lessonId, @NotBlank @Size(max=64) String versionId,
            @NotBlank @Size(max=64) String sentenceId, @NotBlank @Size(max=16) String tab,
            @NotNull Boolean showEnglish, @NotNull Boolean showTranslation) {}
}
