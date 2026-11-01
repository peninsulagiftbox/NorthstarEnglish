-- Frozen per-attempt knowledge sources; generated inside the attempt transaction, never from client input.
CREATE TABLE attempt_knowledge (
  attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  occurrence_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  revision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  role VARCHAR(16) NOT NULL,
  source_json JSON NOT NULL,
  source_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_attempt_knowledge_role CHECK (role IN ('target','support')),
  PRIMARY KEY(attempt_id,occurrence_id),
  UNIQUE KEY uq_attempt_knowledge_context(attempt_id,occurrence_id,exercise_id,version_id),
  FOREIGN KEY(attempt_id,exercise_id,version_id,sentence_id) REFERENCES exercise_attempt(id,exercise_id,version_id,sentence_id),
  FOREIGN KEY(exercise_id,occurrence_id,version_id,concept_id) REFERENCES exercise_knowledge(exercise_id,occurrence_id,version_id,concept_id)
);
-- Attempt snapshots are learning evidence; immutability is enforced by the database, not only by convention.
DELIMITER //
CREATE TRIGGER attempt_knowledge_no_update BEFORE UPDATE ON attempt_knowledge FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Attempt knowledge snapshots are immutable'; END//
CREATE TRIGGER attempt_knowledge_no_delete BEFORE DELETE ON attempt_knowledge FOR EACH ROW
BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Attempt knowledge snapshots are immutable'; END//
DELIMITER ;
