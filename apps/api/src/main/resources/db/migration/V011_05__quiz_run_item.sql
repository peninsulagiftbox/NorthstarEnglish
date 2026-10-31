CREATE TABLE quiz_run_item (
 run_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 set_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 set_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ordinal INT NOT NULL CHECK(ordinal BETWEEN 1 AND 100),
 question_json JSON NOT NULL,
 attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 option_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY(run_id,exercise_id),
 UNIQUE KEY uq_run_ordinal(run_id,ordinal),
 FOREIGN KEY(run_id,version_id) REFERENCES quiz_run(id,version_id),
 FOREIGN KEY(set_id,exercise_id,version_id,sentence_id) REFERENCES exercise_set_item(set_id,exercise_id,version_id,sentence_id),
 FOREIGN KEY(run_id,exercise_id,attempt_id,version_id,sentence_id,option_id) REFERENCES quiz_answer(run_id,exercise_id,attempt_id,version_id,sentence_id,option_id),
 FOREIGN KEY(attempt_id,exercise_id,version_id,sentence_id) REFERENCES exercise_attempt(id,exercise_id,version_id,sentence_id)
);
