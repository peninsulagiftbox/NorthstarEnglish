#!/usr/bin/env python3
"""Fail real Flyway history registration after V012.10 DDL on a disposable target."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from run import q, OUT, PRIVATE, ROOT

FAULT_OUT = OUT / "fault_history"
FAULT_PRIVATE = PRIVATE / "fault-history"
NAME = "northstar-qa-final-r7-fault-history-20261104"
SOURCE = q.SOURCE


def configure(target):
    q.OUT = FAULT_OUT
    q.OUT.mkdir(exist_ok=True)
    q.PRIVATE = FAULT_PRIVATE
    q.PRIVATE.mkdir(exist_ok=True)
    q.SOURCE = SOURCE
    q.NAME = NAME
    q.API_PORT = 8204
    q.WEB_PORT = 3211
    q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
    q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
    original = q.env
    q.env = lambda: dict(original(), SPRING_FLYWAY_TARGET=target)


def create():
    configure("012.09")
    shutil.copy2(OUT / "qa-r7-final-candidate.sha256", FAULT_OUT / "qa-final-candidate-manifest.sha256")
    q.create()
    history = q.sql("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank",
                    label="baseline-history")
    assert history.splitlines()[-1] == "012.09\t1"
    print(json.dumps(q.identity()))


def inject():
    configure("012.11")
    baseline = {name: q.sql("SELECT * FROM " + name + " ORDER BY 1", label="before-" + name)
                for name in ("lesson", "lesson_version", "sentence", "exercise_attempt",
                             "personal_recording", "flyway_schema_history")}
    (FAULT_OUT / "before-hashes.json").write_text(json.dumps({key: hashlib.sha256(value.encode()).hexdigest()
                                                               for key, value in baseline.items()}, indent=2) + "\n")
    q.sql("REVOKE INSERT ON `northstar_phase01_test`.* FROM 'northstar_migrator'@'%'",
          label="inject-revoke-history-insert")
    first = q.run("flyway-history-register-failure", [q.JAVA, "-jar", q.JAR,
                  "--spring.main.web-application-type=none", "--northstar.initialize-content=false"],
                  env=q.env(), check=False)
    assert first.returncode != 0
    unique = q.sql("SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema='northstar_phase01_test' "
                   "AND table_name='attempt_knowledge' AND index_name='uq_attempt_knowledge_card_source'",
                   label="after-ddl-index-count")
    table = q.sql("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='northstar_phase01_test' "
                  "AND table_name='concept_review_source'", label="after-ddl-table-count")
    history = q.sql("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank",
                    label="after-history")
    assert int(unique) >= 1 and table == "1" and "012.10" not in history
    finalize(first.returncode)


def finalize(first_exit_code):
    configure("012.11")
    baseline = json.loads((FAULT_OUT / "before-hashes.json").read_text())
    retry = q.run("flyway-unsafe-retry-blocked", [q.JAVA, "-jar", q.JAR,
                  "--spring.main.web-application-type=none", "--northstar.initialize-content=false"],
                  env=q.env(), check=False)
    assert retry.returncode != 0
    for name in ("lesson", "lesson_version", "sentence", "exercise_attempt", "personal_recording"):
        after = q.sql("SELECT * FROM " + name + " ORDER BY 1", label="after-" + name)
        assert baseline[name] == hashlib.sha256(after.encode()).hexdigest()
    result = {"status": "PASS", "faultTargetUuid": q.identity()["uuid"],
              "faultTargetVolume": q.identity()["volume"], "migration": "012.10",
              "ddlCommitted": True, "historyRegistered": False,
              "firstExitCode": first_exit_code, "retryExitCode": retry.returncode,
              "oldRowsUnchanged": True, "recovery": "restore pre-fault backup into a fresh target; never repair this target"}
    (FAULT_OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    {"create": create, "inject": inject, "finalize": lambda: finalize(1)}[sys.argv[1]]()
