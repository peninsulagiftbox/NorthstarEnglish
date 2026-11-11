#!/usr/bin/env python3
"""Isolated build and evidence journal for Phase 10E."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import phase10b2 as runner

runner.STATE = runner.ROOT / ".local/phase10e"
runner.COPY = runner.STATE / "source"
runner.OUT = runner.ROOT / "docs/handoff/evidence/phase10e"
original_record = runner.record


def record(name, argv, **kwargs):
    entries = {}
    for prefix, base in [("build", runner.COPY), ("live", runner.ROOT)]:
        for folder in ["apps/api/src", "apps/web/src", "scripts", "infra"]:
            if prefix == "live" and folder != "scripts":
                continue
            for path in sorted((base / folder).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc"}:
                    entries[prefix + "/" + str(path.relative_to(base))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name_in_copy in ["apps/api/pom.xml", "package.json", "package-lock.json",
                         "apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar", "apps/web/.next/BUILD_ID"]:
        path = runner.COPY / name_in_copy
        if path.is_file():
            entries["build/" + name_in_copy] = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = json.dumps(entries, sort_keys=True, indent=2).encode()
    sha = hashlib.sha256(raw).hexdigest()
    folder = runner.OUT / "candidates"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (sha + ".json")).write_bytes(raw)
    with (runner.OUT / "candidate-bindings.jsonl").open("a") as output:
        output.write(json.dumps({"command": name, "candidateSha256": sha}) + "\n")
    return original_record(name, argv, **kwargs)


runner.record = record


def baseline():
    runner.OUT.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=runner.ROOT
    ).decode().split("\0")
    entries = {}
    for name in paths:
        if name and name.startswith(("apps/", "scripts/", "infra/", "content/")):
            path = runner.ROOT / name
            if path.is_file():
                entries[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    destination = runner.OUT / "baseline-sha256.json"
    with destination.open("x") as output:
        json.dump(entries, output, indent=2, sort_keys=True)
    print(f"Frozen {len(entries)} baseline files")


if __name__ == "__main__":
    if sys.argv[1:] == ["baseline"]:
        baseline()
    elif sys.argv[1:] == ["sync"]:
        runner.sync()
    elif len(sys.argv) >= 4 and sys.argv[1] == "run":
        runner.record(sys.argv[2], sys.argv[3:], cwd=runner.COPY)
    else:
        raise SystemExit("baseline | sync | run NAME COMMAND...")
