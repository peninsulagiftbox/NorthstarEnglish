#!/usr/bin/env python3
"""Read-only Docker diagnostics. Does not inspect container environment or start services."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from urllib.parse import urlsplit, urlunsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New evidence directory; refuses overwrite')
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    records = []

    def run(argv):
        started = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            item = dict(argv=argv, started=started, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
        except FileNotFoundError:
            item = dict(argv=argv, started=started, returncode=127, stdout='', stderr='Executable not found')
        except subprocess.TimeoutExpired:
            item = dict(argv=argv, started=started, returncode=None, stdout='', stderr='TIMEOUT; exit code unavailable')
        records.append(item)
        print(json.dumps(dict(argv=argv, returncode=item['returncode'])), flush=True)
        return item

    docker = shutil.which('docker')
    host = os.environ.get('DOCKER_HOST')
    if host:
        parsed = urlsplit(host)
        host = urlunsplit((parsed.scheme, parsed.netloc.rsplit('@', 1)[-1], parsed.path, '', ''))
    environment = dict(uid=os.getuid(), euid=os.geteuid(), gid=os.getgid(), groups=os.getgroups(),
        dockerExecutable=docker, dockerExecutableResolved=str(Path(docker).resolve()) if docker else None,
        DOCKER_HOST=host, DOCKER_CONTEXT=os.environ.get('DOCKER_CONTEXT'),
        CODEX_SANDBOX=os.environ.get('CODEX_SANDBOX'),
        CODEX_SANDBOX_NETWORK_DISABLED=os.environ.get('CODEX_SANDBOX_NETWORK_DISABLED'),
        cwd=str(Path.cwd()))
    run(['id'])
    run(['pgrep', '-x', 'Docker'])
    run(['pgrep', '-x', 'com.docker.backend'])
    contexts = []
    if docker:
        run([docker, '--version'])
        current = run([docker, 'context', 'show'])
        if current['returncode'] == 0:
            result = run([docker, 'context', 'inspect', current['stdout'].strip(), '--format', '{{json .Endpoints.docker.Host}}'])
            if result['returncode'] == 0:
                contexts.append(json.loads(result['stdout']))
    paths = {Path.home() / '.docker/run/docker.sock', Path('/var/run/docker.sock')}
    for endpoint in [host, *contexts]:
        if endpoint and endpoint.startswith('unix://'):
            paths.add(Path(endpoint[7:]))
    sockets = []
    for path in sorted(paths):
        item = dict(path=str(path), resolved=str(path.resolve()))
        try:
            meta = path.stat()
            item.update(uid=meta.st_uid, gid=meta.st_gid, mode=oct(stat.S_IMODE(meta.st_mode)),
                        isSocket=stat.S_ISSOCK(meta.st_mode), readAccess=os.access(path, os.R_OK),
                        writeAccess=os.access(path, os.W_OK), isSymlink=path.is_symlink())
        except OSError as error:
            item.update(errorType=type(error).__name__, errno=error.errno, error=str(error))
        sockets.append(item)
    if docker:
        run([docker, 'info', '--format', '{{json .ServerVersion}} {{json .OperatingSystem}} {{json .ID}}'])
        run([docker, 'inspect', '--format',
             '{{json .Id}} {{json .Name}} {{json .Config.Labels}} {{json .HostConfig.PortBindings}} {{json .Mounts}} {{json .State.Status}}',
             'northstar-english-mysql-01'])
    result = dict(environment=environment, contexts=contexts, sockets=sockets, commands=records,
                  readOnly=True, sourceDatabaseConnected=False,
                  scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    path = args.output / 'diagnostic.json'
    with path.open('x') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    path.chmod(0o600)
    return 0 if docker and all(item['returncode'] == 0 for item in records if item['argv'][0] == docker) else 2


if __name__ == '__main__':
    raise SystemExit(main())
