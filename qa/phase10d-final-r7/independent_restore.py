#!/usr/bin/env python3
"""Restore synthetic R7 data into a fresh MySQL container and separate volume."""

import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path

from run import q, OUT, PRIVATE, ROOT, run, sha

CASE = os.environ.get("R7_RESTORE_CASE", "first")
NAME = "northstar-qa-final-r7-restore" + ("" if CASE == "first" else "-" + CASE) + "-20261104"
VOLUME = NAME + "-data"
PORT = 3386 if CASE == "first" else 3397
TARGET = PRIVATE / ("independent-restore" if CASE == "first" else "independent-restore-" + CASE)
SCHEMA = "northstar_phase01_test"


def mysql(sql, identity, password, label):
    command = [q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(identity["port"]),
               "-uroot", "-N", "--batch", "--raw"]
    completed = subprocess.run(command, input="SELECT @@server_uuid;" + sql, text=True,
                               capture_output=True, env=dict(os.environ, MYSQL_PWD=password))
    first, _, body = completed.stdout.partition("\n")
    assert first == identity["uuid"] and completed.returncode == 0, (label, completed.returncode, completed.stderr[-300:])
    return body.rstrip("\n")


def create():
    assert not TARGET.exists() and q.identity()["uuid"] != ""
    assert subprocess.run([q.DOCKER, "inspect", NAME], capture_output=True).returncode != 0
    assert subprocess.run([q.DOCKER, "volume", "inspect", VOLUME], capture_output=True).returncode != 0
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", PORT))
    TARGET.mkdir(mode=0o700)
    secret = secrets.token_hex(32)
    (TARGET / "credentials.json").write_text(json.dumps({"root": secret}))
    (TARGET / "credentials.json").chmod(0o600)
    run("r7-restore-create-volume", [q.DOCKER, "volume", "create", "--label", "northstar.qa=final-r7-restore", VOLUME])
    env = dict(os.environ, MYSQL_ROOT_PASSWORD=secret)
    started = subprocess.run([q.DOCKER, "run", "--pull=never", "-d", "--name", NAME,
                              "--label", "northstar.qa=final-r7-restore", "--restart=no",
                              "--memory=1g", "--cpus=2", "-p", f"127.0.0.1:{PORT}:3306",
                              "-e", "MYSQL_ROOT_PASSWORD", "-v", VOLUME + ":/var/lib/mysql",
                              q.IMAGE, "--default-time-zone=+00:00"],
                             capture_output=True, text=True, env=env)
    assert started.returncode == 0, started.stderr
    cid = started.stdout.strip()
    for _ in range(100):
        ready = subprocess.run([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(PORT),
                                "-uroot", "-N", "-e", "SELECT VERSION(),@@server_uuid"],
                               capture_output=True, text=True, env=dict(os.environ, MYSQL_PWD=secret))
        if ready.returncode == 0:
            break
        time.sleep(.5)
    assert ready.returncode == 0
    version, database_uuid = ready.stdout.strip().split("\t")
    source = q.identity()
    assert database_uuid != source["uuid"] and VOLUME != source["volume"] and PORT != source["port"]
    identity = {"name": NAME, "containerId": cid, "volume": VOLUME, "port": PORT,
                "uuid": database_uuid, "mysqlVersion": version, "sourceUuid": source["uuid"],
                "sourceVolume": source["volume"], "sourcePort": source["port"],
                "mediaRoot": str(TARGET / "recordings")}
    (TARGET / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (OUT / (NAME + "-identity.json")).write_text(json.dumps(identity, indent=2) + "\n")
    mounts = subprocess.check_output([q.DOCKER, "inspect", "--format", "{{json .Mounts}}", cid], text=True)
    assert any(m.get("Name") == VOLUME and m.get("Destination") == "/var/lib/mysql" for m in json.loads(mounts))
    print(json.dumps(identity))


def restore():
    identity = json.loads((TARGET / "identity.json").read_text())
    assert identity["name"] == NAME and identity["port"] == PORT and identity["volume"] == VOLUME
    secret = json.loads((TARGET / "credentials.json").read_text())["root"]
    assert mysql("", identity, secret, "r7-target-uuid") == ""
    assert not mysql("SELECT schema_name FROM information_schema.schemata WHERE schema_name='" + SCHEMA + "';",
                     identity, secret, "r7-target-empty")
    backup_record = "r7-data-transfer-result.json" if CASE == "first" else "r7-data-transfer-" + CASE + "-result.json"
    backup = json.loads((OUT / backup_record).read_text())["backup"]
    media = Path(backup) / "media"
    manifest = json.loads((Path(backup) / "media-manifest.json").read_text())["recordings"]
    assert manifest and all(item["included"] for item in manifest)
    dump = TARGET / "source.sql"
    source = q.identity()
    command = [q.DOCKER, "exec", source["containerId"], "sh", "-c",
               'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --routines --triggers --events --no-tablespaces --set-gtid-purged=OFF ' + SCHEMA]
    with dump.open("xb") as output:
        completed = subprocess.run(command, stdout=output, stderr=subprocess.PIPE)
    assert completed.returncode == 0, completed.stderr[-300:]
    assert dump.stat().st_size > 0
    mysql("CREATE DATABASE `" + SCHEMA + "` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;", identity, secret, "create-target-schema")
    with dump.open("rb") as source_file:
        imported = subprocess.run([q.MYSQL, "--protocol=TCP", "-h127.0.0.1", "-P" + str(PORT),
                                   "-uroot", SCHEMA], stdin=source_file, capture_output=True,
                                  env=dict(os.environ, MYSQL_PWD=secret))
    assert imported.returncode == 0, imported.stderr[-500:]
    media_root = TARGET / "recordings" / SCHEMA
    media_root.mkdir(parents=True, mode=0o700)
    for item in manifest:
        origin = media / (item["id"] + ".audio")
        destination = media_root / origin.name
        shutil.copy2(origin, destination)
        assert sha(destination) == item["sha256"] and destination.stat().st_size == int(item["byte_size"])
    shutil.copytree(PRIVATE / "content", TARGET / "content")
    app = q.credentials()["app"]
    migrator = q.credentials()["migrator"]
    mysql("CREATE USER 'northstar_app'@'%' IDENTIFIED BY '" + app + "'; "
          "CREATE USER 'northstar_migrator'@'%' IDENTIFIED BY '" + migrator + "'; "
          "GRANT SELECT,INSERT,UPDATE,DELETE ON `" + SCHEMA + "`.* TO 'northstar_app'@'%'; "
          "GRANT ALL ON `" + SCHEMA + "`.* TO 'northstar_migrator'@'%'; "
          "SET GLOBAL log_bin_trust_function_creators=1;", identity, secret, "target-grants")
    tables = q.sql("SHOW TABLES", label="r7-source-table-list").splitlines()
    assert len(tables) > 40
    hashes = {}
    for table in tables:
        query = "SELECT * FROM `" + SCHEMA + "`.`" + table + "` ORDER BY 1;"
        source_rows = q.sql(query, label="r7-source-compare-" + table)
        target_rows = mysql(query, identity, secret, "r7-target-compare-" + table)
        assert source_rows == target_rows, table
        hashes[table] = hashlib.sha256(source_rows.encode()).hexdigest()
    history = mysql("SELECT version,description,checksum,success FROM `" + SCHEMA + "`.flyway_schema_history ORDER BY installed_rank;",
                    identity, secret, "r7-target-history")
    assert history.splitlines()[-1].startswith("012.11\t")
    result = {"status": "PASS", "sourceUuid": source["uuid"], "targetUuid": identity["uuid"],
              "sourceVolume": source["volume"], "targetVolume": identity["volume"],
              "tableCount": len(tables), "tableRowHashes": hashes,
              "recordings": [{"id": item["id"], "sha256": item["sha256"], "byteSize": item["byte_size"]} for item in manifest],
              "generatedColumnRows": mysql("SELECT COUNT(*) FROM `" + SCHEMA + "`.knowledge_occurrence WHERE location_guard IS NOT NULL;", identity, secret, "generated-column-count"),
              "dumpSha256": sha(dump), "historySha256": hashlib.sha256(history.encode()).hexdigest()}
    result_name = "r7-independent-restore-result.json" if CASE == "first" else "r7-independent-restore-" + CASE + "-result.json"
    (OUT / result_name).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "tableRowHashes"}))


if __name__ == "__main__":
    {"create": create, "restore": restore}[__import__("sys").argv[1]]()
