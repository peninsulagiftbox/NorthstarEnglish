#!/usr/bin/env python3
"""Real export/restore verification using only UUID-checked campaign containers."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import phase10e_environment as isolated
import local

r = isolated.r


@contextmanager
def api(env, label):
    assert local.available(int(env["API_PORT"]))
    log = (r.OUT / (label + "-api-" + str(time.time_ns()) + ".log")).open("xb")
    process = subprocess.Popen([str(Path(env["JAVA_HOME"]) / "bin/java"), "-jar",
        str(r.COPY / "apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"),
        "--northstar.content-root=" + env["NORTHSTAR_CONTENT_ROOT"],
        "--northstar.recording-root=" + env["NORTHSTAR_RECORDING_ROOT"]],
        env=env, cwd=r.COPY, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(150):
            assert process.poll() is None, "API failed; retained log: " + log.name
            try:
                if read(env, "/health")["migrationVersion"] == "013.04":
                    break
            except OSError:
                time.sleep(.3)
        else:
            raise RuntimeError("Isolated API readiness timeout")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        log.close()


def read(env, path):
    with urllib.request.urlopen("http://127.0.0.1:" + env["API_PORT"] + "/api/v1" + path, timeout=60) as response:
        return json.load(response)


def run():
    role = sys.argv[1] if len(sys.argv) > 1 else "lifecycle"
    target_role = sys.argv[2] if len(sys.argv) > 2 else "restore"
    isolated.prepare(target_role)
    source_media = isolated.STATE / role / "media"
    if (source_media / "demo-01/active.json").exists():
        shutil.copy2(r.ROOT / "content/demo-01/active.json", source_media / "demo-01/active.json")
    env = isolated.environment(role)
    stamp = time.strftime("%Y%m%d%H%M%S")
    schema = "northstar_restore_" + stamp
    backup = r.STATE / "backups" / stamp
    media = isolated.STATE / target_role / ("restored-media-" + stamp)
    if media.exists() and not (media / "CONTENT_INSTALLED").exists():
        raise RuntimeError("Restore media target is in an ambiguous incomplete state; retain for review")
    common = ["--phase10e-role", role, "--api", "http://127.0.0.1:" + env["API_PORT"],
              "--recording-root", env["NORTHSTAR_RECORDING_ROOT"]]
    with api(env, "backup-source"):
        r.record("content-backup", ["python3", str(r.ROOT / "scripts/data-transfer.py"),
            "backup", str(backup), *common, "--content-root", env["NORTHSTAR_CONTENT_ROOT"]], env=env, cwd=r.ROOT)
        original = json.loads(json.loads((backup / "learning.json").read_text())["payloadJson"])
        r.record("content-restore", ["python3", str(r.ROOT / "scripts/data-transfer.py"),
            "restore", str(backup / "learning.json"), *common, "--phase10e-target-role", target_role,
            "--target", schema, "--confirm-new-isolated", "--restore-content-root", str(media)], env=env, cwd=r.ROOT)
        r.record("content-restore-existing-rejected", ["python3", str(r.ROOT / "scripts/data-transfer.py"),
            "restore", str(backup / "learning.json"), *common, "--phase10e-target-role", target_role,
            "--target", schema, "--confirm-new-isolated", "--restore-content-root", str(media)],
            env=env, cwd=r.ROOT, expected=(1,))
    isolated.grant(target_role, [schema])
    restored = isolated.environment(target_role, schema)
    restored.update(NORTHSTAR_ALLOW_RESTORE_DB="true", NORTHSTAR_CONTENT_ROOT=str(media),
        NORTHSTAR_IMPORT_MEDIA_ROOT=str(media),
        NORTHSTAR_RECORDING_ROOT=str(Path(env["NORTHSTAR_RECORDING_ROOT"]) / schema))
    result = {"source": isolated.verify(role), "target": isolated.verify(target_role),
              "schema": schema, "backup": str(backup), "checks": []}
    with api(restored, "restored"):
        actual = json.loads(read(restored, "/data/export")["payloadJson"])
        assert actual["tables"] == original["tables"], "PK-ordered full table values differ after restore"
        result["checks"].append("all tables and generated-column values equal before new writes")
        manifest = json.loads((backup / "content-manifest.json").read_text())
        for entry in manifest["files"]:
            assert hashlib.sha256((media / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
        result["checks"].append("all content and original import files match backup SHA256")
        for lesson, count in [("sample-a", 12), ("sample-b", 24)]:
            assert len(read(restored, "/lessons/" + lesson)["sentences"]) == count
        result["checks"].append("restored A/B read through real API")
        r.record("restored-new-import", ["apps/api/mvnw", "-f", "apps/api/pom.xml",
            "-Dtest=ContentImportRestoreIntegrationTest", "test"], env=restored, cwd=r.COPY, timeout=600)
        assert len(read(restored, "/lessons/restored-new")["sentences"]) == 12
        result["checks"].append("new course applied, explicitly published, and read from restored API")
    result["passed"] = True
    (r.OUT / ("transfer-" + stamp + ".json")).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
