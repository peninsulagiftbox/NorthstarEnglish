CREATE TABLE import_entry (
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 package_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 expected_current_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 snapshot_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 state VARCHAR(24) NOT NULL CHECK(state IN ('applied','published')),
 applied_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 UNIQUE KEY uq_import_package(package_id),
 FOREIGN KEY(package_id) REFERENCES import_batch(package_id),
 FOREIGN KEY(version_id,lesson_id) REFERENCES lesson_version(id,lesson_id)
);
