package local.northstar.practice;

import java.util.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.web.bind.annotation.*;
import tools.jackson.databind.JsonNode;
import static local.northstar.practice.PracticeCommands.fail;

@RestController
public class WritingController {
    private final PracticeCommands c;
    public WritingController(PracticeCommands c){this.c=c;}
    private Map<String,Object> task(String lesson,String version) {
        var rows=c.jdbc.queryForList("SELECT id,prompt FROM writing_task WHERE lesson_id=? AND version_id=?",lesson,version);
        if(rows.isEmpty())throw fail(422,"写作任务与课程版本不匹配。");return rows.getFirst();
    }
    @GetMapping("/api/v1/writing")
    public Object get(@RequestParam String lessonId,@RequestParam String versionId) {
        var task=task(lessonId,versionId);String id=task.get("id").toString();
        var drafts=c.jdbc.queryForList("SELECT raw_text AS text,row_version AS rowVersion FROM writing_draft WHERE task_id=?",id);
        return Map.of("taskId",id,"prompt",task.get("prompt"),"sourceSentenceIds",c.jdbc.queryForList("SELECT sentence_id FROM writing_source WHERE task_id=? ORDER BY sentence_id",String.class,id),"draft",drafts.isEmpty()?Map.of("text","","rowVersion",0):drafts.getFirst(),"state",c.state(id,"writing"),"revisions",c.jdbc.queryForList("SELECT id,version_no AS versionNo,raw_text AS text,source_draft_version AS draftVersion,parent_revision_id AS parentRevisionId,created_at AS createdAt FROM writing_revision WHERE task_id=? ORDER BY version_no",id));
    }
    @PutMapping("/api/v1/writing/draft")
    @org.springframework.transaction.annotation.Transactional
    public Object draft(@Valid @RequestBody Draft value) {
        local.northstar.catalog.VersionAccess.require(c.jdbc,value.lessonId,value.versionId);
        String id=task(value.lessonId,value.versionId).get("id").toString();
        if(value.rowVersion==0) {
            try{c.jdbc.update("INSERT INTO writing_draft(task_id,raw_text) VALUES (?,?)",id,value.text);}catch(DuplicateKeyException e){throw fail(412,"另一页面已保存草稿；请比较本机与服务端文本。");}
        } else if(c.jdbc.update("UPDATE writing_draft SET raw_text=?,row_version=row_version+1,updated_at=UTC_TIMESTAMP(3) WHERE task_id=? AND row_version=?",value.text,id,value.rowVersion)!=1)throw fail(412,"草稿版本冲突；本机文本仍保留。");
        c.progress(id,"writing","in_progress");return Map.of("rowVersion",value.rowVersion+1);
    }
    @PostMapping("/api/v1/writing/revisions")
    public JsonNode revision(@Valid @RequestBody Revision value) {
        return c.command(value.eventId,"writing-revision",value,()->{
            local.northstar.catalog.VersionAccess.require(c.jdbc,value.lessonId,value.versionId);
            String task=task(value.lessonId,value.versionId).get("id").toString();
            var rows=c.jdbc.queryForList("SELECT raw_text,row_version,next_revision FROM writing_draft WHERE task_id=? FOR UPDATE",task);
            if(rows.isEmpty())throw fail(412,"请先同步草稿。");var draft=rows.getFirst();
            if(((Number)draft.get("row_version")).longValue()!=value.draftVersion || !value.text.equals(draft.get("raw_text")))throw fail(412,"草稿已更改；请先同步后再保存版本。");
            if(value.parentRevisionId!=null && c.jdbc.queryForObject("SELECT COUNT(*) FROM writing_revision WHERE id=? AND task_id=?",Integer.class,value.parentRevisionId,task)!=1)throw fail(422,"父版本不属于当前任务。");
            String id=UUID.randomUUID().toString();int number=((Number)draft.get("next_revision")).intValue();
            c.jdbc.update("INSERT INTO writing_revision(id,task_id,event_id,version_no,raw_text,source_draft_version,parent_revision_id) VALUES (?,?,?,?,?,?,?)",id,task,value.eventId,number,value.text,value.draftVersion,value.parentRevisionId);
            c.jdbc.update("UPDATE writing_draft SET next_revision=next_revision+1 WHERE task_id=?",task);
            c.jdbc.update("INSERT INTO learning_evidence(id,event_id,writing_revision_id) VALUES (?,?,?)",UUID.randomUUID().toString(),value.eventId,id);
            c.progress(task,"writing","practiced");return Map.of("id",id,"versionNo",number,"state","practiced");
        });
    }
    @PostMapping("/api/v1/practice/events")
    public JsonNode event(@Valid @RequestBody Event value) {
        return c.command(value.eventId,"practice-event",value,()->{
            local.northstar.catalog.VersionAccess.require(c.jdbc,value.lessonId,value.versionId);
            String target;
            if(value.kind.equals("writing"))target=task(value.lessonId,value.versionId).get("id").toString();
            else if(value.kind.equals("speaking")){c.context(value.lessonId,value.versionId,value.sentenceId);target=value.sentenceId;}
            else throw fail(422,"练习类型无效。");
            String state=switch(value.action){case "start"->"in_progress";case "skip"->"skipped";case "pause"->"paused";default->throw fail(422,"不能直接上报完成。");};
            c.progress(target,value.kind,state);return Map.of("state",state);
        });
    }
    public record Draft(@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotNull @Size(max=10000) String text,@Min(0) long rowVersion){}
    public record Revision(@NotBlank String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=10000) String text,@Min(1) long draftVersion,@Size(max=36) String parentRevisionId){}
    public record Event(@NotBlank String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@Size(max=64) String sentenceId,@NotBlank String kind,@NotBlank String action){}
}
