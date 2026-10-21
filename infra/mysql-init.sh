#!/bin/bash
set -euo pipefail
# Only the entrypoint of this project's NEW volume executes this script.
[[ "$DB_PASSWORD" =~ ^[a-f0-9]{64}$ && "$DB_MIGRATION_PASSWORD" =~ ^[a-f0-9]{64}$ ]] || exit 1
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot <<SQL
CREATE DATABASE northstar_english CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'northstar_app'@'%' IDENTIFIED BY '$DB_PASSWORD';
CREATE USER 'northstar_migrator'@'%' IDENTIFIED BY '$DB_MIGRATION_PASSWORD';
GRANT SELECT ON northstar_english.* TO 'northstar_app'@'%';
GRANT SELECT ON northstar_phase01_test.* TO 'northstar_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON northstar_english.* TO 'northstar_migrator'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON northstar_phase01_test.* TO 'northstar_migrator'@'%';
CREATE TABLE northstar_english.project_identity (
  project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
  created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))
);
CREATE TABLE northstar_phase01_test.project_identity LIKE northstar_english.project_identity;
INSERT INTO northstar_english.project_identity VALUES ('northstar-english-local-v1', UTC_TIMESTAMP(3));
INSERT INTO northstar_phase01_test.project_identity VALUES ('northstar-english-local-v1', UTC_TIMESTAMP(3));
SQL
