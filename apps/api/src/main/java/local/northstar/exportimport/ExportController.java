package local.northstar.exportimport;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import local.northstar.config.DatabaseGuard;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Logical snapshot. Binary recordings and unsynced browser buffers are explicitly separate. */
@RestController
public class ExportController {
    private final JdbcTemplate db;
    private final JsonMapper json=JsonMapper.builder().build();
    private static final Set<String> CONTENT=Set.of("book","lesson","lesson_version","paragraph","sentence","audio_asset","content_license","exercise","knowledge_point","reading_question","reading_option","writing_task","writing_source","quiz_question");
    public ExportController(JdbcTemplate db){this.db=db;}
    private String hash(String value){try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
    private ResponseStatusException invalid(){return new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,"数据包格式、版本、归属或内容基线不匹配；未导入任何数据。");}
    private Map<String,Object> tables(){
        var result=new TreeMap<String,Object>();
        for(String table:db.queryForList("SELECT table_name FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' ORDER BY table_name",String.class)){
            if(!table.matches("[a-z_]+"))throw new IllegalStateException("Unsupported table");
            var columns=db.queryForList("SELECT column_name FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=? ORDER BY ordinal_position",String.class,table);
            var keys=db.queryForList("SELECT column_name FROM information_schema.key_column_usage WHERE table_schema=DATABASE() AND table_name=? AND constraint_name='PRIMARY' ORDER BY ordinal_position",String.class,table);
            if(keys.isEmpty())throw new IllegalStateException("Snapshot requires primary keys");
            var rows=db.query("SELECT * FROM `"+table+"` ORDER BY "+String.join(",",keys.stream().map(k->"`"+k+"`").toList()),(rs,n)->{
                var row=new ArrayList<String>();for(int i=1;i<=columns.size();i++)row.add(rs.getString(i));return row;
            });
            result.put(table,Map.of("columns",columns,"rows",rows));
        }
        return result;
    }
    private List<String> migrationSignature(JsonNode table) {
        var columns=new ArrayList<String>();for(var c:table.path("columns"))columns.add(c.asText());
        var result=new ArrayList<String>();
        for(var row:table.path("rows")) {
            var signature=new ArrayList<String>();
            for(String key:List.of("version","type","script","checksum","success"))signature.add(row.path(columns.indexOf(key)).toString());
            result.add(signature.toString());
        }
        Collections.sort(result);return result;
    }
    @GetMapping("/api/v1/data/export")
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,String> export(){
        String schema=db.queryForObject("SELECT version FROM flyway_schema_history WHERE success=1 ORDER BY installed_rank DESC LIMIT 1",String.class);
        var payload=new LinkedHashMap<String,Object>();
        payload.put("project",DatabaseGuard.PROJECT);payload.put("owner","local");payload.put("schemaVersion",schema);payload.put("exportedAt",java.time.Instant.now().toString());
        payload.put("mediaIncluded",false);payload.put("browserBuffersIncluded",false);payload.put("tables",tables());
        String raw=json.writeValueAsString(payload);return Map.of("format","northstar.snapshot.v1","sha256",hash(raw),"payloadJson",raw);
    }
    @PostMapping("/api/v1/data/import-preview")
    @Transactional(readOnly=true,isolation=Isolation.REPEATABLE_READ)
    public Map<String,Object> preview(@RequestBody JsonNode envelope){
        if(envelope.size()!=3 || !envelope.path("format").asText().equals("northstar.snapshot.v1") || !envelope.path("payloadJson").isString() || envelope.path("payloadJson").asText().length()>32*1024*1024)throw invalid();
        String raw=envelope.path("payloadJson").asText();if(!hash(raw).equals(envelope.path("sha256").asText()))throw invalid();
        JsonNode payload;try{payload=json.readTree(raw);}catch(Exception e){throw invalid();}
        if(payload.size()!=7 || !payload.path("project").asText().equals(DatabaseGuard.PROJECT) || !payload.path("owner").asText().equals("local") || !payload.path("mediaIncluded").isBoolean() || payload.path("mediaIncluded").asBoolean() || payload.path("browserBuffersIncluded").asBoolean() || !payload.path("browserBuffersIncluded").isBoolean())throw invalid();
        try{java.time.Instant.parse(payload.path("exportedAt").asText());}catch(Exception e){throw invalid();}
        String schema=db.queryForObject("SELECT version FROM flyway_schema_history WHERE success=1 ORDER BY installed_rank DESC LIMIT 1",String.class);
        if(!schema.equals(payload.path("schemaVersion").asText()))throw invalid();
        JsonNode baseline=json.valueToTree(tables()),incoming=payload.path("tables");
        if(!incoming.isObject() || !incoming.propertyNames().equals(baseline.propertyNames()))throw invalid();
        var counts=new TreeMap<String,Integer>();
        for(String table:baseline.propertyNames()){
            JsonNode data=incoming.path(table);if(data.size()!=2 || !data.path("columns").equals(baseline.path(table).path("columns")) || !data.path("rows").isArray() || data.path("rows").size()>100000)throw invalid();
            int width=data.path("columns").size();for(var row:data.path("rows")){if(!row.isArray() || row.size()!=width)throw invalid();for(var cell:row)if(!cell.isNull() && !cell.isString())throw invalid();}
            if(CONTENT.contains(table) && !data.equals(baseline.path(table)))throw invalid();
            if(table.equals("flyway_schema_history") && !migrationSignature(data).equals(migrationSignature(baseline.path(table))))throw invalid();
            if(table.equals("project_identity") && (data.path("rows").size()!=1 || !data.path("rows").path(0).path(0).asText().equals(DatabaseGuard.PROJECT)))throw invalid();
            if(table.equals("user_setting") && (data.path("rows").size()!=1 || !data.path("rows").path(0).path(0).asText().equals("local")))throw invalid();
            for(int i=0;i<width;i++) {
                String column=data.path("columns").path(i).asText();
                for(var row:data.path("rows")) {
                    var cell=row.path(i);if(cell.isNull())continue;
                    if(column.equals("owner_key") && !cell.asText().equals("local"))throw invalid();
                    if(column.equals("project_key") && !cell.asText().equals(DatabaseGuard.PROJECT))throw invalid();
                    if(column.equals("event_id") || (table.equals("personal_recording") && column.equals("id"))) {
                        try{if(!UUID.fromString(cell.asText()).toString().equals(cell.asText()))throw invalid();}catch(IllegalArgumentException e){throw invalid();}
                    }
                }
            }
            counts.put(table,data.path("rows").size());
        }
        return Map.of("valid",true,"sha256",envelope.path("sha256").asText(),"tableCounts",counts,"mode","new_isolated_database_only","mediaIncluded",false,"warning","仅预检通过；外键与业务约束在新隔离库恢复时验证。现库不会被覆盖。浏览器未同步草稿与录音二进制不在 JSON 内。");
    }
}
