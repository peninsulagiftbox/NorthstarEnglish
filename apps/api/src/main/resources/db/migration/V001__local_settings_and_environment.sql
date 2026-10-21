CREATE TABLE user_setting (
    owner_key VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai',
    default_speed DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    show_translation BOOLEAN NOT NULL DEFAULT TRUE,
    show_hints BOOLEAN NOT NULL DEFAULT TRUE,
    shortcut_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    recording_retention VARCHAR(16) NOT NULL DEFAULT 'manual',
    row_version BIGINT NOT NULL DEFAULT 0,
    created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
    updated_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)),
    CONSTRAINT fk_setting_project FOREIGN KEY (project_key) REFERENCES project_identity(project_key),
    CONSTRAINT ck_local_owner CHECK (owner_key = 'local'),
    CONSTRAINT ck_speed CHECK (default_speed IN (0.75, 1.00, 1.25, 1.50)),
    CONSTRAINT ck_retention CHECK (recording_retention IN ('manual')),
    CONSTRAINT ck_row_version CHECK (row_version >= 0)
);

INSERT INTO user_setting (owner_key, project_key) VALUES ('local', 'northstar-english-local-v1');
