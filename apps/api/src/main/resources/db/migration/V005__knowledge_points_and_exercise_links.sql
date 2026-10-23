-- Preserve frozen content and existing dictation history; add reading links.
ALTER TABLE exercise DROP CHECK exercise_chk_1,
 ADD CONSTRAINT ck_exercise_kind CHECK(kind IN ('dictation','reading_choice'));
CREATE TABLE knowledge_point (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 term VARCHAR(100) NOT NULL, meaning VARCHAR(255) NOT NULL,
 usage_note VARCHAR(255) NOT NULL, example_text TEXT NOT NULL,
 UNIQUE KEY uq_knowledge_context(id,version_id,sentence_id),
 FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
 FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
CREATE TABLE vocabulary_favorite (
 knowledge_point_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 favorite BOOLEAN NOT NULL,
 updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 FOREIGN KEY(knowledge_point_id) REFERENCES knowledge_point(id)
);
CREATE TABLE reading_question (
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 knowledge_point_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 payload_json JSON NOT NULL,
 UNIQUE KEY uq_reading_context(exercise_id,version_id,sentence_id),
 FOREIGN KEY(exercise_id,version_id,sentence_id) REFERENCES exercise(id,version_id,sentence_id),
 FOREIGN KEY(knowledge_point_id,version_id,sentence_id) REFERENCES knowledge_point(id,version_id,sentence_id)
);
CREATE TABLE reading_option (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 UNIQUE KEY uq_reading_option(id,exercise_id),
 FOREIGN KEY(exercise_id) REFERENCES reading_question(exercise_id)
);
CREATE TABLE reading_answer (
 attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 option_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 FOREIGN KEY(attempt_id,version_id,sentence_id) REFERENCES exercise_attempt(id,version_id,sentence_id),
 FOREIGN KEY(exercise_id,version_id,sentence_id) REFERENCES reading_question(exercise_id,version_id,sentence_id),
 FOREIGN KEY(option_id,exercise_id) REFERENCES reading_option(id,exercise_id)
);
CREATE TABLE reading_progress (
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 current_state VARCHAR(24) NOT NULL CHECK(current_state IN ('not_started','in_progress','practiced','skipped','paused')),
 FOREIGN KEY(exercise_id) REFERENCES reading_question(exercise_id)
);
