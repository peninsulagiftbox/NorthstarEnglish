CREATE TABLE writing_task (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 prompt TEXT NOT NULL,
 UNIQUE KEY uq_writing_context(id,version_id),
 FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id)
);
CREATE TABLE writing_source (
 task_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 PRIMARY KEY(task_id,sentence_id),
 FOREIGN KEY(task_id,version_id) REFERENCES writing_task(id,version_id),
 FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id)
);
CREATE TABLE writing_draft (
 task_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 raw_text TEXT NOT NULL,
 row_version BIGINT NOT NULL DEFAULT 1,
 next_revision INT NOT NULL DEFAULT 1,
 updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 FOREIGN KEY(task_id) REFERENCES writing_task(id)
);
CREATE TABLE writing_revision (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 task_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 version_no INT NOT NULL,
 raw_text TEXT NOT NULL,
 source_draft_version BIGINT NOT NULL,
 parent_revision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL,
 created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 UNIQUE KEY uq_revision_number(task_id,version_no),
 UNIQUE KEY uq_revision_parent(id,task_id),
 FOREIGN KEY(task_id) REFERENCES writing_task(id),
 FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
 FOREIGN KEY(parent_revision_id,task_id) REFERENCES writing_revision(id,task_id)
);
CREATE TABLE personal_recording (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
 mime_type VARCHAR(64) NOT NULL,
 duration_ms INT NOT NULL CHECK(duration_ms BETWEEN 250 AND 120000),
 byte_size INT NOT NULL CHECK(byte_size BETWEEN 32 AND 8388608),
 sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 status VARCHAR(16) NOT NULL CHECK(status IN ('pending','ready','missing','deleted')),
 client_created_at VARCHAR(40) NOT NULL,
 created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
 FOREIGN KEY(sentence_id,version_id) REFERENCES sentence(id,lesson_version_id),
 FOREIGN KEY(event_id) REFERENCES command_receipt(event_id)
);
CREATE TABLE practice_progress (
 target_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 kind VARCHAR(16) NOT NULL CHECK(kind IN ('speaking','writing')),
 current_state VARCHAR(24) NOT NULL CHECK(current_state IN ('not_started','in_progress','practiced','skipped','paused')),
 PRIMARY KEY(target_key,kind)
);
CREATE TABLE recording_observation (
 event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 recording_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 self_rating VARCHAR(24) NOT NULL CHECK(self_rating IN ('replay_only','try_again','satisfied')),
 created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 FOREIGN KEY(recording_id) REFERENCES personal_recording(id),
 FOREIGN KEY(event_id) REFERENCES command_receipt(event_id)
);
ALTER TABLE learning_evidence MODIFY attempt_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD recording_event_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL UNIQUE,
 ADD writing_revision_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL UNIQUE,
 ADD FOREIGN KEY(recording_event_id) REFERENCES recording_observation(event_id),
 ADD FOREIGN KEY(writing_revision_id) REFERENCES writing_revision(id),
 ADD FOREIGN KEY(event_id) REFERENCES command_receipt(event_id),
 ADD CONSTRAINT ck_evidence_one_source CHECK((attempt_id IS NOT NULL)+(recording_event_id IS NOT NULL)+(writing_revision_id IS NOT NULL)=1);
