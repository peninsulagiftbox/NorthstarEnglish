#!/usr/bin/env python3
"""Hold and stop only R7 owned API/Web processes on the restored database."""

import json
import subprocess
import sys
import time
import urllib.request

from independent_restore import TARGET, SCHEMA
from run import q, OUT, PRIVATE, ROOT

identity = json.loads((TARGET / "identity.json").read_text())
original_env = q.env
q.env = lambda: dict(original_env(), MYSQL_PORT=str(identity["port"]), DB_NAME=SCHEMA,
                     NORTHSTAR_EXPECTED_DB_UUID=identity["uuid"],
                     NORTHSTAR_CONTENT_ROOT=str(TARGET / "content"),
                     NORTHSTAR_RECORDING_ROOT=str(TARGET / "recordings"))


def main():
    assert (q.SOURCE / "apps/web/.next/BUILD_ID").read_text().strip() == json.loads((OUT / "web-identity.json").read_text())["buildId"]
    api = q.start_api()
    web = None
    try:
        web_log = (PRIVATE / "r7-browser-web.log").open("xb")
        web = subprocess.Popen([q.NODE + "/node", str(ROOT / "node_modules/next/dist/bin/next"),
                                "start", "--hostname", "127.0.0.1", "--port", str(q.WEB_PORT)],
                               cwd=q.SOURCE / "apps/web", env=q.env(), stdout=web_log,
                               stderr=subprocess.STDOUT)
        for _ in range(100):
            assert web.poll() is None
            try:
                with urllib.request.urlopen(q.WEB + "/api/v1/health", timeout=2) as response:
                    if json.load(response)["migrationVersion"] == "012.11":
                        break
            except OSError:
                pass
            time.sleep(.3)
        else:
            raise RuntimeError("R7 Web not ready")
        runtime = {"databaseUuid": identity["uuid"], "api": q.API, "web": q.WEB,
                   "buildId": (q.SOURCE / "apps/web/.next/BUILD_ID").read_text().strip(),
                   "apiPid": api.pid, "webPid": web.pid}
        (OUT / "r7-browser-runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
        print(json.dumps(runtime), flush=True)
        sys.stdin.readline()
    finally:
        if web:
            q.stop(web)
        q.stop(api)


if __name__ == "__main__":
    main()
