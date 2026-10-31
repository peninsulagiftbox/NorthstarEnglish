CREATE TABLE exercise_set_item (
 set_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 knowledge_point_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ordinal INT NOT NULL CHECK(ordinal BETWEEN 1 AND 100),
 question_json JSON NOT NULL,
 item_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY(set_id,exercise_id),
 UNIQUE KEY uq_set_ordinal(set_id,ordinal),
 UNIQUE KEY uq_set_item_context(set_id,exercise_id,version_id,sentence_id),
 FOREIGN KEY(set_id,version_id) REFERENCES exercise_set(id,version_id),
 FOREIGN KEY(exercise_id,version_id,sentence_id,knowledge_point_id) REFERENCES quiz_question(exercise_id,version_id,sentence_id,knowledge_point_id)
);
