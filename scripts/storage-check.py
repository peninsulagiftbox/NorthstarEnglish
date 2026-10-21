#!/usr/bin/env python3
"""Phase01 storage probe. Changes test settings only; never resets data."""
import json
from pathlib import Path
import subprocess
import sys
import local

env = local.environment()
local.verify_container(env)


def sql(query):
    # Expand secrets only within the verified container, never into argv or logs.
    result = subprocess.run(["docker", "exec", "-i", "northstar-english-mysql-01", "sh", "-c",
                             'MYSQL_PWD="$DB_MIGRATION_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -unorthstar_migrator --batch --skip-column-names'],
                            input=query, text=True, capture_output=True, check=True)
    return result.stdout


def snapshot():
    return {name: sql(f"SELECT JSON_OBJECT('timezone',timezone,'rowVersion',row_version,'createdAt',created_at,'updatedAt',updated_at) FROM {name}.user_setting WHERE owner_key='local';\n"
                      f"SELECT installed_rank,version,checksum,installed_on,success FROM {name}.flyway_schema_history ORDER BY installed_rank;\n"
                      f"SELECT project_key,created_at FROM {name}.project_identity;\n")
            for name in ("northstar_english", "northstar_phase01_test")}


path = local.LOCAL / "storage-before.json"
if sys.argv[1] == "prepare":
    sql("UPDATE northstar_phase01_test.user_setting SET timezone='Europe/London',row_version=row_version+1,updated_at=UTC_TIMESTAMP(3) WHERE owner_key='local';")
    path.write_text(json.dumps(snapshot(), indent=2))
    print("PASS: saved both schemas' settings/identity/history; incremented test setting only")
elif sys.argv[1] == "verify":
    before = json.loads(path.read_text())
    assert before == snapshot(), "Settings, project identity or migration history changed"
    print("PASS: both schemas' settings/identity/history survived restart unchanged")
else:
    raise SystemExit("usage: storage-check.py prepare|verify")
