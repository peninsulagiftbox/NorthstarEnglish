#!/usr/bin/env python3
"""R5-fix independent acceptance: fresh isolated database for the concept queue pagination fix."""
import importlib.util
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r4", ROOT / "qa/phase10d-final-r4/run.py")
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
q.TOOLS = TOOLS
q.OUT = TOOLS / "evidence"
q.PRIVATE = ROOT / ".local/qa-final-r5fix"
q.SOURCE = q.PRIVATE / "source"
q.NAME = "northstar-qa-final-r5fix-20261103"
q.API_PORT = 8194
q.WEB_PORT = 3201
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
q.JAR = ROOT / "output/review/northstar-phase10d2-r5-fix-candidate.jar"
q.JAR_SHA = "771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6"
q.OUT.mkdir(parents=True, exist_ok=True)
q.PRIVATE.mkdir(parents=True, exist_ok=True)


def git_inputs():
    status = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, text=True)
    paths = set()
    for line in status.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and (ROOT / path).is_file():
            paths.add(path)
    return sorted(path for path in paths if not path.startswith("qa/phase10d2-r5-fix/evidence/"))


def freeze():
    inputs = git_inputs()
    print("FREEZE hashing", len(inputs), "inputs", flush=True)
    manifest = "".join(q.sha(ROOT / name) + "  " + name + "\n" for name in inputs)
    (q.OUT / "qa-final-candidate-manifest.sha256").write_text(manifest)
    tracked = [p for p in subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines() if p and (ROOT / p).is_file()]
    print("FREEZE copying", len(set(inputs) | set(tracked)), "files", flush=True)
    q.SOURCE.mkdir(exist_ok=True)
    for name in sorted(set(inputs) | set(tracked)):
        destination = q.SOURCE / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    print("FREEZE source copy done", flush=True)
    for name in ("node_modules", "apps/web/node_modules"):
        if (ROOT / name).exists() and not (q.SOURCE / name).exists():
            (q.SOURCE / name).symlink_to(ROOT / name, target_is_directory=True)
    for origin, name in ((ROOT / "qa/phase10d-final-r4/FinalQaFixture.java", "FinalQaFixture.java"),
                         (TOOLS / "QueuePaginationQaFixture.java", "QueuePaginationQaFixture.java")):
        shutil.copy2(origin, q.SOURCE / "apps/api/src/test/java/local/northstar/knowledge" / name)
    print("FREEZE fixtures copied", flush=True)
    q.save("candidate-identity.json", {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "manifestScope": "all uncommitted and untracked files from git status",
        "inputCount": len(inputs), "trackedSourceCount": len(tracked),
        "manifestSha256": q.sha(q.OUT / "qa-final-candidate-manifest.sha256"),
        "runtimeJar": str(q.JAR.relative_to(ROOT)), "runtimeJarSha256": q.JAR_SHA,
        "jarNote": "API candidate bytes identical to the R5 runtime jar; this round changes web code only.",
        "sourceCopy": str(q.SOURCE),
    })
    q.run("git-status-frozen", ["git", "status", "--short", "--untracked-files=all"])
    q.run("java-version", [q.JAVA, "-version"])
    q.run("node-version", [q.NODE + "/node", "--version"])
    q.run("npm-version", [q.NODE + "/npm", "--version"], env=q.env())
    q.save("migration-inputs.json", {p.name: q.sha(p) for p in sorted((q.SOURCE / "apps/api/src/main/resources/db/migration").glob("*.sql"))})
    print("FROZEN", len(inputs), "uncommitted inputs,", len(tracked), "tracked source files", flush=True)


def seed():
    q.run("seed-original-fixture", ["bash", q.SOURCE / "apps/api/mvnw", "-f", q.SOURCE / "apps/api/pom.xml",
                                    "test", "-Dtest=FinalQaFixture,QueuePaginationQaFixture"], env=q.env())


if __name__ == "__main__":
    {"freeze": freeze, "create": q.create, "nodes": q.nodes, "regressions": q.regressions, "seed": seed}[__import__("sys").argv[1]]()
