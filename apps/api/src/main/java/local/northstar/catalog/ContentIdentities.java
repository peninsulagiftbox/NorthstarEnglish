package local.northstar.catalog;

import java.util.*;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.json.JsonMapper;

/** Explicit registries: physical IDs and stable identities are never inferred from text or position. */
public final class ContentIdentities {
    private ContentIdentities() {}
    public static String initializeDemo(JdbcOperations db,String kind,String physical) {
        try(var stream=ContentIdentities.class.getResourceAsStream("/catalog/demo-identities.json")) {
            for(var row:JsonMapper.builder().build().readTree(Objects.requireNonNull(stream)).path("records")) {
                if(row.path("type").asText().equals(kind) && row.path("physicalId").asText().equals(physical)) {
                    String id=row.path("identityId").asText();
                    db.update("INSERT INTO "+kind+"_identity(id,lesson_id,registry_key) VALUES (?,'demo-01',?)",id,row.path("registryKey").asText());
                    return id;
                }
            }
        } catch(java.io.IOException e) { throw new IllegalStateException("Identity registry unavailable"); }
        throw new IllegalArgumentException("Unregistered Demo record");
    }
    public record Edge(String from,String to) {}
    /** One complete, reviewed group per transaction; mappings never write learning tables. */
    public static void confirm(JdbcOperations db,TransactionTemplate tx,String lesson,String fromVersion,String toVersion,
            String relation,String group,String reviewer,String source,String reason,List<Edge> edges) {
        if(!Set.of("equivalent","edited","split","merged","no_target").contains(relation) || fromVersion.equals(toVersion)
                || group==null || !group.matches("[A-Za-z0-9_-]{1,64}") || reviewer==null || reviewer.isBlank()
                || source==null || source.isBlank() || reason==null || reason.isBlank() || edges.isEmpty()) throw new IllegalArgumentException("Invalid reviewed mapping");
        var from=new HashSet<String>();var to=new HashSet<String>();var distinct=new HashSet<Edge>();
        for(var edge:edges) {
            if(edge.from()==null || !distinct.add(edge) || (!relation.equals("no_target") && edge.to()==null)) throw new IllegalArgumentException("Invalid mapping edge");
            from.add(edge.from());if(edge.to()!=null)to.add(edge.to());
        }
        boolean valid=switch(relation) {
            case "equivalent","edited" -> from.size()==1 && to.size()==1 && edges.size()==1;
            case "split" -> from.size()==1 && to.size()>1;
            case "merged" -> from.size()>1 && to.size()==1;
            default -> from.size()==1 && to.isEmpty() && edges.size()==1;
        };
        if(!valid) throw new IllegalArgumentException("Invalid mapping cardinality");
        tx.executeWithoutResult(status->{
            db.queryForList("SELECT id FROM lesson WHERE id=? FOR UPDATE",lesson);
            if(db.queryForObject("SELECT COUNT(*) FROM version_sentence_map WHERE mapping_group=?",Integer.class,group)!=0)throw new IllegalArgumentException("Mapping group already frozen");
            for(var edge:edges) {
                if(db.queryForObject("SELECT COUNT(*) FROM version_sentence_map WHERE lesson_id=? AND from_version_id=? AND to_version_id=? AND (from_sentence_id=? OR to_sentence_id=?)",Integer.class,lesson,fromVersion,toVersion,edge.from(),edge.to())!=0)throw new IllegalArgumentException("Mapping already reviewed");
                if(relation.equals("equivalent")) {
                    var rows=db.queryForList("SELECT s.text,s.start_ms,s.end_ms,a.sha256 FROM sentence s JOIN audio_asset a ON a.id=s.audio_asset_id WHERE s.id IN (?,?) AND s.lesson_id=?",edge.from(),edge.to(),lesson);
                    if(rows.size()!=2 || !rows.get(0).equals(rows.get(1)))throw new IllegalArgumentException("Changed content/audio cannot be equivalent");
                }
            }
            for(var edge:edges) db.update("INSERT INTO version_sentence_map(id,lesson_id,from_version_id,to_version_id,from_sentence_id,to_sentence_id,relation,mapping_status,mapping_group,reviewer,confirmation_source,reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",UUID.randomUUID().toString(),lesson,fromVersion,toVersion,edge.from(),edge.to(),relation.equals("no_target")?null:relation,relation.equals("no_target")?"no_target":"confirmed",group,reviewer,source,reason);
        });
    }
}
