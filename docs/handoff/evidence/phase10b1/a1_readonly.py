#!/usr/bin/env python3
"""Bounded source metadata reads. No Spring, DDL, DML, backup or service control."""
import datetime
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import zlib

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / 'recovery-20261027/a1'
CONTAINER = 'bbf8c3f55c023dd7e16377417e31b54c742cb3ecf109fd57f22c152babc58fd0'
DOCKER = '/Applications/Docker.app/Contents/Resources/bin/docker'
SCHEMA = 'northstar_english'
PROJECT = 'northstar-english-local-v1'
RECORDS = []


def write(name, value):
    path = OUT / name
    with path.open('x') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    path.chmod(0o600)


def run(argv, sql=None, private=False, allowed=(0,)):
    record = dict(argv=argv, started=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat())
    if sql:
        record['stdinSql'] = sql
    try:
        p = subprocess.run(argv, input=sql, capture_output=True, text=True, timeout=20, cwd=ROOT)
        record.update(returncode=p.returncode, stderr=p.stderr,
                      stdout='[private metadata processed in memory; not persisted]' if private else p.stdout)
        RECORDS.append(record)
        if p.returncode not in allowed:
            raise RuntimeError('Read-only command failed; see commands.json')
        return p.stdout
    except subprocess.TimeoutExpired:
        record.update(returncode=None, stderr='TIMEOUT; exit code unavailable')
        RECORDS.append(record)
        raise RuntimeError('Read-only command timed out')


def sql(query, migrator=False, private=False):
    account = 'northstar_migrator' if migrator else 'northstar_app'
    variable = 'DB_MIGRATION_PASSWORD' if migrator else 'DB_PASSWORD'
    # Password stays inside the container; never in argv, stdin SQL or host logs.
    shell = 'MYSQL_PWD="$' + variable + '" exec mysql --protocol=TCP -h127.0.0.1 -u' + account + ' --database=northstar_english --batch --raw --skip-column-names'
    return run([DOCKER, 'exec', '-i', CONTAINER, 'sh', '-c', shell],
               'START TRANSACTION READ ONLY;\n' + query + ';\nROLLBACK;\n', private)


