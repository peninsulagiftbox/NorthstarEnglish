#!/usr/bin/env python3
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r4", ROOT / "qa/phase10d-final-r4/run.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
q.TOOLS = TOOLS
q.OUT = TOOLS / "evidence"
q.PRIVATE = ROOT / ".local/qa-final-r5"
q.SOURCE = q.PRIVATE / "source"
q.NAME = "northstar-qa-final-r5-20261102"
q.API_PORT = 8192
q.WEB_PORT = 3199
q.API = "http://127.0.0.1:8192/api/v1"
q.WEB = "http://127.0.0.1:3199"
q.OUT.mkdir(parents=True, exist_ok=True)
q.PRIVATE.mkdir(parents=True, exist_ok=True)


def freeze():
    old = {}
    for line in (ROOT / "qa/phase10d-final-r4/evidence/qa-final-candidate-manifest.sha256").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        old[name] = checksum
    files = set(old)
    for folder in ("apps/api/src", "apps/web/src", "apps/web/tests", "apps/web/e2e", "scripts", "qa/phase10d-final-r5"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and not any(part in ("evidence", "__pycache__") for part in path.parts):
                files.add(str(path.relative_to(ROOT)))
    for name in ("qa/phase10d-final-r4/run.py", "qa/phase10d-final-r4/FinalQaFixture.java"):
        files.add(name)
    q.SOURCE.mkdir(exist_ok=False)
    current = {name: q.sha(ROOT / name) for name in sorted(files)}
    manifest = "".join(checksum + "  " + name + "\n" for name, checksum in current.items())
    (q.OUT / "qa-final-candidate-manifest.sha256").write_text(manifest)
    for name in current:
        destination = q.SOURCE / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    for name in ("node_modules", "apps/web/node_modules"):
        if (ROOT / name).exists():
            (q.SOURCE / name).symlink_to(ROOT / name, target_is_directory=True)
    for name, origin in (
        ("FinalQaFixture.java", ROOT / "qa/phase10d-final-r4/FinalQaFixture.java"),
        ("QueueQaFixture.java", TOOLS / "QueueQaFixture.java"),
    ):
        shutil.copy2(origin, q.SOURCE / "apps/api/src/test/java/local/northstar/knowledge" / name)
    q.save("candidate-identity.json", {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "inputCount": len(current), "manifestSha256": q.sha(q.OUT / "qa-final-candidate-manifest.sha256"),
        "changedFromR4": {name: {"before": checksum, "after": current[name]} for name, checksum in old.items() if current[name] != checksum},
        "runtimeJarSha256": q.sha(q.JAR), "sourceCopy": str(q.SOURCE),
    })
    assert q.sha(q.JAR) == q.JAR_SHA
    q.run("git-status", ["git", "status", "--short", "--untracked-files=all"])
    q.run("java-version", [q.JAVA, "-version"])
    q.run("node-version", [q.NODE + "/node", "--version"])
    q.run("npm-version", [q.NODE + "/npm", "--version"], env=q.env())
    q.save("migration-inputs.json", {path.name: q.sha(path) for path in sorted((q.SOURCE / "apps/api/src/main/resources/db/migration").glob("*.sql"))})
    print("FROZEN", len(current), flush=True)


def tests():
    q.regressions()
    q.run("seed-fixtures", ["bash", q.SOURCE / "apps/api/mvnw", "-f", q.SOURCE / "apps/api/pom.xml", "test", "-Dtest=FinalQaFixture,QueueQaFixture"], env=q.env())


if __name__ == "__main__":
    {"freeze": freeze, "create": q.create, "nodes": q.nodes, "tests": tests}[sys.argv[1]]()
