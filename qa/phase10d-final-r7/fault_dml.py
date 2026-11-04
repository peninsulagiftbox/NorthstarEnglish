#!/usr/bin/env python3
"""Exercise real Flyway V011.06 transactional backfill failure."""

import hashlib
import json
import os
import shutil
import subprocess
import sys

from run import q, OUT, PRIVATE

CASE = os.environ.get("R7_DML_CASE", "1")
DIR = OUT / ("fault_dml" if CASE == "1" else "fault_dml" + CASE)
STATE = PRIVATE / ("fault-dml" if CASE == "1" else "fault-dml" + CASE)


def configure(version):
    q.OUT = DIR
    DIR.mkdir(exist_ok=True)
    q.PRIVATE = STATE
    STATE.mkdir(exist_ok=True)
    q.NAME = "northstar-qa-final-r7-fault-dml" + CASE + "-20261104"
    q.API_PORT = 8206
    q.WEB_PORT = 3213
    original = q.env
    q.env = lambda: dict(original(), SPRING_FLYWAY_TARGET=version)


def create():
    configure("011.05")
    shutil.copy2(OUT / "qa-r7-final-candidate.sha256", DIR / "qa-final-candidate-manifest.sha256")
    q.create()
    if CASE != "1":
        q.sql("DELETE FROM exercise_set_item; DELETE FROM exercise_set",
              label="fixture-remove-new-format-sets")
        assert q.sql("SELECT COUNT(*) FROM exercise_set", label="fixture-empty-set") == "0"
        assert q.sql("SELECT COUNT(*) FROM quiz_question", label="fixture-quiz-questions") != "0"
    history = q.sql("SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1",
                    label="baseline-history")
    assert history == "011.05"
    print(json.dumps(q.identity()))


def backup():
    configure("011.05")
    path = STATE / "baseline-before-fault.sql"
    command = [q.DOCKER, "exec", q.identity()["containerId"], "sh", "-c",
               'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --routines --triggers --events --no-tablespaces --set-gtid-purged=OFF northstar_phase01_test']
    with path.open("xb") as output:
        completed = subprocess.run(command, stdout=output, stderr=subprocess.PIPE)
    assert completed.returncode == 0 and path.stat().st_size > 0, completed.stderr[-200:]
    (DIR / "pre-fault-backup.json").write_text(json.dumps({"uuid": q.identity()["uuid"],
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": path.stat().st_size,
        "argv": command, "exitCode": completed.returncode}, indent=2) + "\n")


def inject():
    configure("011.06")
    before = {table: q.sql("SELECT * FROM " + table + " ORDER BY 1", label="before-" + table)
              for table in ("exercise_set", "exercise_set_item", "quiz_run", "quiz_run_item")}
    (DIR / "before-hashes.json").write_text(json.dumps({table: hashlib.sha256(rows.encode()).hexdigest()
                                                       for table, rows in before.items()}, indent=2) + "\n")
    q.sql("REVOKE INSERT ON `northstar_phase01_test`.* FROM 'northstar_migrator'@'%'; "
          "GRANT INSERT ON `northstar_phase01_test`.`exercise_set` TO 'northstar_migrator'@'%'; "
          "GRANT INSERT ON `northstar_phase01_test`.`flyway_schema_history` TO 'northstar_migrator'@'%'",
          label="inject-deny-second-backfill-insert")
    first = q.run("flyway-dml-backfill-failure", [q.JAVA, "-jar", q.JAR,
                  "--spring.main.web-application-type=none", "--northstar.initialize-content=false"],
                  env=q.env(), check=False)
    assert first.returncode != 0
    log = (DIR / "flyway-dml-backfill-failure.log").read_text()
    assert "Error Code : 1142" in log and "exercise_set_item" in log
    after = {table: q.sql("SELECT * FROM " + table + " ORDER BY 1", label="after-" + table)
             for table in before}
    assert before == after
    history = q.sql("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 2",
                    label="after-history")
    result = {"status": "PASS", "targetUuid": q.identity()["uuid"], "volume": q.identity()["volume"],
              "migration": "011.06", "exitCode": first.returncode,
              "oldRowsUnchanged": True, "backfillRowsRolledBack": True,
              "historyTail": history.splitlines(), "errorLog": "flyway-dml-backfill-failure.log"}
    (DIR / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    {"create": create, "backup": backup, "inject": inject}[sys.argv[1]]()
