#!/usr/bin/env python3
"""Probe restored R6 FK and append-only guards without mutating old rows."""

import hashlib
import json
import re

import run

q = run.q
OUT = q.OUT
target = json.loads((OUT / "r6-restore-result.json").read_text())["targetSchema"]
TABLES = ("concept_review_source", "concept_review_result", "attempt_knowledge",
          "concept_review_card", "flyway_schema_history")


def sql(statement, label, check=True):
    return q.sql(statement, label="r6-negative-" + label, schema=target, check=check)


def digest_rows():
    return {table: hashlib.sha256(sql(f"SELECT * FROM `{table}` ORDER BY 1",
                                     "before-after-" + table + "-" + __import__("uuid").uuid4().hex[:6]).encode()).hexdigest()
            for table in TABLES}


def expect_error(label, statement):
    result = sql(statement, label, check=False)
    match = re.search(r"ERROR (\d+)", result.stderr)
    assert result.returncode != 0 and match, (label, result.returncode)
    return {"case": label, "exitCode": result.returncode, "mysqlError": int(match.group(1)),
            "stderrLastLine": result.stderr.strip().splitlines()[-1]}


def main():
    before = digest_rows()
    finance = sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'", "finance-card")
    river = sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-riv'", "river-card")
    row = sql(f"SELECT attempt_id,occurrence_id,exercise_id,version_id FROM concept_review_source WHERE card_id='{finance}' LIMIT 1", "finance-source").split("\t")
    attempt, occurrence, exercise, version = row
    cases = [
        expect_error("cross-concept", "INSERT INTO concept_review_source(card_id,attempt_id,occurrence_id,exercise_id,version_id,concept_id) VALUES "
                     f"('{river}','{attempt}','{occurrence}','{exercise}','{version}','cr-bank-riv')"),
        expect_error("cross-version", "INSERT INTO concept_review_source(card_id,attempt_id,occurrence_id,exercise_id,version_id,concept_id) VALUES "
                     f"('{finance}','{attempt}','{occurrence}','{exercise}','cr-b-v1','cr-bank-fin')"),
        expect_error("append-only-result-update", "UPDATE concept_review_result SET rating='again' WHERE card_id='" + finance + "' LIMIT 1"),
        expect_error("append-only-result-delete", "DELETE FROM concept_review_result WHERE card_id='" + finance + "' LIMIT 1"),
        expect_error("append-only-attempt-update", "UPDATE attempt_knowledge SET concept_id='cr-bank-fin' WHERE attempt_id='" + attempt + "' LIMIT 1"),
        expect_error("append-only-attempt-delete", "DELETE FROM attempt_knowledge WHERE attempt_id='" + attempt + "' LIMIT 1"),
    ]
    after = digest_rows()
    assert before == after, "negative SQL changed business rows or Flyway history"
    (OUT / "r6-negative-sql-result.json").write_text(json.dumps({
        "status": "PASS", "targetSchema": target, "cases": cases,
        "prePostTableSha256Equal": True, "tableSha256": before}, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "mysqlErrors": [case["mysqlError"] for case in cases]}, indent=2))


def correct_version():
    before = digest_rows()
    finance = sql("SELECT id FROM concept_review_card WHERE concept_id='cr-bank-fin'", "version-finance-card")
    attempt = sql(f"SELECT attempt_id FROM concept_review_source WHERE card_id='{finance}' LIMIT 1", "version-attempt")
    case = expect_error("cross-version-distinct-key",
        "INSERT INTO attempt_knowledge(attempt_id,occurrence_id,exercise_id,version_id,concept_id,revision_id,sentence_id,role,source_json,source_sha256) "
        "SELECT attempt_id,'cr-oc-bank-b',exercise_id,'cr-b-v1',concept_id,revision_id,sentence_id,role,source_json,source_sha256 "
        f"FROM attempt_knowledge WHERE attempt_id='{attempt}' LIMIT 1")
    assert case["mysqlError"] == 1452, case
    assert before == digest_rows()
    (OUT / "r6-negative-sql-corrected.json").write_text(json.dumps({
        "status": "PASS", "case": case, "prePostTableSha256Equal": True,
        "priorAttempt": "Cross-version source insert hit duplicate primary key 1062 before FK evaluation; retained as inconclusive."
    }, indent=2) + "\n")


if __name__ == "__main__":
    {"run": main, "correct_version": correct_version}[
        __import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "run"]()
