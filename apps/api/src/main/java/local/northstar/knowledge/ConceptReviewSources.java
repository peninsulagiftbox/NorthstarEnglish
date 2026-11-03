package local.northstar.knowledge;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcOperations;

/** Appends wrong-answer evidence to concept cards; only frozen target relations from failed attempts qualify. */
public final class ConceptReviewSources {
    private ConceptReviewSources() {}
    public static void record(JdbcOperations db,String attemptId) {
        var targets=db.queryForList("""
            SELECT ak.occurrence_id AS occurrenceId,ak.exercise_id AS exerciseId,ak.version_id AS versionId,ak.concept_id AS conceptId
            FROM attempt_knowledge ak JOIN exercise_attempt a ON a.id=ak.attempt_id
            WHERE ak.attempt_id=? AND ak.role='target' AND a.correct=FALSE
            ORDER BY ak.occurrence_id
            """,attemptId);
        for(var target:targets) {
            String concept=target.get("conceptId").toString();
            // The upsert converges concurrent creators on one card; the locking read sees the committed
            // winner even under REPEATABLE READ, where this transaction's earlier snapshot cannot.
            String fresh=UUID.randomUUID().toString();
            db.update("INSERT INTO concept_review_card(id,concept_id,prompt_kind,protocol_version) VALUES (?,?,'meaning_recall','concept_review_v1') ON DUPLICATE KEY UPDATE id=id",fresh,concept);
            String cardId=db.queryForObject("SELECT id FROM concept_review_card WHERE owner_key='local' AND concept_id=? AND prompt_kind='meaning_recall' AND protocol_version='concept_review_v1' FOR UPDATE",String.class,concept);
            db.update("INSERT INTO concept_review_source(card_id,attempt_id,occurrence_id,exercise_id,version_id,concept_id) VALUES (?,?,?,?,?,?)",
                    cardId,attemptId,target.get("occurrenceId"),target.get("exerciseId"),target.get("versionId"),concept);
        }
    }
}
