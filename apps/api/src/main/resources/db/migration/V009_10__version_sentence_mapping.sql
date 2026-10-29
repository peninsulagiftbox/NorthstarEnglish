CREATE TABLE version_sentence_map (
 id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY, lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 from_version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, to_version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 from_sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, to_sentence_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 relation VARCHAR(16) NULL, mapping_status VARCHAR(16) NOT NULL,
 mapping_group VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, reviewer VARCHAR(128) NOT NULL, confirmation_source VARCHAR(255) NOT NULL,
 reason VARCHAR(1000) NOT NULL, confirmed_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 CONSTRAINT ck_map_versions CHECK(from_version_id<>to_version_id),
 CONSTRAINT ck_map_target CHECK((mapping_status='confirmed' AND to_sentence_id IS NOT NULL AND relation IN ('equivalent','edited','split','merged')) OR (mapping_status='no_target' AND to_sentence_id IS NULL AND relation IS NULL)),
 CONSTRAINT ck_map_review CHECK(CHAR_LENGTH(TRIM(reviewer))>0 AND CHAR_LENGTH(TRIM(reason))>0 AND CHAR_LENGTH(TRIM(confirmation_source))>0),
 UNIQUE KEY uq_mapping_edge(from_version_id,to_version_id,from_sentence_id,to_sentence_id),
 FOREIGN KEY(from_version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
 FOREIGN KEY(to_version_id,lesson_id) REFERENCES lesson_version(id,lesson_id),
 FOREIGN KEY(from_sentence_id,from_version_id,lesson_id) REFERENCES sentence(id,lesson_version_id,lesson_id),
 FOREIGN KEY(to_sentence_id,to_version_id,lesson_id) REFERENCES sentence(id,lesson_version_id,lesson_id)
);