def identity(migrator=False):
    value = json.loads(sql("SELECT JSON_OBJECT('serverUuid',@@server_uuid,'schema',DATABASE(),'login',USER(),'account',CURRENT_USER(),'mysqlVersion',VERSION(),'project',(SELECT project_key FROM project_identity))", migrator))
    assert value['schema'] == SCHEMA and value['project'] == PROJECT, 'Source identity mismatch'
    assert value['account'] == ('northstar_migrator@%' if migrator else 'northstar_app@%'), 'Account mismatch'
    return value


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continue-after-history', action='store_true')
    args = parser.parse_args()
    if args.continue_after_history:
        OUT = OUT.parent / 'a1-continuation'
    OUT.mkdir(mode=0o700, exist_ok=False)
    try:
        item = json.loads(run([DOCKER, 'inspect', '--format',
            '{"id":{{json .Id}},"name":{{json .Name}},"labels":{{json .Config.Labels}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}},"status":{{json .State.Status}}}', CONTAINER]))
        assert item['id'] == CONTAINER and item['name'] == '/northstar-english-mysql-01'
        assert item['labels']['local.northstar.project'] == PROJECT
        assert item['labels']['com.docker.compose.project'] == 'northstar-english-local-01'
        assert item['ports']['3306/tcp'] == [{'HostIp':'127.0.0.1','HostPort':'3308'}]
        assert any(m.get('Name') == 'northstar_english_mysql_01_data' and m['Destination'] == '/var/lib/mysql' for m in item['mounts'])
        assert item['status'] == 'running'
        source = identity()
        write('identity.json', source)
        if args.continue_after_history:
            old = json.loads((OUT.parent / 'a1/identity.json').read_text())
            assert source == old, 'Identity changed since first read'
            history = json.loads((OUT.parent / 'a1/flyway-history.json').read_text())
        else:
            grants = sql('SHOW GRANTS FOR CURRENT_USER')
            other = identity(True)
            assert other['serverUuid'] == source['serverUuid']
            write('grants.json', dict(app=grants, migrator=sql('SHOW GRANTS FOR CURRENT_USER', True), migratorIdentity=other,
                  note='Accounts may have write privileges. This probe uses explicit READ ONLY transactions; no privilege changes.'))
            history = [json.loads(line) for line in sql("SELECT JSON_OBJECT('rank',installed_rank,'version',version,'description',description,'type',type,'script',script,'checksum',checksum,'installedBy',installed_by,'installedOn',installed_on,'executionTime',execution_time,'success',success) FROM flyway_schema_history ORDER BY installed_rank").splitlines()]
        write('flyway-history.json', history)
        markers = [x for x in history if x['type'] == 'BASELINE']
        assert len(markers) <= 1 and all(x['version'] == '0' and x['success'] == 1 for x in markers), 'Unexpected history marker'
        history = [x for x in history if x['type'] != 'BASELINE']
        assert len(history) == 8 and [x['version'] for x in history] == [f'{n:03}' for n in range(1,9)], 'Unexpected SQL migration chain'
        for row in history:
            assert row['success'] == 1 and row['type'] == 'SQL'
            p = ROOT / 'apps/api/src/main/resources/db/migration' / row['script']
            crc = 0
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                crc = zlib.crc32(line.encode('utf-8'), crc)
            signed = crc if crc < 2**31 else crc - 2**32
            assert signed == row['checksum'], 'Migration checksum mismatch'
        write('flyway-check.json', dict(status='PASS', method='Compare stored history to local UTF-8 line CRC32; not a Flyway validate invocation', count=8))
        columns = sql("SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='user_setting' ORDER BY ORDINAL_POSITION")
        write('v008-columns.json', dict(columns=columns))
        assert 'recording_enabled\ttinyint(1)\tNO\t1' in columns, 'V008 column mismatch'
        tables = sql('SHOW TABLES').splitlines()
        schemas = {}
        counts = {}
        for name in tables:
            assert re.fullmatch('[a-z_]+', name)
            schemas[name] = sql('SHOW CREATE TABLE `' + name + '`')
            counts[name] = int(sql('SELECT COUNT(*) FROM `' + name + '`').strip())
        write('schema.json', schemas)
        write('row-counts.json', dict(counts=counts, consistentSnapshot=False,
              note='Services were not paused; counts taken in separate READ ONLY transactions. Not a backup or integrity baseline.'))
        sizes = sql('SELECT COALESCE(SUM(DATA_LENGTH+INDEX_LENGTH),0),COALESCE(SUM(DATA_LENGTH),0) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()')
        write('storage.json', dict(informationSchemaAllocatedAndDataBytes=sizes, diskFreeBytes=shutil.disk_usage(ROOT).free,
            exactSqlBackupBytes='NOT VERIFIED', fullMediaAndReplicaBudget='NOT VERIFIED'))
        write('app-db-sessions.json', dict(sessions=sql("SELECT ID,USER,HOST,DB,COMMAND FROM information_schema.PROCESSLIST WHERE USER='northstar_app'"),
             scope='Only sessions visible to app account; no query text collected'))
        # Inspect only recorded project service subtrees; never save process environments or full argv.
        processes = []
        for service in ['api', 'web']:
            record = json.loads((ROOT / '.local' / (service + '.json')).read_text())
            expected = str(ROOT / 'apps' / service)
            assert record['cwd'] == expected
            queue = [(int(record['pid']), 0)]
            while queue:
                pid, depth = queue.pop(0)
                cwd = run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'])
                assert '\nn' + expected + '\n' in cwd, 'Process cwd mismatch'
                command = run(['ps','-p',str(pid),'-o','command='], private=True).strip()
                rows = dict(service=service,pid=pid,cwd=expected,commandSha256=hashlib.sha256(command.encode()).hexdigest(),
                            mediaOverrideMentioned='recording-root' in command or 'NORTHSTAR_RECORDING_ROOT' in command,
                            dbOverrideMentioned='DB_NAME' in command or 'spring.datasource' in command)
                processes.append(rows)
                children = run(['pgrep','-P',str(pid)], allowed=(0,1)).split()
                if depth < 3:
                    queue.extend((int(child), depth+1) for child in children if child.isdigit())
        write('processes.json', dict(processes=processes, environmentInspected=False,
            effectiveRecordingRoot='NOT VERIFIED', processToSchemaBinding='NOT VERIFIED'))
        # No filesystem media scan without effective runtime root verification.
        write('media-browser.json', dict(media='NOT VERIFIED: effective runtime root not proven',
            browserBuffers='NOT VERIFIED; do not navigate/sync/submit/discard user buffers',
            defaultCandidate=str(Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english')))
        write('result.json', dict(status='PARTIAL', identity='PASS', flywayHistory='PASS', grants='PASS',
              media='NOT VERIFIED', browserBuffers='NOT VERIFIED', capacity='NOT VERIFIED',
              sourceDataWrites=False, servicesStartedOrStopped=False, B01='BLOCKED', B03='BLOCKED'))
        return 0
    except Exception as error:
        write('result.json', dict(status='BLOCKED', reason=type(error).__name__ + ': ' + str(error), sourceDataWrites=False,
              servicesStartedOrStopped=False, B01='BLOCKED', B03='BLOCKED'))
        return 2
    finally:
        write('commands.json', RECORDS)


if __name__ == '__main__':
    raise SystemExit(main())
