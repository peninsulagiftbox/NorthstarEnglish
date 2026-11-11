CREATE TABLE import_batch (
 package_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 package_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 raw_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 manifest_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 plan_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
 target_identity VARCHAR(255) NOT NULL,
 schema_version VARCHAR(32) NOT NULL,
 package_json JSON NOT NULL,
 manifest_json JSON NOT NULL,
 plan_json JSON NOT NULL,
 state VARCHAR(24) NOT NULL CHECK(state IN ('validated','staged','materialized','applied','published','partial_failed')),
 error_code VARCHAR(128) NULL,
 created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
 updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))
);
