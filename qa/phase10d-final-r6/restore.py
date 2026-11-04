#!/usr/bin/env python3
"""Exercise the unchanged data-transfer script with an R6 identity adapter."""

import datetime
import json
import runpy
import sys
import types
import uuid
from pathlib import Path

import run

q = run.q
ROOT = run.ROOT
OUT = q.OUT
sys.path.insert(0, str(ROOT / "scripts"))
import local


class Campaign:
    PRIVATE = q.PRIVATE

    def verify(self, role):
        assert role == "."
        assert q.sql("SELECT @@server_uuid", label="r6-transfer-uuid") == q.identity()["uuid"]
        return q.identity()

    def sql(self, role, query, readonly=False):
        assert role == "." and readonly
        return q.sql(query, label="r6-transfer-identity")


def invoke(action, path, target=None):
    adapter = types.ModuleType("phase10d_isolated")
    adapter.r = types.SimpleNamespace(STATE=q.PRIVATE)
    adapter.campaign = Campaign
    adapter.env = lambda campaign, role, schema: q.env()
    sys.modules["phase10d_isolated"] = adapter
    local.environment = q.env
    (q.PRIVATE / "ACTIVE_TEST_ROLE").write_text(".\n")
    argv = ["data-transfer.py", action, str(path), "--phase10d", "--api",
            f"http://127.0.0.1:{q.API_PORT}", "--web-port", str(q.WEB_PORT),
            "--recording-root", str(q.PRIVATE / "recordings")]
    if target:
        argv.extend(["--target", target, "--confirm-new-isolated"])
    sys.argv = argv
    runpy.run_path(str(ROOT / "scripts/data-transfer.py"), run_name="__main__")


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    backup = q.PRIVATE / ("r6-backup-" + stamp)
    target = "northstar_restore_" + stamp
    api = q.start_api()
    try:
        invoke("backup", backup)
        envelope = json.loads((backup / "learning.json").read_text())
        payload = json.loads(envelope["payloadJson"])
        required = ("knowledge_concept", "knowledge_concept_revision", "knowledge_occurrence",
                    "exercise_knowledge", "attempt_knowledge", "concept_review_card",
                    "concept_review_source", "concept_review_result", "review_item", "review_result")
        counts = {table: len(payload["tables"][table]["rows"]) for table in required}
        assert all(counts.values()), counts
        occurrence = payload["tables"]["knowledge_occurrence"]
        assert "location_guard" in occurrence["columns"] and occurrence["rows"]
        invoke("restore", backup / "learning.json", target)
        restored = {table: int(q.sql(f"SELECT COUNT(*) FROM `{table}`", schema=target,
                          label="r6-restored-count-" + table)) for table in required}
        assert restored == counts
        source_guard = q.sql("SELECT id,location_guard FROM knowledge_occurrence ORDER BY id",
                             label="r6-source-generated-column")
        target_guard = q.sql("SELECT id,location_guard FROM knowledge_occurrence ORDER BY id", schema=target,
                             label="r6-target-generated-column")
        assert source_guard == target_guard
        before = {table: q.sql(f"SELECT * FROM `{table}` ORDER BY 1", schema=target,
                  label="r6-restored-rows-" + table) for table in required}
        result = {"status": "PASS", "sourceContainer": q.identity()["containerId"],
                  "sourceUuid": q.identity()["uuid"], "sourceSchema": q.SCHEMA,
                  "targetSchema": target, "backupSha256": q.sha(backup / "learning.json"),
                  "backupPathPrivate": str(backup), "counts": counts,
                  "generatedColumn": "location_guard", "generatedValuesEqual": True,
                  "targetRowsSha256": {table: __import__("hashlib").sha256(rows.encode()).hexdigest()
                                        for table, rows in before.items()}}
        (OUT / "r6-restore-result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        q.stop(api)


if __name__ == "__main__":
    main()
