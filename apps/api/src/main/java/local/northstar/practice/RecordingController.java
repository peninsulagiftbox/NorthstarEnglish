package local.northstar.practice;

import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.*;
import jakarta.annotation.PostConstruct;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import tools.jackson.databind.JsonNode;
import static local.northstar.practice.PracticeCommands.fail;

@RestController
public class RecordingController {
    private final PracticeCommands c;
    private final Path root;
    public RecordingController(PracticeCommands c,@Value("${northstar.recording-root:${user.home}/Library/Application Support/NorthstarEnglish/recordings}") String folder,@Value("${DB_NAME:northstar_english}") String database){
        this.c=c;root=Path.of(folder).toAbsolutePath().normalize().resolve(database);
    }
    @PostConstruct public void reconcile() throws Exception {
        Files.createDirectories(root);if(Files.isSymbolicLink(root))throw new IllegalStateException("Recording directory must be private");
        Files.setPosixFilePermissions(root,PosixFilePermissions.fromString("rwx------"));
        for(var row:c.jdbc.queryForList("SELECT id,sha256,byte_size,status FROM personal_recording WHERE status<>'deleted'")) {
            String status=validFile(row)?"ready":"missing";
            if(!status.equals(row.get("status")))c.jdbc.update("UPDATE personal_recording SET status=? WHERE id=?",status,row.get("id"));
        }
        var known=new HashSet<String>(c.jdbc.queryForList("SELECT id FROM personal_recording",String.class));
        long orphanCount;
        try(var files=Files.list(root)){orphanCount=files.filter(p -> p.toString().endsWith(".part") || (p.toString().endsWith(".audio") && !known.contains(p.getFileName().toString().replace(".audio","")))).count();}
        System.getLogger(RecordingController.class.getName()).log(System.Logger.Level.INFO,"Recording reconciliation: orphan/partial files="+orphanCount+"; retained for manual review");
        // Orphans are retained for manual review; never delete unknown files at startup.
    }
    private Path path(String id) {try{if(!UUID.fromString(id).toString().equals(id))throw new Exception();}catch(Exception e){throw fail(400,"无效录音标识。");}return root.resolve(id+".audio");}
    private boolean validFile(Map<String,Object> row) {
        try{Path file=path(row.get("id").toString());return !Files.isSymbolicLink(file) && Files.isRegularFile(file) && Files.size(file)==((Number)row.get("byte_size")).longValue() && PracticeCommands.hash(Files.readAllBytes(file)).equals(row.get("sha256"));}catch(Exception e){return false;}
    }
    @GetMapping("/api/v1/recordings")
    public Object list(@RequestParam String lessonId,@RequestParam String versionId,@RequestParam String sentenceId){
        c.context(lessonId,versionId,sentenceId);
        return Map.of("state",c.state(sentenceId,"speaking"),"recordings",c.jdbc.queryForList("SELECT r.id,r.mime_type AS mimeType,r.duration_ms AS durationMs,r.byte_size AS byteSize,r.status,r.client_created_at AS clientCreatedAt,r.created_at AS createdAt,(SELECT COUNT(*) FROM recording_observation o WHERE o.recording_id=r.id) AS playbackCount FROM personal_recording r WHERE r.lesson_id=? AND r.version_id=? AND r.sentence_id=? AND r.status<>'deleted' ORDER BY r.created_at DESC,r.id",lessonId,versionId,sentenceId));
    }
    @PostMapping("/api/v1/recordings")
    public JsonNode upload(@Valid @RequestBody Upload value) {
        c.context(value.lessonId,value.versionId,value.sentenceId);PracticeCommands.timestamp(value.createdAt);
        byte[] bytes;try{bytes=Base64.getDecoder().decode(value.audioBase64);}catch(Exception e){throw fail(422,"录音编码无效。");}
        if(bytes.length<32 || bytes.length>8388608)throw fail(413,"录音需为32字节至8MB。");
        boolean webm=value.mimeType.equals("audio/webm") || value.mimeType.equals("audio/webm;codecs=opus");
        boolean ogg=value.mimeType.equals("audio/ogg;codecs=opus") || value.mimeType.equals("audio/ogg");
        boolean mp4=value.mimeType.equals("audio/mp4");
        if(!(webm && bytes[0]==0x1a && bytes[1]==0x45 && bytes[2]==(byte)0xdf && bytes[3]==(byte)0xa3) && !(ogg && new String(bytes,0,4,java.nio.charset.StandardCharsets.US_ASCII).equals("OggS")) && !(mp4 && new String(bytes,4,4,java.nio.charset.StandardCharsets.US_ASCII).equals("ftyp")))throw fail(415,"录音容器与 MIME 不匹配或浏览器格式不受支持。");
        String hash=PracticeCommands.hash(bytes);
        // The file is durable before the DB commit; a crash can leave an orphan, never a false ready row.
        JsonNode receipt=c.command(value.eventId,"recording-upload",value,()->{
            if(!c.jdbc.queryForObject("SELECT recording_enabled FROM user_setting WHERE owner_key='local'",Boolean.class))throw fail(409,"录音功能已在设置中关闭；本机录音缓冲仍保留。");
            String id=UUID.randomUUID().toString();Path temp=null;
            try {
                temp=Files.createTempFile(root,"upload-",".part",PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rw-------")));
                try(var channel=java.nio.channels.FileChannel.open(temp,StandardOpenOption.WRITE)){var buffer=java.nio.ByteBuffer.wrap(bytes);while(buffer.hasRemaining())channel.write(buffer);channel.force(true);}
                Files.move(temp,path(id),StandardCopyOption.ATOMIC_MOVE);
            }catch(Exception e){throw fail(503,"录音文件无法保存；本机缓冲保留，请重试。");}
            c.jdbc.update("INSERT INTO personal_recording(id,lesson_id,version_id,sentence_id,event_id,mime_type,duration_ms,byte_size,sha256,status,client_created_at) VALUES (?,?,?,?,?,?,?,?,?,'pending',?)",id,value.lessonId,value.versionId,value.sentenceId,value.eventId,value.mimeType,value.durationMs,bytes.length,hash,value.createdAt);
            c.progress(value.sentenceId,"speaking","in_progress");return Map.of("id",id);
        });
        String id=receipt.path("id").asText();var row=row(id);
        // Replaying an old upload must never resurrect a deleted recording.
        if(!"deleted".equals(row.get("status"))){if(!validFile(row))throw fail(503,"已接收录音文件缺失，请保留本机缓冲并检查磁盘。");c.jdbc.update("UPDATE personal_recording SET status='ready' WHERE id=? AND status<>'deleted'",id);}
        return receipt;
    }
    private Map<String,Object> row(String id){path(id);var rows=c.jdbc.queryForList("SELECT * FROM personal_recording WHERE id=?",id);if(rows.isEmpty())throw fail(404,"录音不存在。");return rows.getFirst();}
    @GetMapping("/api/v1/recordings/{id}/audio")
    public ResponseEntity<byte[]> audio(@PathVariable String id) throws Exception {
        var row=row(id);if(!"ready".equals(row.get("status")) || !validFile(row))throw fail(404,"录音已删除或文件不可用。");
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(row.get("mime_type").toString())).header("Content-Disposition","inline; filename=recording.audio").body(Files.readAllBytes(path(id)));
    }
    @PostMapping("/api/v1/recordings/{id}/playbacks")
    public JsonNode playback(@PathVariable String id,@Valid @RequestBody Playback value){
        return c.command(value.eventId,"recording-playback:"+id,value,()->{
            path(id);var rows=c.jdbc.queryForList("SELECT * FROM personal_recording WHERE id=? FOR UPDATE",id);
            if(rows.isEmpty())throw fail(404,"录音不存在。");var row=rows.getFirst();
            c.context(value.lessonId,value.versionId,value.sentenceId);
            if(!value.sentenceId.equals(row.get("sentence_id")) || !value.versionId.equals(row.get("version_id")) || !"ready".equals(row.get("status")) || !validFile(row))throw fail(422,"本句没有可用录音。");
            if(!Set.of("replay_only","try_again","satisfied").contains(value.selfRating))throw fail(422,"自评选项无效。");
            if(value.observedMs<250 || value.observedMs>((Number)row.get("duration_ms")).intValue()+2000)throw fail(422,"需要本句真实回放观察。");
            c.jdbc.update("INSERT INTO recording_observation(event_id,recording_id,self_rating) VALUES (?,?,?)",value.eventId,id,value.selfRating);
            c.jdbc.update("INSERT INTO learning_evidence(id,event_id,recording_event_id) VALUES (?,?,?)",UUID.randomUUID().toString(),value.eventId,value.eventId);
            c.progress(value.sentenceId,"speaking","practiced");return Map.of("state","practiced","observation","client_reported_playback","selfRating",value.selfRating);
        });
    }
    @PostMapping("/api/v1/recordings/{id}/ratings")
    public JsonNode rating(@PathVariable String id,@Valid @RequestBody Rating value) {
        return c.command(value.eventId,"recording-rating:"+id,value,()->{
            var recording=row(id);c.context(value.lessonId,value.versionId,value.sentenceId);
            if(!value.sentenceId.equals(recording.get("sentence_id")) || !value.versionId.equals(recording.get("version_id")) || !"ready".equals(recording.get("status")))throw fail(422,"自评与本句录音不匹配。");
            if(!Set.of("try_again","satisfied").contains(value.selfRating))throw fail(422,"自评选项无效。");
            if(c.jdbc.queryForObject("SELECT COUNT(*) FROM recording_observation WHERE event_id=? AND recording_id=?",Integer.class,value.playbackEventId,id)!=1)throw fail(422,"请先实际回放本句录音。");
            // Immutable rating receipt refers to an existing playback; no extra playback/evidence row.
            return Map.of("recordingId",id,"playbackEventId",value.playbackEventId,"selfRating",value.selfRating,"ratingOnly",true);
        });
    }
    @PostMapping("/api/v1/recordings/{id}/delete")
    public JsonNode delete(@PathVariable String id,@Valid @RequestBody Delete value) throws Exception {
        if(!value.confirmed)throw fail(422,"删除需要明确确认。");
        JsonNode result=c.command(value.eventId,"recording-delete:"+id,value,()->{row(id);c.jdbc.update("UPDATE personal_recording SET status='deleted' WHERE id=?",id);return Map.of("deleted",true);});
        // Tombstone commits before unlink; retries complete an interrupted unlink.
        Files.deleteIfExists(path(id));return result;
    }
    public record Upload(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@NotBlank @Size(max=40) String createdAt,@NotBlank @Size(max=64) String mimeType,@Min(250) @Max(120000) int durationMs,@NotBlank @Size(max=11184812) String audioBase64){}
    public record Playback(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@Min(250) int observedMs,@NotBlank String selfRating){}
    public record Rating(@NotBlank @Size(max=36) String eventId,@NotBlank @Size(max=64) String lessonId,@NotBlank @Size(max=64) String versionId,@NotBlank @Size(max=64) String sentenceId,@NotBlank @Size(max=36) String playbackEventId,@NotBlank String selfRating){}
    public record Delete(@NotBlank @Size(max=36) String eventId,boolean confirmed){}
}
