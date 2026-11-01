package local.northstar.knowledge;

import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Objects;
import org.springframework.jdbc.core.JdbcOperations;
import tools.jackson.databind.json.JsonMapper;

/** Freezes the server-side knowledge relations of one attempt; never trusts client concept IDs. */
public final class KnowledgeSources {
    private KnowledgeSources() {}
    public static void record(JdbcOperations db,JsonMapper mapper,String attemptId,String eventId,
            String lesson,String version,String exerciseId,String sentenceId,boolean correct,String algorithmVersion) {
        var relations=db.queryForList("""
            SELECT ek.occurrence_id AS occurrenceId,ek.role,ek.concept_id AS conceptId,o.revision_id AS revisionId,
                   o.scope,o.paragraph_id AS paragraphId,o.sentence_id AS occurrenceSentenceId,
                   CAST(o.usage_json AS CHAR CHARACTER SET utf8mb4) AS usageJson,
                   c.kind,c.canonical_key AS canonicalKey,c.sense_key AS senseKey,r.revision_no AS revisionNo,
                   r.display_name AS displayName,r.explanation,r.reviewer,CAST(r.reviewed_at AS CHAR CHARACTER SET utf8mb4) AS reviewedAt
            FROM exercise_knowledge ek
            JOIN knowledge_occurrence o ON o.id=ek.occurrence_id AND o.version_id=ek.version_id AND o.concept_id=ek.concept_id
            JOIN knowledge_concept c ON c.id=ek.concept_id
            JOIN knowledge_concept_revision r ON r.id=o.revision_id AND r.concept_id=o.concept_id AND r.review_status='confirmed'
            WHERE ek.exercise_id=? AND ek.version_id=?
            ORDER BY ek.occurrence_id
            """,exerciseId,version);
        if(relations.isEmpty()) return;
        var sentences=db.queryForList("""
            SELECT es.sentence_id AS sentenceId,es.role,s.sequence_no AS sequence,s.text,s.paragraph_id AS paragraphId
            FROM exercise_sentence es JOIN sentence s ON s.id=es.sentence_id
            WHERE es.exercise_id=? AND es.version_id=? ORDER BY s.sequence_no,es.sentence_id
            """,exerciseId,version);
        for(var relation:relations) {
            var snapshot=new LinkedHashMap<String,Object>();
            snapshot.put("eventId",eventId);snapshot.put("lessonId",lesson);snapshot.put("versionId",version);
            snapshot.put("exerciseId",exerciseId);snapshot.put("attemptSentenceId",sentenceId);
            snapshot.put("correct",correct);snapshot.put("algorithmVersion",algorithmVersion);
            snapshot.put("role",relation.get("role").toString());
            var occurrence=new LinkedHashMap<String,Object>();
            occurrence.put("id",relation.get("occurrenceId").toString());occurrence.put("scope",relation.get("scope").toString());
            occurrence.put("paragraphId",Objects.toString(relation.get("paragraphId"),null));
            occurrence.put("sentenceId",Objects.toString(relation.get("occurrenceSentenceId"),null));
            try {occurrence.put("usage",mapper.readTree(relation.get("usageJson").toString()));}
            catch(Exception error) {throw new IllegalStateException("Occurrence usage JSON invalid",error);}
            snapshot.put("occurrence",occurrence);
            var concept=new LinkedHashMap<String,Object>();
            concept.put("id",relation.get("conceptId").toString());concept.put("kind",relation.get("kind").toString());
            concept.put("canonicalKey",relation.get("canonicalKey").toString());concept.put("senseKey",relation.get("senseKey").toString());
            concept.put("revisionNo",((Number)relation.get("revisionNo")).intValue());
            concept.put("displayName",relation.get("displayName").toString());concept.put("explanation",relation.get("explanation").toString());
            concept.put("reviewer",relation.get("reviewer").toString());
            concept.put("reviewedAt",Objects.toString(relation.get("reviewedAt"),null));
            snapshot.put("concept",concept);
            snapshot.put("sourceSentences",sentences);
            String json=mapper.writeValueAsString(snapshot);
            db.update("INSERT INTO attempt_knowledge(attempt_id,occurrence_id,exercise_id,version_id,concept_id,revision_id,sentence_id,role,source_json,source_sha256) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    attemptId,relation.get("occurrenceId"),exerciseId,version,relation.get("conceptId"),relation.get("revisionId"),
                    sentenceId,relation.get("role"),json,sha256(json));
        }
    }
    private static String sha256(String value) {
        try {return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));}
        catch(java.security.NoSuchAlgorithmException error) {throw new IllegalStateException(error);}
    }
}
