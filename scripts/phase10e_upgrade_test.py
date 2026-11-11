#!/usr/bin/env python3
"""Frozen V012 backup upgrade and retained failed migration targets."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import phase10e_environment as isolated

r = isolated.r
schema = "northstar_phase01_test"


def migrate(role, target=None, expected=(0,)):
    env = isolated.environment(role)
    classes = r.COPY / "apps/api/target"
    classpath = str(classes / "classes") + os.pathsep + (classes / "import-classpath.txt").read_text().strip()
    return r.record("upgrade-" + role, [str(Path(env["JAVA_HOME"]) / "bin/java"), "-cp", classpath,
        str(r.ROOT / "scripts/phase10e/Migrate.java"), *([target] if target else [])],
        env=env, cwd=r.COPY, timeout=600, expected=expected)


def snapshot(role, tables=None):
    if tables is None:
        tables = isolated.sql(role, "SHOW TABLES", schema=schema).decode().splitlines()
    result = {}
    for table in tables:
        keys = isolated.sql(role, "SELECT column_name FROM information_schema.key_column_usage "
            f"WHERE table_schema='{schema}' AND table_name='{table}' AND constraint_name='PRIMARY' "
            "ORDER BY ordinal_position").decode().splitlines()
        rows = isolated.sql(role, "SELECT * FROM `" + table + "`"
            + (" WHERE version NOT LIKE '013.%'" if table == "flyway_schema_history" else "")
            + " ORDER BY " + ",".join("`" + key + "`" for key in keys), schema=schema)
        result[table] = hashlib.sha256(rows).hexdigest()
    return result


def main():
    source = "upgrade-source-" + str(time.time_ns())
    isolated.prepare(source)
    migrate(source, "012.12")
    isolated.grant(source)
    env = isolated.environment(source)
    shutil.copytree(r.ROOT / "content", Path(env["NORTHSTAR_CONTENT_ROOT"]), dirs_exist_ok=True)
    r.record("upgrade-old-seed", [str(Path(env["JAVA_HOME"]) / "bin/java"), "-jar",
        str(r.COPY / "apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar"),
        "--spring.main.web-application-type=none", "--spring.flyway.target=012.12",
        "--northstar.initialize-content=true", "--northstar.content-root=" + env["NORTHSTAR_CONTENT_ROOT"]],
        env=env, cwd=r.COPY, timeout=180)
    before = snapshot(source)
    frozen = r.STATE / "backups" / ("v012-" + str(time.time_ns()) + ".sql")
    frozen.parent.mkdir(exist_ok=True, parents=True)
    data = isolated.docker("exec", isolated.verify(source)["container"], "sh", "-c",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --skip-add-drop-table '
        '--no-tablespaces --set-gtid-purged=OFF --single-transaction '
        '--ignore-table=northstar_phase01_test.project_identity ' + schema)
    with os.fdopen(os.open(frozen, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        output.write(data)
    created = isolated.sql(source, "SELECT created_at FROM project_identity", schema=schema).decode().strip()
    results = {"backupSha256": hashlib.sha256(data).hexdigest(), "before": before, "targets": {}}
    suffix = str(time.time_ns())
    for base_role in ["upgrade-restored", "upgrade-ddl-fault", "upgrade-history-fault", "upgrade-recovered"]:
        role = base_role + "-" + suffix
        isolated.prepare(role)
        isolated.sql(role, data.decode(), schema=schema)
        isolated.sql(role, "UPDATE project_identity SET created_at='" + created + "'", schema=schema)
        assert snapshot(role) == before
        shutil.copytree(Path(env["NORTHSTAR_CONTENT_ROOT"]), isolated.STATE / role / "media", dirs_exist_ok=True)
        if role == "upgrade-ddl-fault":
            isolated.sql(role, "CREATE TABLE import_entry(injected INT PRIMARY KEY)", schema=schema)
            migrate(role, expected=(1,))
            failed = isolated.sql(role, "SELECT version,success FROM flyway_schema_history WHERE success=0", schema=schema).decode()
            assert "013.02" in failed
            migrate(role, expected=(1,))
            results["targets"][role] = {"detected": True, "failedHistory": failed, "retained": True}
        elif role == "upgrade-history-fault":
            isolated.sql(role, "UPDATE flyway_schema_history SET checksum=checksum+1 WHERE version='012.12'", schema=schema)
            migrate(role, expected=(1,))
            assert isolated.sql(role, "SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_schema='{schema}' AND table_name='import_batch'").decode().strip() == "0"
            results["targets"][role] = {"checksumMismatchRejectedBeforeDDL": True, "retained": True}
        else:
            migrate(role)
            after = snapshot(role, before)
            assert before == after
            old_files = {str(path.relative_to(Path(env["NORTHSTAR_CONTENT_ROOT"]))): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in Path(env["NORTHSTAR_CONTENT_ROOT"]).rglob("*") if path.is_file()}
            target_files = {str(path.relative_to(isolated.STATE / role / "media")): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (isolated.STATE / role / "media").rglob("*") if path.is_file()}
            assert old_files == target_files
            results["targets"][role] = {"allOldTablesEqual": True, "oldMediaEqual": True,
                "migration": "013.04", "identity": isolated.verify(role)}
    results["passed"] = True
    results["recoveryPolicy"] = "Retain anomalous targets; restore frozen old backup into another new container. No automatic repair or checksum rewrite."
    (r.OUT / "upgrade-result.json").write_text(json.dumps(results, indent=2))
    print("PASS: frozen V012 restored/upgraded, old PK values/media unchanged, DDL/history failures rejected, independent recovery.")


if __name__ == "__main__":
    main()
