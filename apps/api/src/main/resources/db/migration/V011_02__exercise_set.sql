CREATE TABLE exercise_set (
 id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 purpose VARCHAR(24) NOT NULL CHECK(purpose='practice'),
 protocol_version VARCHAR(32) NOT NULL CHECK(protocol_version='quiz_choice_v1'),
 context_group_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 set_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 frozen BOOLEAN NOT NULL DEFAULT FALSE,
 snapshot_origin VARCHAR(32) NOT NULL CHECK(snapshot_origin IN ('legacy_reconstructed','version_content')),
 UNIQUE KEY uq_set_version(id,version_id),
 UNIQUE KEY uq_default_quiz(version_id,purpose),
 CHECK(NOT frozen OR set_hash IS NOT NULL),
 FOREIGN KEY(version_id) REFERENCES lesson_version(id)
);
