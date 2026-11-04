#!/usr/bin/env python3
"""Record an immutable R6 candidate and independent command results."""

import datetime
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qa/phase10d-final-r6/evidence"
NODE = Path("/opt/homebrew/opt/node@22/bin")
SKIP_DIRS = {".next", "target", "node_modules", "evidence", "__pycache__"}
INPUT_DIRS = [
    "apps/api/src", "apps/web/src", "apps/web/tests", "apps/web/e2e",
    "apps/web/public", "apps/api/.mvn", "content", "infra",
    "qa/phase10d2-r5-fix", "qa/phase10d-final-r4", "qa/phase10d-final-r5",
]
INPUT_FILES = [
    "AGENTS.md", "package.json", "package-lock.json", ".node-version",
    "apps/web/package.json", "apps/web/next.config.ts", "apps/web/tsconfig.json",
    "apps/web/playwright.config.ts", "apps/api/pom.xml", "apps/api/mvnw",
    "scripts/data-transfer.py", "docs/openapi.yaml",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    files = {ROOT / name for name in INPUT_FILES if (ROOT / name).is_file()}
    for name in INPUT_DIRS:
        base = ROOT / name
        if base.exists():
            files.update(path for path in base.rglob("*") if path.is_file()
                         and not SKIP_DIRS.intersection(path.relative_to(base).parts))
    return sorted(files)


def freeze():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    manifest = EVIDENCE / "qa-r6-candidate-manifest.sha256"
    if manifest.exists():
        raise RuntimeError("R6 manifest already exists; use a fresh run directory")
    manifest.write_text("".join(f"{digest(path)}  {path.relative_to(ROOT)}\n" for path in inputs()))
    old = ROOT / "qa/phase10d2-r5-fix/evidence/qa-final-candidate-manifest.sha256"
    drift = []
    for line in old.read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            drift.append({"path": name, "reason": "missing" if not path.is_file() else "sha256 differs"})
    jar = ROOT / "output/review/northstar-phase10d2-r5-fix-candidate.jar"
    identity = {
        "runId": "qa-r6-" + uuid.uuid4().hex,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "candidateManifestSha256": digest(manifest),
        "candidateManifestEntries": len(manifest.read_text().splitlines()),
        "r5ManifestSha256": digest(old), "r5ManifestDrift": drift,
        "runtimeJarSha256": digest(jar),
        "node": subprocess.check_output([NODE / "node", "--version"], text=True).strip(),
    }
    (EVIDENCE / "candidate-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(json.dumps(identity, indent=2))


def execute(label, argv):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    identity = json.loads((EVIDENCE / "candidate-identity.json").read_text())
    run_id = identity["runId"] + "-" + uuid.uuid4().hex[:12]
    log = EVIDENCE / f"{run_id}-{label}.log"
    env = os.environ.copy()
    env["PATH"] = str(NODE) + os.pathsep + env["PATH"]
    env["JAVA_HOME"] = str(ROOT / ".local/jdk21/jdk-21.0.12.1+1/Contents/Home")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open("xb") as output:
        completed = subprocess.run(argv, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
    record = {
        "runId": run_id, "case": label, "startedAt": started,
        "endedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": argv, "cwd": str(ROOT), "exitCode": completed.returncode,
        "log": log.name, "logSha256": digest(log),
        "candidateManifestSha256": identity["candidateManifestSha256"],
    }
    with (EVIDENCE / "commands.jsonl").open("a") as journal:
        journal.write(json.dumps(record) + "\n")
    print(json.dumps(record))
    return completed.returncode


if __name__ == "__main__":
    if sys.argv[1] == "freeze":
        freeze()
    elif sys.argv[1] == "node":
        for case in ("test", "typecheck", "lint", "build"):
            if execute("node-" + case, [str(NODE / "npm"), "run", case]):
                sys.exit(1)
    elif sys.argv[1] == "run":
        sys.exit(execute(sys.argv[2], sys.argv[3:]))
