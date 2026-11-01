package local.northstar.knowledge;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcOperations;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Offline reviewed registration: java -jar app.jar --northstar.register-knowledge=file.json
 * --spring.main.web-application-type=none. The runtime app account has no write access to these tables.
 */
@Component
public class KnowledgeRegistrationCli implements ApplicationRunner {
    private final JdbcOperations db;
    private final TransactionTemplate tx;
    private final JsonMapper mapper=JsonMapper.builder().build();
    public KnowledgeRegistrationCli(JdbcOperations db,PlatformTransactionManager manager) {this.db=db;this.tx=new TransactionTemplate(manager);}
    @Override public void run(ApplicationArguments args) throws Exception {
        List<String> values=args.getOptionValues("northstar.register-knowledge");
        if(values==null || values.isEmpty()) return;
        var result=register(mapper.readTree(Files.readString(Path.of(values.getFirst()),StandardCharsets.UTF_8)));
        System.out.println(mapper.writeValueAsString(result));
    }
    public Map<String,Object> register(JsonNode request) {
        String reviewer=request.path("reviewer").asText("").trim();
        if(reviewer.isEmpty() || reviewer.length()>128) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_REVIEWER_REQUIRED","登记需要非空审校人。");
        String version=request.path("versionId").asText("");
        if(!version.matches("[A-Za-z0-9_-]{1,64}")) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_VERSION_INVALID","内容版本标识无效。");
        return tx.execute(status -> {
            var versions=db.queryForList("SELECT lesson_id,publication_state FROM lesson_version WHERE id=?",version);
            if(versions.size()!=1) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_VERSION_NOT_FOUND","内容版本不存在。");
            String lesson=versions.getFirst().get("lesson_id").toString();
            var projections=db.queryForList("SELECT frozen FROM knowledge_projection WHERE version_id=?",version);
            if(!projections.isEmpty()) return Map.<String,Object>of("code",((Boolean)projections.getFirst().get("frozen"))?"ALREADY_FROZEN":"PROJECTION_EXISTS","versionId",version);
            int concepts=0,revisions=0,occurrences=0,links=0,sentences=0,knowledge=0;
            for(var entry:request.path("concepts")) {
                String id=identifier(entry.path("id").asText(""),"concept");
                String kind=entry.path("kind").asText("");
                if(!KnowledgeConcepts.KINDS.contains(kind)) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_KIND_INVALID","知识类别无效。");
                String key=KnowledgeConcepts.canonicalKey(entry.path("canonicalKey").asText(null));
                String sense=ascii(entry.path("senseKey").asText(""),"senseKey",64);
                var existing=db.queryForList("SELECT kind,canonical_key,sense_key FROM knowledge_concept WHERE id=?",id);
                if(existing.size()>1 || (existing.size()==1 && (!existing.getFirst().get("kind").equals(kind) || !existing.getFirst().get("canonical_key").equals(key) || !existing.getFirst().get("sense_key").equals(sense))))
                    throw new KnowledgeConcepts.Failure(409,"KNOWLEDGE_CONCEPT_CONFLICT","概念身份与已登记记录不一致。");
                if(existing.isEmpty()) {db.update("INSERT INTO knowledge_concept(id,kind,canonical_key,sense_key) VALUES (?,?,?,?)",id,kind,key,sense);concepts++;}
                for(var revision:entry.path("revisions")) {
                    if(!"confirmed".equals(revision.path("reviewStatus").asText("")))
                        throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_REVISION_UNCONFIRMED","只有人工确认的义项修订可以登记。");
                    Instant reviewedAt=parseInstant(revision.path("reviewedAt").asText(""));
                    String revisionId=revision.hasNonNull("id")?identifier(revision.path("id").asText(""),"revision"):UUID.randomUUID().toString();
                    int no=revision.hasNonNull("revisionNo")?revision.path("revisionNo").asInt():db.queryForObject("SELECT COALESCE(MAX(revision_no),0)+1 FROM knowledge_concept_revision WHERE concept_id=?",Integer.class,id);
                    db.update("INSERT INTO knowledge_concept_revision(id,concept_id,revision_no,display_name,explanation,source_ref,reviewer,review_status,reviewed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                            revisionId,id,no,text(revision.path("displayName").asText(""),255,"display_name"),revision.path("explanation").asText(""),
                            text(revision.path("sourceRef").asText(reviewer+" reviewed offline registration"),255,"source_ref"),reviewer,"confirmed",java.sql.Timestamp.from(reviewedAt));
                    revisions++;
                }
            }
            for(var entry:request.path("occurrences")) {
                String id=entry.hasNonNull("id")?identifier(entry.path("id").asText(""),"occurrence"):UUID.randomUUID().toString();
                String revisionId=identifier(entry.path("revisionId").asText(""),"revisionId");
                var revisionRows=db.queryForList("SELECT concept_id,review_status FROM knowledge_concept_revision WHERE id=?",revisionId);
                if(revisionRows.size()!=1 || !"confirmed".equals(revisionRows.getFirst().get("review_status")))
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_REVISION_UNCONFIRMED","出现位置必须引用已确认的义项修订。");
                String conceptId=revisionRows.getFirst().get("concept_id").toString();
                String scope=entry.path("scope").asText("");
                String paragraph=nullIfBlank(entry.path("paragraphId").asText(null)),sentence=nullIfBlank(entry.path("sentenceId").asText(null));
                boolean lessonScope=scope.equals("lesson"),paragraphScope=scope.equals("paragraph"),sentenceScope=scope.equals("sentence");
                if(!lessonScope && !paragraphScope && !sentenceScope) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_SCOPE_INVALID","出现位置范围无效。");
                if(lessonScope && (paragraph!=null || sentence!=null)) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_SCOPE_INVALID","课程级出现不能绑定段落或句子。");
                if(paragraphScope && (paragraph==null || sentence!=null)) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_SCOPE_INVALID","段落级出现必须只绑定段落。");
                if(sentenceScope && sentence==null) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_SCOPE_INVALID","句子级出现必须绑定句子。");
                if(!entry.path("usage").isObject()) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_USAGE_INVALID","出现位置用法必须是JSON对象。");
                if(paragraph!=null && db.queryForList("SELECT id FROM paragraph WHERE id=? AND version_id=?",paragraph,version).isEmpty())
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","段落不属于当前版本。");
                if(sentence!=null) {
                    var rows=db.queryForList("SELECT paragraph_id FROM sentence WHERE id=? AND lesson_id=? AND lesson_version_id=?",sentence,lesson,version);
                    if(rows.isEmpty()) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","句子不属于当前版本。");
                    String sentenceParagraph=Objects.toString(rows.getFirst().get("paragraph_id"),null);
                    if(paragraph==null) paragraph=sentenceParagraph;
                    else if(!paragraph.equals(sentenceParagraph)) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","句子不属于指定段落。");
                }
                db.update("INSERT INTO knowledge_occurrence(id,concept_id,revision_id,lesson_id,version_id,scope,paragraph_id,sentence_id,usage_json) VALUES (?,?,?,?,?,?,?,?,?)",
                        id,conceptId,revisionId,lesson,version,scope,paragraph,sentence,mapper.writeValueAsString(entry.path("usage")));
                occurrences++;
            }
            for(var entry:request.path("legacyLinks")) {
                String point=identifier(entry.path("knowledgePointId").asText(""),"knowledgePointId");
                String occurrenceId=identifier(entry.path("occurrenceId").asText(""),"occurrenceId");
                String basis=entry.path("mappingBasis").asText("");
                if(!Set.of("manual_review","synthetic_fixture_reviewed").contains(basis))
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_BASIS_INVALID","映射必须具有明确审校依据。");
                var points=db.queryForList("SELECT sentence_id FROM knowledge_point WHERE id=? AND lesson_id=? AND version_id=?",point,lesson,version);
                if(points.isEmpty()) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","旧知识点不属于当前版本。");
                String pointSentence=points.getFirst().get("sentence_id").toString();
                var occurrencesRow=db.queryForList("SELECT concept_id,sentence_id,scope FROM knowledge_occurrence WHERE id=? AND version_id=?",occurrenceId,version);
                if(occurrencesRow.isEmpty() || !"sentence".equals(occurrencesRow.getFirst().get("scope")) || !pointSentence.equals(occurrencesRow.getFirst().get("sentence_id")))
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","旧知识点只能映射到同句的句子级出现。");
                db.update("INSERT INTO legacy_knowledge_link(knowledge_point_id,version_id,sentence_id,occurrence_id,concept_id,mapping_basis,reviewer) VALUES (?,?,?,?,?,?,?)",
                        point,version,pointSentence,occurrenceId,occurrencesRow.getFirst().get("concept_id"),basis,reviewer);
                links++;
            }
            for(var entry:request.path("exerciseSentences")) {
                String exercise=identifier(entry.path("exerciseId").asText(""),"exerciseId");
                String sentence=identifier(entry.path("sentenceId").asText(""),"sentenceId");
                String role=entry.path("role").asText("");
                if(!Set.of("primary","supporting").contains(role)) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_ROLE_INVALID","练习来源角色无效。");
                if(db.queryForList("SELECT id FROM exercise WHERE id=? AND version_id=?",exercise,version).isEmpty()
                        || db.queryForList("SELECT id FROM sentence WHERE id=? AND lesson_version_id=?",sentence,version).isEmpty())
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","练习来源句不属于当前版本。");
                db.update("INSERT INTO exercise_sentence(exercise_id,version_id,sentence_id,role) VALUES (?,?,?,?)",exercise,version,sentence,role);
                sentences++;
            }
            for(var entry:request.path("exerciseKnowledge")) {
                String exercise=identifier(entry.path("exerciseId").asText(""),"exerciseId");
                String occurrenceId=identifier(entry.path("occurrenceId").asText(""),"occurrenceId");
                String role=entry.path("role").asText("");
                if(!Set.of("target","support").contains(role)) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_ROLE_INVALID","练习知识角色无效。");
                var exercises=db.queryForList("SELECT lesson_id FROM exercise WHERE id=? AND version_id=?",exercise,version);
                var occurrenceRows=db.queryForList("SELECT concept_id,lesson_id,scope,sentence_id,paragraph_id FROM knowledge_occurrence WHERE id=? AND version_id=?",occurrenceId,version);
                if(exercises.isEmpty() || occurrenceRows.isEmpty() || !exercises.getFirst().get("lesson_id").equals(occurrenceRows.getFirst().get("lesson_id")))
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","练习知识关联不属于当前版本或课程。");
                if("sentence".equals(occurrenceRows.getFirst().get("scope")) && db.queryForList("SELECT role FROM exercise_sentence WHERE exercise_id=? AND version_id=? AND sentence_id=?",exercise,version,occurrenceRows.getFirst().get("sentence_id")).isEmpty())
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","句子级知识出现必须来自本题的来源句。");
                if("paragraph".equals(occurrenceRows.getFirst().get("scope"))) {
                    var sourceRows=db.queryForList("SELECT s.paragraph_id FROM exercise_sentence es JOIN sentence s ON s.id=es.sentence_id WHERE es.exercise_id=? AND es.version_id=?",exercise,version);
                    if(sourceRows.isEmpty() || sourceRows.stream().anyMatch(row->!occurrenceRows.getFirst().get("paragraph_id").equals(row.get("paragraph_id"))))
                        throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_CONTEXT_MISMATCH","段落级知识出现必须覆盖本题全部来源句所在段落。");
                }
                db.update("INSERT INTO exercise_knowledge(exercise_id,occurrence_id,version_id,concept_id,role) VALUES (?,?,?,?,?)",exercise,occurrenceId,version,occurrenceRows.getFirst().get("concept_id"),role);
                knowledge++;
            }
            for(var row:db.queryForList("SELECT exercise_id FROM exercise_sentence WHERE version_id=? GROUP BY exercise_id",version)) {
                var primary=db.queryForList("SELECT sentence_id FROM exercise_sentence WHERE version_id=? AND exercise_id=? AND role='primary'",version,row.get("exercise_id"));
                String anchor=db.queryForObject("SELECT sentence_id FROM exercise WHERE id=?",String.class,row.get("exercise_id"));
                if(primary.size()!=1 || !anchor.equals(primary.getFirst().get("sentence_id")))
                    throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_PRIMARY_INVALID","每道练习必须恰好一个主锚点来源句。");
            }
            if(db.queryForObject("SELECT COUNT(*) FROM knowledge_concept_revision r JOIN knowledge_occurrence o ON o.revision_id=r.id WHERE o.version_id=? AND r.review_status<>'confirmed'",Integer.class,version)!=0)
                throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_REVISION_UNCONFIRMED","存在未确认义项的出现位置。");
            int relationCount=db.queryForObject("SELECT (SELECT COUNT(*) FROM knowledge_occurrence WHERE version_id=?) + (SELECT COUNT(*) FROM legacy_knowledge_link WHERE version_id=?) + (SELECT COUNT(*) FROM exercise_sentence WHERE version_id=?) + (SELECT COUNT(*) FROM exercise_knowledge WHERE version_id=?)",Integer.class,version,version,version,version);
            if(relationCount>0) {
                String digest=relationsHash(db,version);
                db.update("INSERT INTO knowledge_projection(version_id,protocol_version,relations_sha256,registered_by,frozen) VALUES (?,'knowledge-registration-v1',?,?,FALSE)",version,digest,reviewer);
                db.update("UPDATE knowledge_projection SET frozen=TRUE,frozen_at=UTC_TIMESTAMP(3) WHERE version_id=?",version);
                if(!digest.equals(relationsHash(db,version))) throw new IllegalStateException("Knowledge relations changed during freeze");
            }
            var result=new LinkedHashMap<String,Object>();
            result.put("code","REGISTERED");result.put("versionId",version);result.put("lessonId",lesson);
            result.put("concepts",concepts);result.put("revisions",revisions);result.put("occurrences",occurrences);
            result.put("legacyLinks",links);result.put("exerciseSentences",sentences);result.put("exerciseKnowledge",knowledge);
            return result;
        });
    }
    /** Canonical relations digest shared with publication validation. */
    public static String relationsHash(JdbcOperations db,String version) {
        JsonMapper mapper=JsonMapper.builder().build();
        var payload=new LinkedHashMap<String,Object>();
        payload.put("revisions",db.queryForList("SELECT r.id,r.concept_id,r.revision_no,r.display_name,r.explanation,r.review_status FROM knowledge_concept_revision r WHERE EXISTS (SELECT 1 FROM knowledge_occurrence o WHERE o.revision_id=r.id AND o.version_id=?) ORDER BY r.id",version));
        payload.put("occurrences",db.queryForList("SELECT id,concept_id,revision_id,scope,paragraph_id,sentence_id,CAST(usage_json AS CHAR CHARACTER SET utf8mb4) AS usage_json FROM knowledge_occurrence WHERE version_id=? ORDER BY id",version));
        payload.put("legacyLinks",db.queryForList("SELECT knowledge_point_id,occurrence_id,concept_id,mapping_basis FROM legacy_knowledge_link WHERE version_id=? ORDER BY knowledge_point_id",version));
        payload.put("exerciseSentences",db.queryForList("SELECT exercise_id,sentence_id,role FROM exercise_sentence WHERE version_id=? ORDER BY exercise_id,sentence_id",version));
        payload.put("exerciseKnowledge",db.queryForList("SELECT exercise_id,occurrence_id,role FROM exercise_knowledge WHERE version_id=? ORDER BY exercise_id,occurrence_id",version));
        try {return sha256(mapper.writeValueAsString(payload).getBytes(StandardCharsets.UTF_8));}
        catch(Exception error) {throw new IllegalStateException(error);}
    }
    public static boolean projectionFrozen(JdbcOperations db,String version) {
        var rows=db.queryForList("SELECT frozen FROM knowledge_projection WHERE version_id=?",version);
        return rows.size()==1 && Boolean.TRUE.equals(rows.getFirst().get("frozen"));
    }
    private static String sha256(byte[] value) {
        try {return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(value));}
        catch(java.security.NoSuchAlgorithmException error) {throw new IllegalStateException(error);}
    }
    private static String identifier(String value,String field) {
        if(value.isEmpty() || value.length()>64 || !value.matches("[A-Za-z0-9_-]+")) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_ID_INVALID","标识无效: "+field);
        return value;
    }
    private static String ascii(String value,String field,int limit) {
        if(value.isEmpty() || value.length()>limit || !value.matches("[A-Za-z0-9_.:-]+")) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_SENSE_INVALID","义项标识无效: "+field);
        return value;
    }
    private static String text(String value,int limit,String field) {
        if(value==null || value.isBlank() || value.length()>limit) throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_TEXT_INVALID","文本无效: "+field);
        return value;
    }
    private static Instant parseInstant(String value) {
        if(value==null || value.isBlank()) return Instant.now();
        try {return Instant.parse(value);}catch(Exception error) {throw new KnowledgeConcepts.Failure(422,"KNOWLEDGE_TIME_INVALID","审校时间必须是ISO-8601。");}
    }
    private static String nullIfBlank(String value) {return value==null || value.isBlank()?null:value;}
}
