#!/usr/bin/env python3
"""M08: run the unchanged old Demo full learning loop on the final2 restore target."""

import glob
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

from run import q, OUT, PRIVATE, ROOT

TARGET = PRIVATE / "independent-restore-final2"
RESULT = OUT / "r7-demo-loop-result.json"


def main():
    identity = json.loads((TARGET / "identity.json").read_text())
    credentials = json.loads((PRIVATE / "credentials.json").read_text())
    assert identity["port"] == 3397
    original_env = q.env
    q.API_PORT = 8202
    q.WEB_PORT = 3219
    q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
    q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
    q.env = lambda: dict(original_env(), MYSQL_PORT=str(identity["port"]), DB_NAME="northstar_phase01_test",
                         DB_PASSWORD=credentials["app"], DB_MIGRATION_PASSWORD=credentials["migrator"],
                         NORTHSTAR_EXPECTED_DB_UUID=identity["uuid"],
                         NORTHSTAR_CONTENT_ROOT=str(TARGET / "content"),
                         NORTHSTAR_RECORDING_ROOT=str(TARGET / "recordings"))
    assert (q.SOURCE / "apps/web/.next/BUILD_ID").read_text().strip() == json.loads((OUT / "web-identity.json").read_text())["buildId"]
    api = q.start_api()
    web = None
    try:
        web = subprocess.Popen([q.NODE + "/node", str(ROOT / "node_modules/next/dist/bin/next"),
                                "start", "--hostname", "127.0.0.1", "--port", str(q.WEB_PORT)],
                               cwd=q.SOURCE / "apps/web", env=q.env(),
                               stdout=(PRIVATE / "demo-loop-web.log").open("ab"), stderr=subprocess.STDOUT)
        for _ in range(150):
            assert web.poll() is None
            try:
                with urllib.request.urlopen(q.WEB + "/api/v1/health", timeout=2) as response:
                    assert response.headers["X-Northstar-Test-Database"] == "true"
                    if json.load(response)["migrationVersion"] == "012.11":
                        break
            except (OSError, AssertionError):
                pass
            time.sleep(.4)
        else:
            raise RuntimeError("demo loop web not ready")
        cli = None
        for path in sorted(glob.glob(str(Path.home() / ".npm/_npx/*/node_modules/@playwright/cli/package.json"))):
            if json.loads(Path(path).read_text()).get("version") == "0.1.22":
                cli = Path(path).parent / "playwright-cli.js"
                break
        assert cli, "pinned Playwright CLI missing"
        command = ["node", str(cli), "--session=northstar-r7-demo"]
        script = (ROOT / "scripts/full-learning-loop.js").read_text()
        q.run("demo-loop-open", command + ["open", q.WEB], env=q.env(), cwd=ROOT, timeout=120)
        completed = q.run("demo-loop-run-code", command + ["run-code", script], env=q.env(), cwd=ROOT,
                          timeout=420, check=False)
        q.run("demo-loop-close", command + ["close"], env=q.env(), cwd=ROOT, timeout=60, check=False)
        log = None
        for line in open(OUT / "commands.jsonl"):
            row = json.loads(line)
            if row.get("label") == "demo-loop-run-code":
                log = row["log"]
        assert log, "demo-loop-run-code journal row missing"
        text = (OUT / log).read_text()
        assert completed.returncode == 0 and re.search(r'"passed"\s*:\s*true', text), text[-1200:]
        checks = re.search(r'"checks"\s*:\s*\[(.*?)\]', text, re.S)
        passed = {"status": "PASS", "databaseUuid": identity["uuid"], "web": q.WEB,
                  "script": "scripts/full-learning-loop.js", "scriptUnchanged": True,
                  "runLog": log, "checks": ("[" + checks.group(1) + "]") if checks else None}
        RESULT.write_text(json.dumps(passed, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({key: value for key, value in passed.items() if key != "runLog"}))
    finally:
        if web:
            q.stop(web)
        q.stop(api)


if __name__ == "__main__":
    main()
