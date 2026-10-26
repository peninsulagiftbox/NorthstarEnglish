#!/usr/bin/env python3
"""Phase09 isolated runtime; preserves the main site, schemas and media."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import time
import local


def stop(name):
    path = local.LOCAL / (name + '.json')
    if not path.exists():
        return
    record = json.loads(path.read_text())
    if local.owns_process(record):
        os.kill(record['pid'], signal.SIGTERM)
        for _ in range(80):
            if not local.owns_process(record):
                break
            time.sleep(.25)
        else:
            raise RuntimeError('停止超时，保留身份记录')
    elif subprocess.run(['ps', '-p', str(record['pid'])], stdout=subprocess.DEVNULL).returncode == 0:
        raise RuntimeError('进程身份不符，拒绝停止')
    path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'start', 'stop', 'restart-api'])
    parser.add_argument('--api-port', type=int, default=8086)
    parser.add_argument('--web-port', type=int, default=3101)
    target = parser.add_mutually_exclusive_group()
    target.add_argument('--restore-db', help='northstar_restore_YYYYMMDDhhmmss on dedicated recovery MySQL')
    target.add_argument('--fresh-recovery', action='store_true', help='separate recovery MySQL initialized application schema; never clears data')
    args = parser.parse_args()
    env = local.environment()
    if not all(1024 <= p <= 65535 for p in (args.api_port, args.web_port)) or args.api_port == args.web_port:
        raise RuntimeError('测试端口必须不同且为 1024–65535')
    if {str(args.api_port), str(args.web_port)} & {env[k] for k in ('API_PORT', 'WEB_PORT', 'MYSQL_PORT')}:
        raise RuntimeError('隔离端口不得使用主站端口')
    env.update(DB_NAME='northstar_phase01_test', API_PORT=str(args.api_port), WEB_PORT=str(args.web_port))
    prefix = 'phase09'
    if args.restore_db or args.fresh_recovery:
        if args.restore_db and not re.fullmatch(r'northstar_restore_[0-9]{14}', args.restore_db):
            raise RuntimeError('Only timestamped isolated restore schemas are allowed')
        import recovery_mysql
        env.update(DB_NAME=args.restore_db or 'northstar_english', NORTHSTAR_ALLOW_RESTORE_DB='true', MYSQL_PORT=str(recovery_mysql.verify(env)))
        prefix = 'phase09-restore' if args.restore_db else 'phase09-fresh'
    build = local.LOCAL / (prefix + '-web')
    jar = local.ROOT / 'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    cli = local.ROOT / 'node_modules/next/dist/bin/next'
    if args.action == 'stop':
        stop(prefix + '-web')
        stop(prefix + '-api')
        return
    if not (args.restore_db or args.fresh_recovery):
        local.verify_container(env)
    if args.action == 'build':
        for name in (prefix + '-web', prefix + '-api'):
            path = local.LOCAL / (name + '.json')
            if path.exists() and local.owns_process(json.loads(path.read_text())):
                raise RuntimeError('先停止隔离服务再构建')
        build.mkdir(exist_ok=True)
        for source in (local.ROOT / 'apps/web').iterdir():
            if source.name in ('.next', 'node_modules', 'tsconfig.tsbuildinfo'):
                continue
            target = build / source.name
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)
        subprocess.run(['npm', 'run', 'build'], cwd=build, env=env, check=True)
        return
    if args.action == 'restart-api':
        stop(prefix + '-api')
    for name, port in [(prefix + '-api', args.api_port), (prefix + '-web', args.web_port)]:
        path = local.LOCAL / (name + '.json')
        if not local.available(port) and not (path.exists() and local.owns_process(json.loads(path.read_text()))):
            raise RuntimeError(f'端口 {port} 被其他进程占用；不终止占用进程')
    local.start_process(prefix + '-api', [shutil.which('java', path=env['PATH']), '-jar', str(jar),
                        '--northstar.content-root=' + str(local.ROOT / 'content'),
                        '--northstar.recording-root=' + str(local.LOCAL / 'phase09-media')],
                        local.ROOT / 'apps/api', env, str(jar))
    local.wait_health(f'http://127.0.0.1:{args.api_port}/api/v1/health')
    local.start_process(prefix + '-web', [shutil.which('node', path=env['PATH']), str(cli), 'start',
                        '--hostname', '127.0.0.1', '--port', str(args.web_port)], build, env, str(cli))
    local.wait_health(f'http://127.0.0.1:{args.web_port}/api/v1/health')
    print(f'Isolated regression: http://127.0.0.1:{args.web_port}')


if __name__ == '__main__':
    main()
