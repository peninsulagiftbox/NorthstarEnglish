CREATE TABLE exercise (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  kind VARCHAR(24) NOT NULL CHECK (kind='dictation'),
  algorithm_version VARCHAR(32) NOT NULL DEFAULT 'english_token_v1',
  UNIQUE KEY uq_exercise_context(id,version_id,sentence_id),
  UNIQUE KEY uq_exercise_target(version_id,sentence_id,kind),
  FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
  FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
INSERT INTO exercise(id,lesson_id,version_id,sentence_id,kind)
 SELECT CONCAT(id,'-dictation'),lesson_id,lesson_version_id,id,'dictation' FROM sentence;
CREATE TABLE command_receipt (
  event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  payload_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  response_json JSON NULL,
  recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))
);
CREATE TABLE exercise_attempt (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  exercise_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  raw_text TEXT NOT NULL,
  correct BOOLEAN NOT NULL,
  answer_exposed BOOLEAN NOT NULL,
  algorithm_version VARCHAR(32) NOT NULL,
  result_json JSON NOT NULL,
  client_occurred_at VARCHAR(40) NOT NULL,
  recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  UNIQUE KEY uq_attempt_event(id,event_id),
  UNIQUE KEY uq_attempt_target(id,version_id,sentence_id),
  FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
  FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
  FOREIGN KEY(exercise_id,version_id,sentence_id) REFERENCES exercise(id,version_id,sentence_id)
);
CREATE TABLE learning_evidence (
  id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  FOREIGN KEY(attempt_id,event_id) REFERENCES exercise_attempt(id,event_id)
);
CREATE TABLE study_event (
  event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  action VARCHAR(24) NOT NULL CHECK(action IN ('start','skip','pause')),
  client_occurred_at VARCHAR(40) NOT NULL,
  recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
  FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
  FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
CREATE TABLE study_stage (
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  current_state VARCHAR(24) NOT NULL CHECK(current_state IN ('not_started','in_progress','practiced','skipped','paused')),
  practice_count INT NOT NULL DEFAULT 0 CHECK(practice_count>=0),
  FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
CREATE TABLE exercise_draft (
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  raw_text TEXT NOT NULL,
  row_version BIGINT NOT NULL DEFAULT 1 CHECK(row_version>0),
  updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
  FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
CREATE TABLE review_item (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending' CHECK(status='pending'),
  UNIQUE KEY uq_review_target(id,version_id,sentence_id),
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
CREATE TABLE review_source (
  attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  item_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  reason VARCHAR(64) NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  FOREIGN KEY(attempt_id,version_id,sentence_id) REFERENCES exercise_attempt(id,version_id,sentence_id),
  FOREIGN KEY(item_id,version_id,sentence_id) REFERENCES review_item(id,version_id,sentence_id)
);
ALTER TABLE study_resume
 ADD COLUMN playing_sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD COLUMN position_ms INT NOT NULL DEFAULT 0 CHECK(position_ms>=0),
 ADD CONSTRAINT fk_resume_playing FOREIGN KEY(playing_sentence_id,version_id) REFERENCES sentence(id,lesson_version_id);
