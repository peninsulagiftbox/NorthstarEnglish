CREATE TABLE exercise_knowledge (
  exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  occurrence_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  concept_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  role VARCHAR(16) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_exercise_knowledge_role CHECK (role IN ('target','support')),
  PRIMARY KEY(exercise_id,occurrence_id),
  UNIQUE KEY uq_exercise_knowledge_context(exercise_id,occurrence_id,version_id,concept_id),
  FOREIGN KEY(exercise_id,version_id) REFERENCES exercise(id,version_id),
  FOREIGN KEY(occurrence_id,version_id,concept_id) REFERENCES knowledge_occurrence(id,version_id,concept_id)
);
