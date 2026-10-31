ALTER TABLE quiz_run
 ADD total_count INT NULL,
 ADD submitted_count INT NULL,
 ADD set_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD set_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
 ADD exposure_status VARCHAR(16) NULL,
 ADD measurement_policy_version VARCHAR(32) NULL;
