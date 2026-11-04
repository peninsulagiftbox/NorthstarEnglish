#!/usr/bin/env python3
"""Run P0/P1 fix acceptance against a fresh disposable MySQL container."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("r4_base", ROOT / "qa/phase10d-final-r4/run.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

q.OUT = ROOT / "qa/phase10d-final-r7-fix/evidence"
q.PRIVATE = ROOT / ".local/qa-final-r7-fix"
q.SOURCE = ROOT
q.NAME = "northstar-qa-r7-p0p1-fix-20261104"
q.API_PORT = 8214
q.WEB_PORT = 3214
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
q.OUT.mkdir(parents=True, exist_ok=True)
q.PRIVATE.mkdir(parents=True, exist_ok=True)


def main(action):
    if action == "create":
        q.create()
    elif action == "test":
        q.run("p0p1-quiz-review", ["bash", ROOT / "apps/api/mvnw", "-f",
                                   ROOT / "apps/api/pom.xml", "test",
                                   "-Dtest=QuizReviewIntegrationTest"], env=q.env())
        history = q.sql("SELECT version,success FROM flyway_schema_history ORDER BY installed_rank",
                        label="p0p1-history")
        triggers = q.sql("SELECT trigger_name,event_manipulation FROM information_schema.triggers "
                         "WHERE event_object_schema='" + q.SCHEMA + "' AND event_object_table='review_result'",
                         label="p0p1-review-result-triggers")
        assert history.splitlines()[-1].startswith("012.12\t1"), history
        assert triggers == "review_result_no_update\tUPDATE", triggers
        result = {"status": "PASS", "migration": "012.12", "trigger": "review_result_no_update",
                  "databaseUuid": q.identity()["uuid"], "volume": q.identity()["volume"]}
        (q.OUT / "p0p1-fix-result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    else:
        raise ValueError(action)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
