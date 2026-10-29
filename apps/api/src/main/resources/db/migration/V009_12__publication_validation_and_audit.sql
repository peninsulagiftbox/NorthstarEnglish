CREATE TABLE content_validation (
 version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY, snapshot_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 content_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 manifest_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 algorithm VARCHAR(40) NOT NULL CHECK(algorithm='northstar.relational.v1'),
 reviewer VARCHAR(128) NOT NULL, validated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 FOREIGN KEY(version_id) REFERENCES lesson_version(id)
);
-- Request IDs are retained even for unknown lessons/versions; do not FK untrusted request values.
CREATE TABLE publication_audit (
 operation_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 request_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 action VARCHAR(16) NOT NULL CHECK(action IN ('publish','withdraw')),
 lesson_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, target_version_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 expected_current_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL, actual_current_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 content_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 result_code VARCHAR(64) NOT NULL, response_json JSON NOT NULL,
 recorded_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))
);
