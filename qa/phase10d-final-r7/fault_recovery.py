#!/usr/bin/env python3
"""Recover the pre-fault V012.09 backup on a new volume and finish Flyway."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import independent_restore as isolated
from run import q, OUT, PRIVATE

CASE = os.environ.get("R7_RECOVERY_CASE", "history")
isolated.NAME = "northstar-qa-final-r7-fault-recovery" + ("" if CASE == "history" else "-" + CASE) + "-20261104"
isolated.VOLUME = isolated.NAME + "-data"
isolated.PORT = 3388 if CASE == "history" else 3391
isolated.TARGET = PRIVATE / ("fault-recovery" if CASE == "history" else "fault-recovery-" + CASE)


def create():
    isolated.create()


def recover():
    target = isolated.TARGET
    identity = json.loads((target / "identity.json").read_text())
    secret = json.loads((target / "credentials.json").read_text())["root"]
    fault_dir = PRIVATE / ("fault-history" if CASE == "history" else "fault-" + CASE)
    evidence_dir = OUT / ("fault_history" if CASE == "history" else "fault_" + CASE)
    fault = json.loads((fault_dir / "identity.json").read_text())
    assert fault["uuid"] != identity["uuid"] and fault["volume"] != identity["volume"]
    backup = fault_dir / "baseline-before-fault.sql"
    expected = json.loads((evidence_dir / "pre-fault-backup.json").read_text())
    assert isolated.sha(backup) == expected["sha256"] and fault["uuid"] == expected.get("databaseUuid", expected.get("uuid"))
    assert not isolated.mysql("SELECT schema_name FROM information_schema.schemata WHERE schema_name='northstar_phase01_test';",
                              identity, secret, "new-target-empty")
    isolated.mysql("CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
                   identity, secret, "new-target-schema")
    with backup.open("rb") as source:
        imported = subprocess.run([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(identity["port"]),
                                   "-uroot", "northstar_phase01_test"], stdin=source, capture_output=True,
                                  env=dict(os.environ, MYSQL_PWD=secret))
    assert imported.returncode == 0, imported.stderr[-300:]
    app_password = q.credentials()["app"]
    migrator_password = q.credentials()["migrator"]
    isolated.mysql("CREATE USER 'northstar_app'@'%' IDENTIFIED BY '" + app_password + "'; "
                   "CREATE USER 'northstar_migrator'@'%' IDENTIFIED BY '" + migrator_password + "'; "
                   "GRANT SELECT,INSERT,UPDATE,DELETE ON northstar_phase01_test.* TO 'northstar_app'@'%'; "
                   "GRANT ALL ON northstar_phase01_test.* TO 'northstar_migrator'@'%'; "
                   "SET GLOBAL log_bin_trust_function_creators=1;", identity, secret, "new-target-grants")
    shutil.copytree(fault_dir / "content", target / "content")
    (target / "recordings").mkdir(exist_ok=True)
    before = {table: isolated.mysql("SELECT * FROM northstar_phase01_test.`" + table + "` ORDER BY 1;",
                                    identity, secret, "before-" + table)
              for table in ("lesson", "exercise_attempt", "quiz_run", "personal_recording")}
    q.API_PORT = 8205 if CASE == "history" else 8207
    q.WEB_PORT = 3212 if CASE == "history" else 3214
    q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
    q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
    original_env = q.env
    q.env = lambda: dict(original_env(), MYSQL_PORT=str(identity["port"]),
                         NORTHSTAR_EXPECTED_DB_UUID=identity["uuid"],
                         NORTHSTAR_CONTENT_ROOT=str(target / "content"),
                         NORTHSTAR_RECORDING_ROOT=str(target / "recordings"))
    api = q.start_api()
    try:
        status, health = q.request("/health")
        assert status == 200 and health["migrationVersion"] == "012.11"
        status, lessons = q.request("/lessons")
        assert status == 200 and lessons
    finally:
        q.stop(api)
    after = {table: isolated.mysql("SELECT * FROM northstar_phase01_test.`" + table + "` ORDER BY 1;",
                                   identity, secret, "after-" + table)
             for table in before}
    assert before == after
    history = isolated.mysql("SELECT version,success FROM northstar_phase01_test.flyway_schema_history "
                             "ORDER BY installed_rank;", identity, secret, "history")
    assert history.splitlines()[-1] == "012.11\t1"
    result = {"status": "PASS", "failedTargetUuid": fault["uuid"],
              "restoredTargetUuid": identity["uuid"], "restoredVolume": identity["volume"],
              "backupSha256": expected["sha256"], "flywayVersion": "012.11",
              "oldRowsUnchanged": True, "lessonApiRead": True}
    (OUT / ("r7-fault-recovery-result.json" if CASE == "history" else "r7-fault-recovery-" + CASE + "-result.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    {"create": create, "recover": recover}[sys.argv[1]]()
