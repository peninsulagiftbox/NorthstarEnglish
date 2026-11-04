#!/usr/bin/env python3
"""M07 interruption safety: kill backup, restore and media copy; verify no false success."""

import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from run import q, OUT, PRIVATE, ROOT

TOOLS = Path(__file__).resolve().parent
RESULT = OUT / "r7-m07-interruption-result.json"
KEY_TABLES = ("lesson", "exercise_attempt", "personal_recording")


def probe(query):
    completed = subprocess.run([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(q.identity()["port"]),
                                "-uroot", "-N", "--batch", "--raw"], input="SELECT @@server_uuid;" + query,
                               capture_output=True, text=True, env=dict(os.environ, MYSQL_PWD=q.credentials()["root"]))
    assert completed.returncode == 0, completed.stderr[-300:]
    first, _, body = completed.stdout.partition("\n")
    assert first == q.identity()["uuid"]
    return body.rstrip("\n")


def counts(schema):
    result = {}
    for table in KEY_TABLES:
        try:
            result[table] = int(probe("SELECT COUNT(*) FROM `" + schema + "`.`" + table + "`"))
        except AssertionError:
            result[table] = None
    return result


def transfer(action, path, target=None):
    args = [sys.executable, str(TOOLS / "run_transfer.py"), action, str(path), "--phase10d",
            "--api", f"http://127.0.0.1:{q.API_PORT}", "--web-port", str(q.WEB_PORT),
            "--recording-root", str(PRIVATE / "recordings")]
    if target:
        args += ["--target", target, "--confirm-new-isolated"]
    return args


def stamp():
    time.sleep(1.05)
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")


def spawn(args):
    return subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run_transfer(args, timeout=300):
    return subprocess.run(args, cwd=ROOT, capture_output=True, timeout=timeout)


def schema_exists(target):
    return probe("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='" + target + "'") == "1"


def backup_kill():
    folder = PRIVATE / ("r7-backup-interrupt-" + stamp())
    process = spawn(transfer("backup", folder))
    killed = False
    for _ in range(12000):
        if process.poll() is not None:
            break
        if folder.is_dir():
            time.sleep(.02)
            process.kill()
            killed = True
            break
        time.sleep(.005)
    output = process.communicate()[0]
    assert killed and process.returncode == -9, (killed, process.returncode, output[-400:])
    assert not (folder / "COMPLETE").is_file()
    leftover = sorted(item.name for item in folder.iterdir())
    target = "northstar_restore_" + stamp()
    rejected = run_transfer(transfer("restore", folder / "learning.json", target), timeout=180)
    assert rejected.returncode == 1 and not schema_exists(target), rejected.stderr[-300:]
    assert not schema_exists(target)
    retry_folder = PRIVATE / ("r7-backup-retry-" + stamp())
    completed = run_transfer(transfer("backup", retry_folder), timeout=600)
    assert completed.returncode == 0 and b"PASS" in completed.stdout and (retry_folder / "COMPLETE").is_file(), completed.stdout[-400:]
    return {"scenario": "backup-interrupt", "interruptedAt": "backup folder created, before COMPLETE",
            "folderContentsAtKill": leftover, "processSignal": "SIGKILL", "exitCode": process.returncode,
            "completeWritten": False, "rejection": rejected.stderr.decode()[-120:].strip(),
            "restoreRejectedBeforeTarget": True, "rejectedExitCode": rejected.returncode,
            "retryBackup": retry_folder.name, "retryPassed": True}


def restore_kill(backup):
    target = "northstar_restore_" + stamp()
    process = spawn(transfer("restore", Path(backup) / "learning.json", target))
    killed = False
    tables = 0
    for _ in range(18000):
        if process.poll() is not None:
            break
        tables = int(probe("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='" + target + "'"))
        if tables > 0:
            time.sleep(.02)
            process.kill()
            killed = True
            break
        time.sleep(.01)
    output = process.communicate()[0]
    assert killed and process.returncode == -9, (killed, process.returncode, output[-400:])
    partial = counts(target)
    source = counts(q.SCHEMA)
    assert any(partial[table] is None or partial[table] < source[table] for table in KEY_TABLES), (partial, source)
    assert not (PRIVATE / "recordings" / target).exists()
    retry_target = "northstar_restore_" + stamp()
    completed = run_transfer(transfer("restore", Path(backup) / "learning.json", retry_target), timeout=900)
    assert completed.returncode == 0 and b"PASS" in completed.stdout, completed.stdout[-400:] + completed.stderr[-200:]
    assert counts(retry_target) == source
    return {"scenario": "restore-interrupt", "target": target, "tablesPresentAtKill": tables,
            "processSignal": "SIGKILL", "exitCode": process.returncode,
            "partialRowCounts": partial, "sourceRowCounts": source,
            "noMediaDirectory": True, "retryTarget": retry_target, "retryPassed": True,
            "retryCountsMatchSource": True}


def media_kill(backup):
    target = "northstar_restore_" + stamp()
    process = spawn(transfer("restore", Path(backup) / "learning.json", target))
    killed = False
    for _ in range(24000):
        if process.poll() is not None:
            break
        if (PRIVATE / "recordings" / target).is_dir():
            time.sleep(.01)
            process.kill()
            killed = True
            break
        time.sleep(.005)
    output = process.communicate()[0]
    assert killed and process.returncode == -9, (killed, process.returncode, output[-400:])
    manifest = json.loads((Path(backup) / "media-manifest.json").read_text())["recordings"]
    expected = sum(1 for item in manifest if item["included"])
    copied = list((PRIVATE / "recordings" / target).glob("*.audio"))
    retry_target = "northstar_restore_" + stamp()
    completed = run_transfer(transfer("restore", Path(backup) / "learning.json", retry_target), timeout=900)
    assert completed.returncode == 0 and b"PASS" in completed.stdout, completed.stdout[-400:]
    retry_files = list((PRIVATE / "recordings" / retry_target).glob("*.audio"))
    assert len(retry_files) == expected
    return {"scenario": "media-copy-interrupt", "target": target, "processSignal": "SIGKILL",
            "exitCode": process.returncode, "mediaFilesCopied": len(copied), "mediaExpected": expected,
            "interruptedBeforePass": True, "retryTarget": retry_target, "retryMediaFiles": len(retry_files),
            "retryPassed": True}


def main():
    valid = json.loads((OUT / "r7-data-transfer-result.json").read_text())["backup"]
    assert (Path(valid) / "COMPLETE").is_file()
    (PRIVATE / "ACTIVE_TEST_ROLE").write_text(".\n")
    before = {table: q.sql("SELECT * FROM " + table + " ORDER BY 1", label="m07-before-" + table)
              for table in KEY_TABLES}
    api = q.start_api()
    results = {}
    try:
        results["backupInterrupt"] = backup_kill()
        results["restoreInterrupt"] = restore_kill(valid)
        results["mediaInterrupt"] = media_kill(valid)
    finally:
        q.stop(api)
    after = {table: q.sql("SELECT * FROM " + table + " ORDER BY 1", label="m07-after-" + table)
             for table in KEY_TABLES}
    assert before == after
    results["sourceUnchanged"] = True
    results["status"] = "PASS"
    RESULT.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results))


if __name__ == "__main__":
    main()
