#!/usr/bin/env python3
"""Create and operate only this campaign's new labelled MySQL containers."""
import json
import os
from pathlib import Path
import secrets
import socket
import shutil
import subprocess
import sys
import time
import phase10e

r = phase10e.runner
STATE = r.STATE / "database"
LABEL = "northstar-phase10e-20261105"


def docker(*args, input=None):
    return subprocess.run(["docker", *args], input=input, capture_output=True, check=True).stdout


def prepare(role):
    directory = STATE / role
    directory.mkdir(parents=True, exist_ok=True)
    state = directory / "state.json"
    if state.exists():
        return verify(role)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    passwords = {name: secrets.token_hex(32) for name in ["root", "app", "migrator", "importer"]}
    credentials = directory / "credentials.json"
    with os.fdopen(os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        json.dump(passwords, output)
    envfile = directory / "mysql.env"
    with os.fdopen(os.open(envfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        output.write("MYSQL_ROOT_PASSWORD=" + passwords["root"] + "\n")
    name = LABEL + "-" + role
    identifier = docker("run", "-d", "--name", name, "--label", "local.northstar.campaign=" + LABEL,
        "--env-file", str(envfile), "-p", f"127.0.0.1:{port}:3306",
        "-v", name + "-data:/var/lib/mysql", "mysql:8.4.9").decode().strip()
    data = {"container": identifier, "name": name, "port": port, "uuid": None}
    state.write_text(json.dumps(data))
    for _ in range(120):
        try:
            sql(role, "SELECT 1", bootstrap=True)
            break
        except subprocess.CalledProcessError:
            time.sleep(.5)
    for schema in ["northstar_english", "northstar_phase01_test"]:
        sql(role, f"CREATE DATABASE {schema} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
            f"CREATE TABLE {schema}.project_identity(project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3)));"
            f"INSERT INTO {schema}.project_identity(project_key) VALUES ('northstar-english-local-v1');", bootstrap=True)
    for account in ["app", "migrator", "importer"]:
        sql(role, f"CREATE USER 'northstar_{account}'@'%' IDENTIFIED BY '{passwords[account]}';", bootstrap=True)
    sql(role, "SET GLOBAL log_bin_trust_function_creators=1;"
        "GRANT ALL ON northstar_english.* TO 'northstar_migrator'@'%';"
        "GRANT ALL ON northstar_phase01_test.* TO 'northstar_migrator'@'%';", bootstrap=True)
    data["uuid"] = sql(role, "SELECT @@server_uuid", bootstrap=True).decode().strip()
    state.write_text(json.dumps(data, indent=2))
    (directory / "media").mkdir(exist_ok=True)
    r.OUT.mkdir(parents=True, exist_ok=True)
    (r.OUT / (role + "-identity.json")).write_text(json.dumps(data, indent=2))
    return data


def verify(role):
    data = json.loads((STATE / role / "state.json").read_text())
    actual = json.loads(docker("inspect", data["container"]))[0]
    assert actual["Config"]["Labels"]["local.northstar.campaign"] == LABEL
    assert actual["HostConfig"]["PortBindings"]["3306/tcp"] == [{"HostIp": "127.0.0.1", "HostPort": str(data["port"])}]
    assert actual["Name"] == "/" + data["name"]
    assert data["uuid"] == sql(role, "SELECT @@server_uuid", bootstrap=True).decode().strip()
    return data


def sql(role, query, bootstrap=False, schema=None):
    data = json.loads((STATE / role / "state.json").read_text())
    if not bootstrap:
        verify(role)
    args = ["exec", "-i", data["container"], "sh", "-c",
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --batch --raw --skip-column-names'
            + (" -D" + schema if schema else "")]
    return docker(*args, input=query.encode())


def environment(role, schema="northstar_phase01_test"):
    data = verify(role)
    passwords = json.loads((STATE / role / "credentials.json").read_text())
    env = r.environment()
    env.update(MYSQL_PORT=str(data["port"]), DB_NAME=schema,
        DB_PASSWORD=passwords["app"], DB_MIGRATION_PASSWORD=passwords["migrator"],
        DB_IMPORT_PASSWORD=passwords["importer"], NORTHSTAR_IMPORT_DB_UUID=data["uuid"],
        NORTHSTAR_EXPECTED_DB_UUID=data["uuid"], NORTHSTAR_DB_TEST="1",
        NORTHSTAR_CONTENT_ROOT=str(STATE / role / "media"),
        NORTHSTAR_IMPORT_MEDIA_ROOT=str(STATE / role / "media"),
        NORTHSTAR_IMPORT_RUNTIME=str(r.COPY / "apps/api/target"),
        NORTHSTAR_IMPORT_SAMPLE_ROOT=str(r.STATE / "samples"),
        NORTHSTAR_TEST_AUDIO=str(r.ROOT / ".local/phase10b2/audio/original-test-tone.mp3"),
        NORTHSTAR_AUDIO_FIXTURES=str(r.ROOT / ".local/phase10c1/audio/manifest.json"),
        NORTHSTAR_RECORDING_ROOT=str(STATE / role / "recordings"),
        API_PORT="18185", WEB_PORT="13185")
    return env


def grant(role, schemas=None):
    sql(role, "REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'northstar_app'@'%';"
              "REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'northstar_importer'@'%';")
    tables = ["content_license", "book", "lesson", "lesson_version", "paragraph", "sentence",
              "audio_asset", "sentence_identity", "paragraph_identity", "audio_alignment", "lesson_audio",
              "knowledge_point", "exercise", "reading_question", "reading_option", "quiz_question",
              "knowledge_concept", "knowledge_concept_revision", "knowledge_occurrence", "legacy_knowledge_link",
              "exercise_sentence", "exercise_knowledge", "knowledge_projection", "exercise_set", "exercise_set_item",
              "content_validation", "publication_audit", "import_batch", "import_entry"]
    for schema in schemas or ["northstar_english", "northstar_phase01_test"]:
        present = set(sql(role, f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema}'").decode().splitlines())
        sql(role, f"GRANT SELECT ON {schema}.* TO 'northstar_app'@'%'; REVOKE ALL PRIVILEGES ON {schema}.* FROM 'northstar_app'@'%'; GRANT SELECT ON {schema}.* TO 'northstar_app'@'%';")
        for table in ("study_resume", "user_setting", "command_receipt", "study_stage", "exercise_draft",
                      "review_item", "vocabulary_favorite", "reading_progress", "writing_draft", "personal_recording",
                      "practice_progress", "quiz_progress", "concept_review_card"):
            if table in present:
                sql(role, f"GRANT INSERT,UPDATE ON {schema}.{table} TO 'northstar_app'@'%';")
        for table in ("exercise_attempt", "learning_evidence", "study_event", "review_source", "reading_answer",
                      "writing_revision", "recording_observation", "quiz_run", "quiz_answer", "quiz_run_item",
                      "review_result", "attempt_knowledge", "concept_review_source", "concept_review_result",
                      "knowledge_concept", "knowledge_concept_revision", "knowledge_occurrence",
                      "exercise_sentence", "exercise_knowledge", "legacy_knowledge_link"):
            if table in present:
                sql(role, f"GRANT INSERT ON {schema}.{table} TO 'northstar_app'@'%';")
        if "knowledge_projection" in present:
            sql(role, f"GRANT INSERT,UPDATE ON {schema}.knowledge_projection TO 'northstar_app'@'%';")
        if "import_mutex" in present:
            sql(role, f"GRANT UPDATE ON {schema}.import_mutex TO 'northstar_importer'@'%';")
        sql(role, f"GRANT SELECT ON {schema}.* TO 'northstar_importer'@'%';")
        for table in tables:
            if table not in present:
                continue
            sql(role, f"GRANT INSERT ON {schema}.{table} TO 'northstar_importer'@'%';")
        for table, columns in {"lesson": "current_version_id,availability",
                               "lesson_version": "publication_state,published_at",
                               "knowledge_projection": "frozen,frozen_at",
                               "exercise_set": "set_hash,frozen",
                               "import_batch": "state,error_code,updated_at",
                               "import_entry": "state"}.items():
            if table in present:
                sql(role, f"GRANT UPDATE({columns}) ON {schema}.{table} TO 'northstar_importer'@'%';")


if __name__ == "__main__":
    action, role = sys.argv[1:3]
    if action == "prepare":
        print(json.dumps(prepare(role)))
    elif action == "run":
        r.record(sys.argv[3], sys.argv[4:], env=environment(role), cwd=r.COPY, timeout=1200)
    elif action == "grant":
        grant(role)
    elif action == "grant-restore":
        import re
        assert re.fullmatch(r"northstar_restore_[0-9]{14}", sys.argv[3])
        grant(role, [sys.argv[3]])
    elif action == "migrate":
        env = environment(role, sys.argv[3] if len(sys.argv) > 3 else "northstar_phase01_test")
        target = r.COPY / "apps/api/target"
        classpath = str(target / "classes") + os.pathsep + (target / "import-classpath.txt").read_text().strip()
        r.record("migrate-" + role, [str(Path(env["JAVA_HOME"]) / "bin/java"), "-cp", classpath,
                 str(r.ROOT / "scripts/phase10e/Migrate.java"), *sys.argv[4:]],
                 env=env, cwd=r.COPY, timeout=600)
    elif action == "seed":
        env = environment(role, sys.argv[3] if len(sys.argv) > 3 else "northstar_phase01_test")
        media = STATE / role / "media"
        shutil.copytree(r.ROOT / "content", media, dirs_exist_ok=True)
        r.record("seed-" + role, [str(Path(env["JAVA_HOME"]) / "bin/java"), "-jar",
                 str(r.COPY / "apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"),
                 "--spring.main.web-application-type=none", "--northstar.initialize-content=true",
                 "--northstar.content-root=" + str(media), "--northstar.recording-root=" + env["NORTHSTAR_RECORDING_ROOT"]],
                 env=env, cwd=r.COPY, timeout=180)
    else:
        raise SystemExit("prepare ROLE | run ROLE LABEL COMMAND... | grant ROLE")
