#!/usr/bin/env python3
"""Create-only R7 source database and immutable, logged candidate inventory."""

import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
OUT = TOOLS / "evidence"
PRIVATE = ROOT / ".local/qa-final-r7"
spec = importlib.util.spec_from_file_location("r7_base", ROOT / "qa/phase10d-final-r4/run.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
q.TOOLS = TOOLS
q.OUT = OUT
q.PRIVATE = PRIVATE
q.SOURCE = PRIVATE / "source"
q.NAME = "northstar-qa-final-r7-source-20261104"
q.API_PORT = 8202
q.WEB_PORT = 3209
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
q.JAR = ROOT / "output/review/northstar-phase10d2-r5-fix-candidate.jar"
q.JAR_SHA = "771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6"
OUT.mkdir(parents=True, exist_ok=True)
PRIVATE.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze():
    manifest = OUT / "qa-r7-final-candidate.sha256"
    if manifest.exists():
        raise RuntimeError("R7 candidate already frozen")
    old = ROOT / "qa/phase10d-final-r6/evidence/qa-r6-candidate-manifest-complete.sha256"
    selected = {line.split("  ", 1)[1] for line in old.read_text().splitlines()}
    for base in ("apps/api/src", "apps/web/src", "apps/web/tests", "apps/web/e2e",
                 "apps/web/public", "apps/api/.mvn", "content", "infra", "scripts",
                 "qa/phase10d-final-r4", "qa/phase10d-final-r5", "qa/phase10d-final-r6",
                 "qa/phase10d-final-r7"):
        folder = ROOT / base
        if folder.exists():
            selected.update(str(path.relative_to(ROOT)) for path in folder.rglob("*")
                            if path.is_file() and not {"evidence", "target", ".next", "node_modules", "__pycache__"}.intersection(path.relative_to(folder).parts)
                            and path.suffix in {".java", ".sql", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".sh", ".yml", ".yaml", ".json", ".xml", ".md"})
    selected.update(("AGENTS.md", "package.json", "package-lock.json", ".node-version",
                     "apps/api/pom.xml", "apps/api/mvnw", "apps/web/package.json",
                     "apps/web/next.config.ts", "apps/web/tsconfig.json",
                     "apps/web/playwright.config.ts", "docs/openapi.yaml"))
    selected = sorted(name for name in selected if (ROOT / name).is_file()
                      and not name.startswith((".local/", "output/")))
    manifest.write_text("".join(f"{sha(ROOT / name)}  {name}\n" for name in selected))
    old_diff = [name for line in old.read_text().splitlines()
                for expected, name in [line.split("  ", 1)]
                if not (ROOT / name).is_file() or sha(ROOT / name) != expected]
    record = {"runId": "qa-r7-" + uuid.uuid4().hex,
              "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "manifestSha256": sha(manifest), "count": len(selected),
              "r6InputDrift": old_diff, "runtimeJarSha256": sha(q.JAR),
              "java": subprocess.run([str(q.JAVA), "-version"], capture_output=True, text=True).stderr.splitlines()[0],
              "node": subprocess.check_output([q.NODE + "/node", "--version"], text=True).strip()}
    (OUT / "candidate-identity.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False))


def prepare():
    if q.SOURCE.exists():
        raise RuntimeError("R7 source copy already exists")
    names = [line.split("  ", 1)[1] for line in (OUT / "qa-r7-final-candidate.sha256").read_text().splitlines()]
    names = sorted(set(names) | set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()))
    for name in names:
        origin = ROOT / name
        if not origin.is_file() or name.startswith(("output/", ".local/")) or "/evidence/" in name:
            continue
        target = q.SOURCE / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    for name in ("node_modules", "apps/web/node_modules"):
        origin = ROOT / name
        if origin.exists() and not (q.SOURCE / name).exists():
            (q.SOURCE / name).symlink_to(origin, target_is_directory=True)
    for source, destination in (("qa/phase10d-final-r4/FinalQaFixture.java", "FinalQaFixture.java"),
                                ("qa/phase10d2-r5-fix/QueuePaginationQaFixture.java", "QueuePaginationQaFixture.java")):
        shutil.copy2(ROOT / source, q.SOURCE / "apps/api/src/test/java/local/northstar/knowledge" / destination)
    print("R7 source copy prepared", len(names))


def run(label, args, env=None, cwd=ROOT, timeout=600, check=True):
    identity = json.loads((OUT / "candidate-identity.json").read_text())
    run_id = identity["runId"] + "-" + uuid.uuid4().hex[:12]
    log = OUT / (run_id + "-" + label + ".log")
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    completed = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                               stdout=log.open("xb"), stderr=subprocess.STDOUT, timeout=timeout)
    record = {"runId": run_id, "case": label, "startedAt": start,
              "endedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "argv": [str(arg) for arg in args], "cwd": str(cwd),
              "exitCode": completed.returncode, "log": log.name, "logSha256": sha(log),
              "candidateManifestSha256": identity["manifestSha256"],
              "databaseUuid": q.identity()["uuid"] if (PRIVATE / "identity.json").exists() else None}
    with (OUT / "commands.jsonl").open("a") as journal:
        journal.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(label, "exit=" + str(completed.returncode), flush=True)
    if check and completed.returncode:
        raise RuntimeError(label + " failed; log retained at " + str(log))
    return completed.returncode


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "freeze":
        freeze()
    elif action == "prepare":
        prepare()
    elif action == "create":
        assert sha(q.JAR) == q.JAR_SHA
        q.create()
    elif action == "regressions":
        q.regressions()
    elif action == "seed":
        q.seed()
    else:
        raise ValueError(action)
