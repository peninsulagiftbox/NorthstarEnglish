#!/usr/bin/env python3
"""Run R6 against a new, guarded MySQL container and frozen source copy."""

import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("qa_r4", ROOT / "qa/phase10d-final-r4/run.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
q.TOOLS = TOOLS
q.OUT = TOOLS / "evidence"
q.PRIVATE = ROOT / ".local/qa-final-r6"
q.SOURCE = q.PRIVATE / "source"
q.NAME = "northstar-qa-final-r6-20261103"
q.API_PORT = 8198
q.WEB_PORT = 3205
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
q.JAR = ROOT / "output/review/northstar-phase10d2-r5-fix-candidate.jar"
q.JAR_SHA = "771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6"
q.OUT.mkdir(parents=True, exist_ok=True)
q.PRIVATE.mkdir(parents=True, exist_ok=True)


def run(label, args, env=None, stdin=None, cwd=ROOT, check=True, timeout=600):
    identity = json.loads((q.OUT / "candidate-identity.json").read_text())
    run_id = identity["runId"] + "-" + uuid.uuid4().hex[:12]
    log = q.OUT / (run_id + "-" + label + ".log")
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    completed = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, input=stdin,
                               capture_output=True, text=True, timeout=timeout)
    output = completed.stdout + "\nSTDERR\n" + completed.stderr
    for secret in q.credentials().values():
        output = output.replace(secret, "<REDACTED>")
    log.write_text(output)
    record = dict(runId=run_id, case=label, startedAt=start,
                  endedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  argv=[str(arg) for arg in args], cwd=str(cwd), exitCode=completed.returncode,
                  log=log.name, logSha256=q.sha(log),
                  candidateManifestSha256=identity["candidateManifestSha256"])
    with (q.OUT / "commands.jsonl").open("a") as journal:
        journal.write(json.dumps(record) + "\n")
    print(label, "exit=" + str(completed.returncode), flush=True)
    if check and completed.returncode:
        raise RuntimeError(label + " failed; " + str(log))
    return completed


q.run = run


def prepare():
    if q.SOURCE.exists():
        raise RuntimeError("R6 source copy already exists")
    manifest = q.OUT / "qa-r6-candidate-manifest.sha256"
    selected = {line.split("  ", 1)[1] for line in manifest.read_text().splitlines()}
    selected.update(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    for name in sorted(selected):
        origin = ROOT / name
        if not origin.is_file() or name.startswith(("qa/phase10d-final-r6/evidence/", "output/")):
            continue
        destination = q.SOURCE / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)
    for name in ("node_modules", "apps/web/node_modules"):
        origin = ROOT / name
        if origin.exists() and not (q.SOURCE / name).exists():
            (q.SOURCE / name).symlink_to(origin, target_is_directory=True)
    shutil.copy2(ROOT / "qa/phase10d-final-r4/FinalQaFixture.java",
                 q.SOURCE / "apps/api/src/test/java/local/northstar/knowledge/FinalQaFixture.java")
    shutil.copy2(ROOT / "qa/phase10d2-r5-fix/QueuePaginationQaFixture.java",
                 q.SOURCE / "apps/api/src/test/java/local/northstar/knowledge/QueuePaginationQaFixture.java")
    run("r6-java-version", [q.JAVA, "-version"])
    run("r6-node-version", [q.NODE + "/node", "--version"])
    run("r6-mysql-client-version", [q.MYSQL, "--version"])
    q.save("r6-migration-inputs.json", {p.name: q.sha(p) for p in
           sorted((q.SOURCE / "apps/api/src/main/resources/db/migration").glob("*.sql"))})
    print("R6 copied", len(selected), "candidate paths", flush=True)


if __name__ == "__main__":
    {"prepare": prepare, "create": q.create, "regressions": q.regressions,
     "seed": q.seed}[sys.argv[1]]()
