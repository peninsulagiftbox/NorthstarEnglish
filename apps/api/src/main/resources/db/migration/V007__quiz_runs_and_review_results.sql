-- New immutable quiz targets; preserve existing attempts and review IDs.
ALTER TABLE exercise DROP CHECK ck_exercise_kind,
 DROP INDEX uq_exercise_target,
 ADD CONSTRAINT ck_exercise_kind CHECK(kind IN ('dictation','reading_choice','quiz_choice'));
CREATE TABLE quiz_question (
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 knowledge_point_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 payload_json JSON NOT NULL,
 FOREIGN KEY(exercise_id,version_id,sentence_id) REFERENCES exercise(id,version_id,sentence_id),
 FOREIGN KEY(knowledge_point_id,version_id,sentence_id) REFERENCES knowledge_point(id,version_id,sentence_id)
);
CREATE TABLE quiz_run (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 correct_count INT NOT NULL CHECK(correct_count BETWEEN 0 AND 3),
 submitted_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 UNIQUE KEY uq_quiz_context(id,version_id),
 FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
 FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id)
);
CREATE TABLE quiz_answer (
 run_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 option_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY(run_id,exercise_id),
 FOREIGN KEY(run_id,version_id) REFERENCES quiz_run(id,version_id),
 FOREIGN KEY(exercise_id,version_id,sentence_id) REFERENCES exercise(id,version_id,sentence_id),
 FOREIGN KEY(attempt_id,version_id,sentence_id) REFERENCES exercise_attempt(id,version_id,sentence_id)
);
CREATE TABLE quiz_progress (
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 current_state VARCHAR(24) NOT NULL CHECK(current_state IN ('not_started','in_progress','practiced','skipped','paused')),
 FOREIGN KEY(version_id) REFERENCES lesson_version(id)
);
ALTER TABLE review_item DROP INDEX sentence_id,
 ADD owner_key VARCHAR(16) NOT NULL DEFAULT 'local',
 ADD target_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD card_kind VARCHAR(24) NOT NULL DEFAULT 'dictation',
 ADD knowledge_point_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD due_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 ADD scheduler_version VARCHAR(24) NOT NULL DEFAULT 'simple_v1',
 ADD reps INT NOT NULL DEFAULT 0 CHECK(reps>=0),
 ADD row_version BIGINT NOT NULL DEFAULT 1,
 ADD FOREIGN KEY(knowledge_point_id,version_id,sentence_id) REFERENCES knowledge_point(id,version_id,sentence_id);
UPDATE review_item SET target_key=sentence_id;
ALTER TABLE review_item MODIFY target_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 ADD UNIQUE KEY uq_review_card(owner_key,version_id,target_key,card_kind),
 ADD INDEX ix_review_due(status,due_at,id);
-- Separate existing reading evidence from dictation without losing any source.
INSERT INTO review_item(id,sentence_id,version_id,target_key,card_kind,knowledge_point_id)
 SELECT DISTINCT CONCAT(q.knowledge_point_id,'-reading'),r.sentence_id,r.version_id,q.knowledge_point_id,'reading_choice',q.knowledge_point_id
 FROM review_source r JOIN exercise_attempt a ON a.id=r.attempt_id JOIN reading_question q ON q.exercise_id=a.exercise_id;
UPDATE review_source r JOIN exercise_attempt a ON a.id=r.attempt_id JOIN reading_question q ON q.exercise_id=a.exercise_id
 SET r.item_id=CONCAT(q.knowledge_point_id,'-reading');
DELETE r FROM review_item r LEFT JOIN review_source s ON s.item_id=r.id WHERE s.item_id IS NULL;
CREATE TABLE review_result (
 event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 item_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 rating VARCHAR(16) NOT NULL CHECK(rating IN ('again','good')),
 origin VARCHAR(24) NOT NULL DEFAULT 'self_rating' CHECK(origin='self_rating'),
 scheduler_version VARCHAR(24) NOT NULL DEFAULT 'simple_v1',
 previous_due_at DATETIME(3) NOT NULL,
 next_due_at DATETIME(3) NOT NULL,
 previous_row_version BIGINT NOT NULL,
 client_occurred_at VARCHAR(40) NOT NULL,
 recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
 FOREIGN KEY(item_id) REFERENCES review_item(id),
 UNIQUE KEY uq_review_result_version(item_id,previous_row_version)
);
