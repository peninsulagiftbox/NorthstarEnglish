CREATE TABLE study_resume (
  owner_key VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  session_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  tab_key VARCHAR(16) NOT NULL,
  show_english BOOLEAN NOT NULL DEFAULT TRUE,
  show_translation BOOLEAN NOT NULL DEFAULT TRUE,
  row_version BIGINT NOT NULL DEFAULT 1,
  updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  CONSTRAINT ck_resume_owner CHECK (owner_key = 'local'),
  CONSTRAINT ck_resume_tab CHECK (tab_key IN ('text','dictation','vocabulary','speaking','writing','quiz')),
  CONSTRAINT ck_resume_version CHECK (row_version > 0),
  FOREIGN KEY (version_id, lesson_id) REFERENCES lesson_version(id, lesson_id),
  FOREIGN KEY (sentence_id, version_id) REFERENCES sentence(id, lesson_version_id)
);
