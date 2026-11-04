#!/usr/bin/env python3
"""D01-M03.a: kill real Flyway between the two V012.02 DDL statements on a disposable target."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from run import q, OUT, PRIVATE, ROOT

FAULT_OUT = OUT / os.environ.get("R7_DDL_EVIDENCE", "fault_ddl")
FAULT_PRIVATE = PRIVATE / os.environ.get("R7_DDL_DIR", "fault-ddl")
NAME = os.environ.get("R7_DDL_CONTAINER", "northstar-qa-final-r7-fault-ddl-20261104")
TABLES = ("lesson", "lesson_version", "sentence", "exercise_attempt",
          "personal_recording", "flyway_schema_history")
BASE_ENV = q.env


def configure(target=None):
    q.OUT = FAULT_OUT
    q.OUT.mkdir(exist_ok=True)
    q.PRIVATE = FAULT_PRIVATE
    q.PRIVATE.mkdir(exist_ok=True)
    q.NAME = NAME
    q.API_PORT = 8217
    q.WEB_PORT = 3217
    q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
    q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
    q.env = (lambda: dict(BASE_ENV(), SPRING_FLYWAY_TARGET=target)) if target else BASE_ENV


def probe(query):
    """Direct root probe; polling must not journal every sample."""
    completed = subprocess.run([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(q.identity()["port"]),
                                "-uroot", "-N", "--batch", "--raw"], input="SELECT @@server_uuid;USE " + q.SCHEMA + ";" + query,
                               capture_output=True, text=True, env=dict(os.environ, MYSQL_PWD=q.credentials()["root"]))
    assert completed.returncode == 0, completed.stderr[-300:]
    first, _, body = completed.stdout.partition("\n")
    assert first == q.identity()["uuid"]
    return body.rstrip("\n")


def rows():
    return {name: q.sql("SELECT * FROM " + name + " ORDER BY 1", label="ddl-" + name)
            for name in TABLES}


def hashes(values):
    return {key: hashlib.sha256(value.encode()).hexdigest() for key, value in values.items()}


def create():
    configure("012.01")
    shutil.copy2(OUT / "qa-r7-final-candidate.sha256", FAULT_OUT / "qa-final-candidate-manifest.sha256")
    q.create()
    history = q.sql("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank",
                    label="ddl-baseline-history")
    assert history.splitlines()[-1] == "012.01\t1", history
    dump = FAULT_PRIVATE / "baseline-before-fault.sql"
    with dump.open("xb") as output:
        completed = subprocess.run([q.DOCKER, "exec", q.identity()["containerId"], "sh", "-c",
                                    'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot '
                                    "--single-transaction --routines --triggers --events "
                                    "--no-tablespaces --set-gtid-purged=OFF " + q.SCHEMA],
                                   stdout=output, stderr=subprocess.PIPE,
                                   env=dict(os.environ, MYSQL_ROOT_PASSWORD=q.credentials()["root"]))
    assert completed.returncode == 0 and dump.stat().st_size > 0, completed.stderr[-300:]
    (FAULT_OUT / "pre-fault-backup.json").write_text(json.dumps(
        {"sha256": q.sha(dump), "databaseUuid": q.identity()["uuid"], "rowsSha256": hashes(rows())},
        indent=2) + "\n")
    print(json.dumps({"status": "BASELINE", "uuid": q.identity()["uuid"],
                      "historyTail": history.splitlines()[-1]}))


def inject():
    configure("012.02")
    before = hashes(rows())
    blocker = subprocess.Popen([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(q.identity()["port"]),
                                "-uroot", "-N", "-e", "USE " + q.SCHEMA + ";"
                                "LOCK TABLES knowledge_concept WRITE; SELECT SLEEP(240); UNLOCK TABLES;"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               env=dict(os.environ, MYSQL_PWD=q.credentials()["root"]))
    log = FAULT_PRIVATE / "inject.log"
    probes = []
    session_id = None
    java = subprocess.Popen([q.JAVA, "-jar", q.JAR, "--spring.main.web-application-type=none",
                             "--northstar.initialize-content=false"], env=q.env(), cwd=q.SOURCE,
                            stdout=log.open("xb"), stderr=subprocess.STDOUT)
    killed = False
    for _ in range(24000):
        if java.poll() is not None:
            break
        listing = probe("SHOW FULL PROCESSLIST")
        waiting = [line for line in listing.splitlines()
                   if "CREATE TABLE knowledge_occurrence" in line and "metadata lock" in line]
        probes.append(waiting[0].split("\t")[0] if waiting else "0")
        if waiting:
            session_id = waiting[0].split("\t")[0]
            probe("KILL " + session_id)
            java.kill()
            killed = True
            break
        time.sleep(.005)
    try:
        blocker.kill()
    finally:
        blocker.wait()
    java.wait()
    assert killed and java.returncode != 0, (killed, java.returncode, log.read_text(errors="replace")[-500:])
    occurrence = probe("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='" + q.SCHEMA +
                       "' AND table_name='knowledge_occurrence'")
    history = probe("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank")
    assert occurrence == "0" and "012.02" not in history
    (FAULT_OUT / "m03a-probe-samples.json").write_text(json.dumps(
        {"pollCount": len(probes), "detections": sum(1 for item in probes if item != "0"),
         "killedSessionId": session_id,
         "firstDetectionSample": next((i for i, item in enumerate(probes) if item != "0"), None)},
        indent=2) + "\n")
    assert before == hashes(rows())
    result = {"status": "PASS", "migration": "012.02", "statement1": "ALTER TABLE sentence ADD UNIQUE KEY uq_sentence_paragraph",
              "statement1Committed": True, "statement2": "CREATE TABLE knowledge_occurrence",
              "statement2Committed": False, "statement2KilledOnServer": session_id,
              "historyRegistered": False, "processStop": "server-side KILL then client SIGKILL",
              "javaExitCode": java.returncode, "injectLog": "inject.log", "injectLogSha256": q.sha(log),
              "databaseUuid": q.identity()["uuid"], "oldRowsUnchanged": True,
              "faultTargetPreserved": True}
    (FAULT_OUT / "m03a-inject-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


def retry():
    configure("012.02")
    before = hashes(rows())
    log = FAULT_PRIVATE / os.environ.get("R7_RETRY_LOG", "retry.log")
    completed = subprocess.run([q.JAVA, "-jar", q.JAR, "--spring.main.web-application-type=none",
                                "--northstar.initialize-content=false"], env=q.env(), cwd=q.SOURCE,
                               stdout=log.open("xb"), stderr=subprocess.STDOUT, timeout=600)
    text = log.read_text(errors="replace")
    assert completed.returncode != 0, text[-500:]
    assert ("1061" in text or "Duplicate key name" in text or "Detected failed migration" in text
            or ("failed" in text.lower() and "012.02" in text)), "retry failure is not diagnosable"
    history = probe("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank")
    assert "012.02\t0" in history and "012.02\t1" not in history
    occurrence = probe("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='" + q.SCHEMA +
                       "' AND table_name='knowledge_occurrence'")
    assert occurrence == "0"
    before.pop("flyway_schema_history")
    assert before == {key: value for key, value in hashes(rows()).items() if key != "flyway_schema_history"}
    result = {"status": "PASS", "behavior": "retry rejected, no silent success",
              "exitCode": completed.returncode, "mysqlError": "1061 duplicate key name",
              "retryLog": log.name, "retryLogSha256": q.sha(log),
              "historyRecorded": "012.02 success=0 (failed migration registered)",
              "oldRowsUnchanged": True}
    (FAULT_OUT / "m03a-retry-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


def api():
    """M07: a real API boot on the fault target must fail loudly, never half-open."""
    configure(None)
    before = hashes(rows())
    log = FAULT_PRIVATE / "api-failure.log"
    process = subprocess.Popen([q.JAVA, "-jar", q.JAR], env=q.env(), cwd=q.SOURCE,
                               stdout=log.open("xb"), stderr=subprocess.STDOUT)
    served = False
    for _ in range(300):
        if process.poll() is not None:
            break
        try:
            with urllib.request.urlopen(q.API + "/health", timeout=1) as response:
                if response.status == 200:
                    served = True
                    break
        except OSError:
            time.sleep(.2)
    process.wait()
    text = log.read_text(errors="replace")
    assert not served and process.returncode != 0, (served, process.returncode)
    assert ("1061" in text or "Duplicate key name" in text or "Detected failed migration" in text
            or ("failed" in text.lower() and "012.02" in text)), "API failure is not diagnosable"
    history = probe("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank")
    assert "012.02\t0" in history and "012.02\t1" not in history
    before.pop("flyway_schema_history")
    assert before == {key: value for key, value in hashes(rows()).items() if key != "flyway_schema_history"}
    result = {"status": "PASS", "scenario": "api startup on fault target",
              "exitCode": process.returncode, "healthServed": False,
              "diagnosableError": "Flyway V012.02 rerun rejected with MySQL 1061; history success=0",
              "log": "api-failure.log", "logSha256": q.sha(log), "oldRowsUnchanged": True}
    (FAULT_OUT / "m07-api-failure-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


def recover():
    sys.path.insert(0, str(ROOT / "qa/phase10d-final-r6"))
    import independent_restore as isolated
    configure(None)
    isolated.NAME = "northstar-qa-final-r7-fault-recovery-ddl-20261104"
    isolated.VOLUME = isolated.NAME + "-data"
    isolated.PORT = 3398
    isolated.TARGET = PRIVATE / "fault-recovery-ddl"
    isolated.create()
    identity = json.loads((isolated.TARGET / "identity.json").read_text())
    secret = json.loads((isolated.TARGET / "credentials.json").read_text())["root"]
    fault = json.loads((FAULT_PRIVATE / "identity.json").read_text())
    expected = json.loads((FAULT_OUT / "pre-fault-backup.json").read_text())
    assert fault["uuid"] != identity["uuid"] and fault["volume"] != identity["volume"]
    backup = FAULT_PRIVATE / "baseline-before-fault.sql"
    assert isolated.sha(backup) == expected["sha256"] and fault["uuid"] == expected["databaseUuid"]
    assert not isolated.mysql("SELECT schema_name FROM information_schema.schemata "
                              "WHERE schema_name='northstar_phase01_test';", identity, secret, "new-target-empty")
    isolated.mysql("CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
                   identity, secret, "new-target-schema")
    with backup.open("rb") as source:
        imported = subprocess.run([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(identity["port"]),
                                   "-uroot", "northstar_phase01_test"], stdin=source, capture_output=True,
                                  env=dict(os.environ, MYSQL_PWD=secret))
    assert imported.returncode == 0, imported.stderr[-300:]
    isolated.mysql("CREATE USER 'northstar_app'@'%' IDENTIFIED BY '" + q.credentials()["app"] + "'; "
                   "CREATE USER 'northstar_migrator'@'%' IDENTIFIED BY '" + q.credentials()["migrator"] + "'; "
                   "GRANT SELECT,INSERT,UPDATE,DELETE ON northstar_phase01_test.* TO 'northstar_app'@'%'; "
                   "GRANT ALL ON northstar_phase01_test.* TO 'northstar_migrator'@'%'; "
                   "SET GLOBAL log_bin_trust_function_creators=1;", identity, secret, "new-target-grants")
    shutil.copytree(FAULT_PRIVATE / "content", isolated.TARGET / "content")
    (isolated.TARGET / "recordings").mkdir(exist_ok=True)
    q.API_PORT = 8218
    q.WEB_PORT = 3218
    q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
    q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
    q.env = lambda: dict(BASE_ENV(), MYSQL_PORT=str(identity["port"]), DB_NAME="northstar_phase01_test",
                         NORTHSTAR_EXPECTED_DB_UUID=identity["uuid"],
                         NORTHSTAR_CONTENT_ROOT=str(isolated.TARGET / "content"),
                         NORTHSTAR_RECORDING_ROOT=str(isolated.TARGET / "recordings"))
    old = {table: isolated.mysql("SELECT * FROM northstar_phase01_test.`" + table + "` ORDER BY 1;",
                                 identity, secret, "before-" + table)
           for table in ("lesson", "lesson_version", "sentence", "personal_recording")}
    api = q.start_api()
    try:
        status, health = q.request("/health")
        assert status == 200 and health["migrationVersion"] == "012.11"
        status, lessons = q.request("/lessons")
        assert status == 200 and lessons
        event = str(uuid.uuid4())
        payload = {"eventId": event, "lessonId": "demo-01", "versionId": "demo-01-v2",
                   "sentenceId": "demo-01-v2-s06", "text": "Please put them behind the blue bench.",
                   "answerExposed": False, "audioPlayed": True, "clientOccurredAt": "2026-11-05T00:00:00Z"}
        first = q.request("/exercises/demo-01-v2-s06-dictation/attempts", payload)
        assert first[0] == 200
        replay = q.request("/exercises/demo-01-v2-s06-dictation/attempts", payload)
        assert replay == first
    finally:
        q.stop(api)
    new = {table: isolated.mysql("SELECT * FROM northstar_phase01_test.`" + table + "` ORDER BY 1;",
                                 identity, secret, "after-" + table) for table in old}
    assert old == new
    attempt = isolated.mysql("SELECT COUNT(*) FROM northstar_phase01_test.exercise_attempt WHERE event_id='" + event + "';",
                             identity, secret, "new-attempt-count")
    history = isolated.mysql("SELECT version,success FROM northstar_phase01_test.flyway_schema_history "
                             "ORDER BY installed_rank;", identity, secret, "history")
    assert attempt == "1" and history.splitlines()[-1] == "012.11\t1"
    result = {"status": "PASS", "failedTargetUuid": fault["uuid"], "restoredTargetUuid": identity["uuid"],
              "restoredVolume": identity["volume"], "backupSha256": expected["sha256"],
              "flywayVersion": "012.11", "oldRowsUnchanged": True, "newEventId": event,
              "replaySameReceipt": True, "lessonApiRead": True}
    (FAULT_OUT / "m03a-recovery-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    {"create": create, "inject": inject, "retry": retry, "api": api, "recover": recover}[sys.argv[1]]()
