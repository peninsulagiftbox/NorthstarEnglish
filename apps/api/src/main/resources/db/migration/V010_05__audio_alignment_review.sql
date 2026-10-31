CREATE TABLE audio_alignment (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 asset_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 audio_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 transcript_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 timebase VARCHAR(24) NOT NULL CHECK (timebase='asset_milliseconds'),
 tool VARCHAR(128) NOT NULL,
 tool_version VARCHAR(64) NOT NULL,
 parameters_json JSON NOT NULL,
 status VARCHAR(24) NOT NULL CHECK (status IN ('auto_draft','needs_review','verified','rejected')),
 reviewer VARCHAR(128) NULL,
 reviewed_at DATETIME(3) NULL,
 UNIQUE KEY uq_alignment_asset (asset_id,version_id),
 CONSTRAINT ck_alignment_review CHECK (status<>'verified' OR (reviewer IS NOT NULL AND CHAR_LENGTH(TRIM(reviewer))>0 AND reviewed_at IS NOT NULL)),
 FOREIGN KEY (asset_id,version_id) REFERENCES audio_asset(id,lesson_version_id)
);
