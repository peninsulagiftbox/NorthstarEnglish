#!/usr/bin/env python3
"""Use a second new container for independent R6 browser regression."""

import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "qa/phase10d-final-r6/run.py"
spec = importlib.util.spec_from_file_location("r6_base", BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
q = base.q
q.TOOLS = Path(__file__).resolve().parent
q.OUT = q.TOOLS / "evidence"
q.PRIVATE = ROOT / ".local/qa-browser-r6"
q.SOURCE = ROOT / ".local/qa-final-r6/source"
q.NAME = "northstar-qa-browser-r6-20261103"
q.API_PORT = 8200
q.WEB_PORT = 3207
q.API = f"http://127.0.0.1:{q.API_PORT}/api/v1"
q.WEB = f"http://127.0.0.1:{q.WEB_PORT}"
q.OUT.mkdir(parents=True, exist_ok=True)
q.PRIVATE.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / "qa/phase10d-final-r6/evidence/candidate-identity.json",
             q.OUT / "candidate-identity.json") if not (q.OUT / "candidate-identity.json").exists() else None


def seed():
    q.run("r6-browser-seed", ["bash", q.SOURCE / "apps/api/mvnw", "-f",
          q.SOURCE / "apps/api/pom.xml", "test",
          "-Dtest=FinalQaFixture,QueuePaginationQaFixture"], env=q.env())


if __name__ == "__main__":
    {"create": q.create, "nodes": q.nodes, "seed": seed}[sys.argv[1]]()
