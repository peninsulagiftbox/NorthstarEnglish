-- The five-column key turns source-to-card concept equality into a database rule, not a service check.
ALTER TABLE attempt_knowledge
  ADD UNIQUE KEY uq_attempt_knowledge_card_source(attempt_id,occurrence_id,exercise_id,version_id,concept_id);
CREATE TABLE concept_review_source (
  card_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  occurrence_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  PRIMARY KEY(card_id,attempt_id,occurrence_id),
  FOREIGN KEY(card_id,concept_id) REFERENCES concept_review_card(id,concept_id),
  FOREIGN KEY(attempt_id,occurrence_id,exercise_id,version_id,concept_id)
    REFERENCES attempt_knowledge(attempt_id,occurrence_id,exercise_id,version_id,concept_id)
);
