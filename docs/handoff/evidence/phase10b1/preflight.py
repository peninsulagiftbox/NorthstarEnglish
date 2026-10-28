#!/usr/bin/env python3
"""Read-only identity gate. Never connect to SQL, start/stop services or migrate."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def save(name, value):
    path = OUT / name
    with path.open('x') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    os.chdir(ROOT)
    records = []

    def run(name, argv):
        start = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=15)
            rc, stdout, stderr = p.returncode, p.stdout, p.stderr
        except FileNotFoundError:
            rc, stdout, stderr = 127, '', 'Executable not found'
        except subprocess.TimeoutExpired as error:
            rc, stdout, stderr = None, '', 'Timed out; no process exit code obtained'
        record = dict(name=name, argv=argv, cwd=str(ROOT), started=start,
                      returncode=rc, stdout=stdout, stderr=stderr)
        records.append(record)
        save('probe-' + name + '.json', record)
        print(name, 'exit=', rc, flush=True)
        return record

    head = run('head', ['git', 'rev-parse', 'HEAD'])
    status = run('status', ['git', 'status', '--short', '--untracked-files=all'])
    tracked = run('tracked-files', ['git', 'ls-files', '-z', 'apps', 'scripts', 'infra', 'content', 'package.json', 'package-lock.json'])
    hashes = []
    for rel in tracked['stdout'].split('\0'):
        if not rel:
            continue
        path = ROOT / rel
        if path.is_file() and not path.is_symlink():
            hashes.append(dict(path=rel, bytes=path.stat().st_size,
                               sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    migrations = []
    for path in sorted((ROOT / 'apps/api/src/main/resources/db/migration').glob('*.sql')):
        rel = str(path.relative_to(ROOT))
        old = subprocess.run(['git', 'show', 'HEAD:' + rel], capture_output=True)
        migrations.append(dict(path=rel, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               matchesHead=old.returncode == 0 and old.stdout == path.read_bytes(),
                               gitShowReturncode=old.returncode))
    config = {}
    env_file = ROOT / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key in {'MYSQL_PORT', 'API_PORT', 'WEB_PORT'}:
                config[key] = value
    state = {}
    for name in ['api', 'web', 'phase09-recovery']:
        path = ROOT / '.local' / (name + '.json')
        if path.exists():
            data = json.loads(path.read_text())
            state[name] = {k: data[k] for k in ['pid', 'cwd', 'mysqlPort'] if k in data}
    jar = ROOT / 'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    libraries = []
    if jar.is_file():
        import zipfile
        with zipfile.ZipFile(jar) as z:
            libraries = [n for n in z.namelist() if n.startswith('BOOT-INF/lib/flyway')]
    save('baseline.json', dict(at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
         head=head['stdout'].strip(), status=status['stdout'], trackedSourceHashes=hashes,
         migrations=migrations, configurationOnly=config, recordedServiceClaimsUnverified=state,
         expectedSource=dict(container='northstar-english-mysql-01', schema='northstar_english',
             project='northstar-english-local-v1', appAccount='northstar_app', migrationAccount='northstar_migrator'),
         jarFlywayLibraries=libraries, jarSha256=hashlib.sha256(jar.read_bytes()).hexdigest() if jar.is_file() else None,
         jarMatchesHead='NOT VERIFIED', diskFreeBytes=shutil.disk_usage(ROOT).free,
         databaseConnected=False, sourcePrivileges='NOT VERIFIED', mediaRoot='NOT VERIFIED'))
    # A denial here is a hard stop: no alternate host, schema or API is attempted.
    docker = run('docker-identity', ['docker', 'inspect', '--format',
        '{{json .Name}} {{json .Config.Labels}} {{json .HostConfig.PortBindings}} {{json .Mounts}} {{json .State.Status}}',
        'northstar-english-mysql-01'])
    save('commands.json', records)
    if docker['returncode'] != 0:
        save('gate.json', dict(status='BLOCKED', reason='Source container identity could not be verified',
             evidence='probe-docker-identity.json', databaseConnected=False, sourceWritesByThisRun=False,
             servicesStartedOrStopped=False, backupCreated=False, migrationApplied=False))
        return 2
    save('gate.json', dict(status='BLOCKED', reason='Container inspection alone is insufficient; database identity, grants, process ownership and isolated targets still unverified',
         databaseConnected=False, sourceWritesByThisRun=False, servicesStartedOrStopped=False,
         backupCreated=False, migrationApplied=False))
    return 2


if __name__ == '__main__':
    sys.exit(main())
