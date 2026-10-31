CREATE TABLE lesson_audio (
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 asset_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 UNIQUE KEY uq_lesson_main_audio (asset_id,version_id),
 FOREIGN KEY (version_id) REFERENCES lesson_version(id),
 FOREIGN KEY (asset_id,version_id) REFERENCES audio_asset(id,lesson_version_id)
);
