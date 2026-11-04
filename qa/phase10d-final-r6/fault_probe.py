#!/usr/bin/env python3
"""Keep narrow R6 failure probes in new schemas; report their formal limits."""

import datetime
import hashlib
import json
import re
import shutil
import uuid

import restore

q = restore.q
OUT = q.OUT


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def source_state():
    return {table: digest(q.sql(f"SELECT * FROM `{table}` ORDER BY 1",
                                 label="r6-fault-source-" + table + "-" + uuid.uuid4().hex[:6]))
            for table in ("flyway_schema_history", "concept_review_card", "concept_review_source",
                          "concept_review_result", "attempt_knowledge", "review_item", "review_result")}


def error(query, schema, label):
    result = q.sql(query, schema=schema, check=False, label="r6-fault-" + label)
    code = re.search(r"ERROR (\d+)", result.stderr)
    assert result.returncode != 0 and code, (label, result.returncode)
    return int(code.group(1))


def main():
    before = source_state()
    marker = uuid.uuid4().hex[:10]
    ddl = "northstar_r6_fault_ddl_" + marker
    dml = "northstar_r6_fault_dml_" + marker
    for schema in (ddl, dml):
        q.sql(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4", label="r6-fault-create-" + schema)
    ddl_error = error("CREATE TABLE r6_probe(id INT PRIMARY KEY); INSERT INTO r6_probe(no_such_column) VALUES (1)",
                      ddl, "ddl-after-commit")
    assert q.sql("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='" + ddl +
                 "' AND table_name='r6_probe'", label="r6-fault-ddl-table") == "1"
    assert q.sql("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='" + ddl +
                 "' AND table_name='flyway_schema_history'", label="r6-fault-ddl-history") == "0"
    q.sql("CREATE TABLE r6_probe(id INT PRIMARY KEY)", schema=dml, label="r6-fault-dml-table")
    dml_error = error("START TRANSACTION; INSERT INTO r6_probe VALUES (1); INSERT INTO r6_probe(no_such_column) VALUES (2)",
                      dml, "dml-before-commit")
    assert q.sql("SELECT COUNT(*) FROM r6_probe", schema=dml, label="r6-fault-dml-row-count") == "0"

    backup = __import__("pathlib").Path(json.loads((OUT / "r6-restore-result.json").read_text())["backupPathPrivate"])
    incomplete = q.PRIVATE / ("r6-incomplete-backup-" + marker)
    incomplete.mkdir(mode=0o700)
    original = (backup / "learning.json").read_bytes()
    (incomplete / "learning.json").write_bytes(original[:len(original) // 2])
    target = "northstar_restore_" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    try:
        restore.invoke("restore", incomplete / "learning.json", target)
        raise AssertionError("truncated backup unexpectedly restored")
    except SystemExit as failure:
        assert failure.code == 1
    assert q.sql("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='" + target + "'",
                 label="r6-fault-incomplete-target-absent") == "0"
    after = source_state()
    assert before == after
    media = {str(path.relative_to(q.PRIVATE / "content")): q.sha(path)
             for path in (q.PRIVATE / "content").rglob("*.mp3")}
    result = {"status": "PARTIAL", "sourceUuid": q.identity()["uuid"],
              "ddlProbe": {"schema": ddl, "error": ddl_error, "committedTablePersists": True,
                           "flywayHistoryTableAbsent": True},
              "dmlProbe": {"schema": dml, "error": dml_error, "uncommittedRows": 0},
              "backupProbe": {"truncatedSha256": hashlib.sha256((incomplete / "learning.json").read_bytes()).hexdigest(),
                              "targetSchema": target, "targetCreated": False},
              "sourceRowsUnchanged": True, "sourceTableSha256": before,
              "originalContentMp3Sha256": media, "restoredPersonalRecordingCount": 0,
              "limit": "Generic isolated SQL and truncated-backup probes; not a complete V012 Flyway M03-M08 failure matrix."}
    (OUT / "r6-fault-probe-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "ddlError": ddl_error,
                      "dmlError": dml_error, "incompleteTargetCreated": False}))


if __name__ == "__main__":
    main()
