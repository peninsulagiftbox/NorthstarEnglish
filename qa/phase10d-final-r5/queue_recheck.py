import json
import subprocess
import time
import urllib.request
from run import q

api = q.start_api()
web = None
before = {}
try:
    for table in ("concept_review_card", "concept_review_source", "concept_review_result", "exercise_attempt", "attempt_knowledge", "command_receipt", "review_item", "review_result", "learning_evidence"):
        before[table] = q.sql("SELECT * FROM `" + table + "` ORDER BY 1", label="recheck-before-" + table)
    web = subprocess.Popen([q.NODE + "/node", str(q.ROOT / "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", str(q.WEB_PORT)], cwd=q.SOURCE / "apps/web", env=q.env(), stdout=(q.PRIVATE / "recheck-web.log").open("wb"), stderr=subprocess.STDOUT)
    for attempt in range(100):
        assert web.poll() is None
        try:
            with urllib.request.urlopen(q.WEB + "/api/v1/health", timeout=2) as response:
                if json.load(response).get("migrationVersion") == "012.11":
                    break
        except OSError:
            pass
        time.sleep(.3)
    else:
        raise RuntimeError("Web readiness timeout")
    q.run("queue-recheck", [q.NODE + "/node", q.TOOLS / "queue_recheck.cjs"], env=q.env(), timeout=180)
finally:
    unchanged = {}
    for table, snapshot in before.items():
        unchanged[table] = snapshot == q.sql("SELECT * FROM `" + table + "` ORDER BY 1", label="recheck-after-" + table)
    q.save("recheck-read-only-comparison.json", unchanged)
    if web:
        q.stop(web)
    q.stop(api)
    q.save("recheck-stop-state.json", dict(apiPid=api.pid, apiExit=api.returncode, webPid=None if web is None else web.pid, webExit=None if web is None else web.returncode))
