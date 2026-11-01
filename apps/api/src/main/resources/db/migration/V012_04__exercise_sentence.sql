ALTER TABLE exercise
 ADD UNIQUE KEY uq_exercise_version(id,version_id);
CREATE TABLE exercise_sentence (
  exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  role VARCHAR(16) NOT NULL,
  primary_guard CHAR(64) CHARACTER SET ascii COLLATE ascii_bin
    GENERATED ALWAYS AS (CASE WHEN role='primary' THEN exercise_id ELSE NULL END) STORED,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_exercise_sentence_role CHECK (role IN ('primary','supporting')),
  PRIMARY KEY(exercise_id,sentence_id),
  UNIQUE KEY uq_exercise_sentence_context(exercise_id,version_id,sentence_id),
  UNIQUE KEY uq_exercise_sentence_primary(primary_guard),
 FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
