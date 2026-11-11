#!/usr/bin/env python3
"""Offline source commands or standalone Java import CLI; never boots Spring."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if len(sys.argv) < 2:
    raise SystemExit("inspect | extract | review | validate | dry-run | apply | publish | status | resume | verify")
if sys.argv[1] in {"inspect", "extract", "review"}:
    command = [sys.executable, str(root / "scripts/content_source.py"), *sys.argv[1:]]
else:
    runtime = Path(os.environ.get("NORTHSTAR_IMPORT_RUNTIME", root / "apps/api/target"))
    dependencies = runtime / "import-classpath.txt"
    if not dependencies.is_file():
        raise SystemExit("先编译并运行 Maven dependency:build-classpath -Dmdep.outputFile=target/import-classpath.txt")
    java = str(Path(os.environ["JAVA_HOME"]) / "bin/java") if "JAVA_HOME" in os.environ else "java"
    command = [java, "-cp", str(runtime / "classes") + os.pathsep + dependencies.read_text().strip(),
               "local.northstar.catalog.ContentImportCli", *sys.argv[1:]]
raise SystemExit(subprocess.call(command))
