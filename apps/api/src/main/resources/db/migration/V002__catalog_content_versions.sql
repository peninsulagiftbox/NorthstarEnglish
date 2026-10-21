CREATE TABLE IF NOT EXISTS content_license (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('original', 'licensed')),
  source_ref VARCHAR(255) NOT NULL,
  review_status VARCHAR(24) NOT NULL CHECK (review_status IN ('pending_review','confirmed','rejected','expired')),
  details_json JSON NOT NULL,
  UNIQUE KEY uq_license_source (source_ref, source_type)
);
CREATE TABLE IF NOT EXISTS book (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  catalog_key VARCHAR(64) NOT NULL,
  sequence_no INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  edition_label VARCHAR(100) NOT NULL,
  availability VARCHAR(24) NOT NULL CHECK (availability = 'catalog_only'),
  declared_lesson_count INT NOT NULL CHECK (declared_lesson_count > 0),
  metadata_source VARCHAR(255) NOT NULL,
  UNIQUE KEY uq_book_edition (catalog_key, edition_label),
  UNIQUE KEY uq_book_sequence (edition_label, sequence_no)
);
CREATE TABLE IF NOT EXISTS lesson (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  slug VARCHAR(128) NOT NULL UNIQUE,
  kind VARCHAR(24) NOT NULL CHECK (kind IN ('original_demo','licensed')),
  availability VARCHAR(24) NOT NULL CHECK (availability IN ('draft','available','withdrawn')),
  book_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
  current_version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
  FOREIGN KEY (book_id) REFERENCES book(id)
);
CREATE TABLE IF NOT EXISTS lesson_version (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  version_no INT NOT NULL CHECK (version_no > 0),
  license_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  content_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  manifest_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  payload_json JSON NOT NULL,
  release_ready BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
  UNIQUE KEY uq_version (lesson_id, version_no),
  UNIQUE KEY uq_version_lesson (id, lesson_id),
  FOREIGN KEY (lesson_id) REFERENCES lesson(id),
  FOREIGN KEY (license_id) REFERENCES content_license(id)
);
-- MySQL DDL commits each statement. Permit resuming this migration after a
-- verified partial failure without dropping tables or changing stored content.
SET @current_fk_exists = (SELECT COUNT(*) FROM information_schema.table_constraints
  WHERE constraint_schema = DATABASE() AND table_name = 'lesson' AND constraint_name = 'fk_current_version');
SET @current_fk_sql = IF(@current_fk_exists = 0,
  'ALTER TABLE lesson ADD CONSTRAINT fk_current_version FOREIGN KEY (current_version_id, id) REFERENCES lesson_version(id, lesson_id)',
  'SELECT 1');
PREPARE northstar_current_fk FROM @current_fk_sql;
EXECUTE northstar_current_fk;
DEALLOCATE PREPARE northstar_current_fk;
CREATE TABLE IF NOT EXISTS audio_asset (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  lesson_version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  license_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_kind VARCHAR(24) NOT NULL CHECK (source_kind IN ('original_tts','licensed_audio')),
  storage_key VARCHAR(128) NOT NULL UNIQUE,
  mime_type VARCHAR(32) NOT NULL CHECK (mime_type = 'audio/mpeg'),
  byte_size INT NOT NULL CHECK (byte_size > 0),
  duration_ms INT NOT NULL CHECK (duration_ms > 0),
  sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  status VARCHAR(24) NOT NULL CHECK (status IN ('pending','ready','missing','withdrawn')),
  UNIQUE KEY uq_audio_version (id, lesson_version_id),
  FOREIGN KEY (lesson_version_id) REFERENCES lesson_version(id),
  FOREIGN KEY (license_id) REFERENCES content_license(id)
);
CREATE TABLE IF NOT EXISTS sentence (
  id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  lesson_version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  stable_key VARCHAR(64) NOT NULL,
  sequence_no INT NOT NULL,
  speaker VARCHAR(64) NOT NULL,
  text TEXT NOT NULL,
  translation TEXT NOT NULL,
  explanation TEXT NOT NULL,
  focus VARCHAR(255) NOT NULL,
  audio_asset_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  start_ms INT NOT NULL CHECK (start_ms = 0),
  end_ms INT NOT NULL,
  CONSTRAINT ck_sentence_interval CHECK (end_ms > start_ms),
  UNIQUE KEY uq_sentence_sequence (lesson_version_id, sequence_no),
  UNIQUE KEY uq_sentence_key (lesson_version_id, stable_key),
  UNIQUE KEY uq_sentence_version (id, lesson_version_id),
  UNIQUE KEY uq_sentence_audio (audio_asset_id),
  FOREIGN KEY (lesson_version_id, lesson_id) REFERENCES lesson_version(id, lesson_id),
  FOREIGN KEY (audio_asset_id, lesson_version_id) REFERENCES audio_asset(id, lesson_version_id)
);
