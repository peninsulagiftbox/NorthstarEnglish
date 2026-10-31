ALTER TABLE quiz_run
 MODIFY total_count INT NOT NULL,
 MODIFY submitted_count INT NOT NULL,
 MODIFY set_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 MODIFY set_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 MODIFY exposure_status VARCHAR(16) NOT NULL,
 MODIFY measurement_policy_version VARCHAR(32) NOT NULL,
 ADD CONSTRAINT ck_quiz_exposure CHECK(exposure_status='unknown'),
 ADD FOREIGN KEY(set_id,version_id) REFERENCES exercise_set(id,version_id);
ALTER TABLE quiz_answer ADD FOREIGN KEY(attempt_id,exercise_id,version_id,sentence_id) REFERENCES exercise_attempt(id,exercise_id,version_id,sentence_id);
