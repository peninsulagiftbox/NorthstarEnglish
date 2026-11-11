#!/usr/bin/env python3
"""Own isolated API/Web subprocesses and a pinned Playwright CLI session."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import phase10e_environment as isolated
import local

r = isolated.r
role = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else "imports"
env = isolated.environment(role)
assert local.available(int(env["API_PORT"])) and local.available(int(env["WEB_PORT"]))
cli = None
for path in sorted((Path.home() / ".npm/_npx").glob("*/node_modules/@playwright/cli/package.json")):
    if json.loads(path.read_text()).get("version") == "0.1.22":
        cli = path.parent / "playwright-cli.js"
        break
assert cli, "Pinned Playwright CLI 0.1.22 unavailable"
command = ["node", str(cli), "--session=phase10e-" + mode]
processes, streams = [], []
try:
    for name, argv, cwd in [
        ("api", [str(Path(env["JAVA_HOME"]) / "bin/java"), "-jar",
                 str(r.COPY / "apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"),
                 "--northstar.content-root=" + env["NORTHSTAR_CONTENT_ROOT"],
                 "--northstar.recording-root=" + env["NORTHSTAR_RECORDING_ROOT"]], r.COPY / "apps/api"),
        ("web", ["node", str(r.ROOT / "node_modules/next/dist/bin/next"), "start",
                 "--hostname", "127.0.0.1", "--port", env["WEB_PORT"]], r.COPY / "apps/web")]:
        stream = (r.OUT / (mode + "-" + name + "-" + str(time.time_ns()) + ".log")).open("xb")
        streams.append(stream)
        processes.append(subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT))
    base = "http://127.0.0.1:" + env["WEB_PORT"]
    for _ in range(120):
        assert all(process.poll() is None for process in processes), "Isolated service exited"
        try:
            with urllib.request.urlopen(base + "/api/v1/health", timeout=2) as response:
                assert response.headers["X-Northstar-Test-Database"] == "true"
                assert json.load(response)["migrationVersion"] == "013.04"
            break
        except OSError:
            time.sleep(.3)
    else:
        raise RuntimeError("Isolated browser readiness timeout")
    (r.ROOT / "output/playwright/phase10e").mkdir(parents=True, exist_ok=True)
    (r.ROOT / "output/playwright/phase10e-demo").mkdir(parents=True, exist_ok=True)
    r.record(mode + "-browser-open", command + ["open", base + "/courses"], env=env, cwd=r.ROOT)
    r.record(mode + "-browser-snapshot", command + ["snapshot"], env=env, cwd=r.ROOT)
    script = "phase10e-browser.js" if mode == "imports" else "full-learning-loop.js"
    code = (r.ROOT / "scripts" / script).read_text().replace(
        "output/playwright/phase10b2-demo/", "output/playwright/phase10e-demo/")
    completed = r.record(mode + "-browser-run", command + ["run-code", code], env=env, cwd=r.ROOT, timeout=420)
    text = completed.stdout.decode()
    assert re.search(r'"passed"\s*:\s*true', text) and "### Error" not in text, "Browser assertions failed; log retained"
    result = json.loads(text.split("### Result\n", 1)[1].split("\n###", 1)[0])
    (r.OUT / (mode + "-browser-result.json")).write_text(json.dumps(result, ensure_ascii=False, indent=2))
finally:
    try:
        r.record(mode + "-browser-close", command + ["close"], env=env, cwd=r.ROOT, expected=(0, 1))
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        for stream in streams:
            stream.close()
