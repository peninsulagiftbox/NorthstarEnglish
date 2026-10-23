package local.northstar.practice;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.function.Supplier;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@Service
public class PracticeCommands {
    final JdbcOperations jdbc;
    final JsonMapper mapper=JsonMapper.builder().build();
    private final TransactionTemplate tx;
    public PracticeCommands(JdbcOperations jdbc,PlatformTransactionManager manager) {this.jdbc=jdbc;tx=new TransactionTemplate(manager);}
    public static ResponseStatusException fail(int code,String message) {return new ResponseStatusException(HttpStatus.valueOf(code),message);}
    public void context(String lesson,String version,String sentence) {
        if(jdbc.queryForObject("SELECT COUNT(*) FROM sentence s JOIN lesson l ON l.id=s.lesson_id WHERE s.lesson_id=? AND s.lesson_version_id=? AND s.id=? AND l.availability='available'",Integer.class,lesson,version,sentence)!=1) throw fail(422,"课次、版本和目标句不匹配。");
    }
    public void progress(String target,String kind,String state) {
        jdbc.update("INSERT INTO practice_progress(target_key,kind,current_state) VALUES (?,?,?) ON DUPLICATE KEY UPDATE current_state=?",target,kind,state,state);
    }
    public String state(String target,String kind) {
        var rows=jdbc.queryForList("SELECT current_state FROM practice_progress WHERE target_key=? AND kind=?",target,kind);
        return rows.isEmpty()?"not_started":rows.getFirst().get("current_state").toString();
    }
    public JsonNode command(String event,String operation,Object body,Supplier<Object> work) {
        try {UUID.fromString(event);} catch(Exception e) {throw fail(400,"事件标识必须为 UUID。");}
        String hash=hash((operation+":"+mapper.writeValueAsString(body)).getBytes(StandardCharsets.UTF_8));
        JsonNode old=replay(event,hash); if(old!=null) return old;
        try {return tx.execute(status -> {
            jdbc.update("INSERT INTO command_receipt(event_id,payload_hash) VALUES (?,?)",event,hash);
            JsonNode result=mapper.valueToTree(work.get());
            jdbc.update("UPDATE command_receipt SET response_json=? WHERE event_id=?",mapper.writeValueAsString(result),event);
            return result;
        });} catch(DuplicateKeyException e) {old=replay(event,hash);if(old!=null)return old;throw e;}
    }
    private JsonNode replay(String event,String hash) {
        var rows=jdbc.queryForList("SELECT payload_hash,response_json FROM command_receipt WHERE event_id=?",event);
        if(rows.isEmpty())return null;
        if(!hash.equals(rows.getFirst().get("payload_hash")))throw fail(409,"相同事件不能提交不同内容。");
        return mapper.readTree(rows.getFirst().get("response_json").toString());
    }
    public static String hash(byte[] bytes) {try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));}catch(Exception e){throw new IllegalStateException(e);}}
    public static void timestamp(String time) {try{Instant.parse(time);}catch(Exception e){throw fail(400,"时间必须为 ISO-8601 格式。");}}
}
