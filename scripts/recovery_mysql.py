#!/usr/bin/env python3
"""Create/start/stop only the dedicated recovery instance. Never remove volumes or containers."""
import argparse
import json
import subprocess
import local

CONTAINER = 'northstar-english-phase09-recovery'
VOLUME = 'northstar_english_phase09_recovery_data'
ROLE = 'phase09-recovery'
CONFIG = local.LOCAL / 'phase09-recovery.json'


def port():
    value = json.loads(CONFIG.read_text())['mysqlPort']
    if not isinstance(value, int) or not 1024 <= value <= 65535:
        raise RuntimeError('Invalid recovery port')
    return value


def check_identity(item, expected_port):
    labels = item['Config'].get('Labels', {})
    if labels.get('local.northstar.project') != local.IDENTITY or labels.get('local.northstar.role') != ROLE:
        raise RuntimeError('Recovery container identity mismatch')
    if item['HostConfig']['PortBindings'].get('3306/tcp') != [{'HostIp': '127.0.0.1', 'HostPort': str(expected_port)}]:
        raise RuntimeError('Recovery port/binding mismatch')
    if not any(m.get('Name') == VOLUME and m.get('Destination') == '/var/lib/mysql' for m in item['Mounts']):
        raise RuntimeError('Recovery volume mismatch')


def verify(env):
    selected = port()
    if str(selected) in {env[k] for k in ('MYSQL_PORT', 'API_PORT', 'WEB_PORT')}:
        raise RuntimeError('Recovery port overlaps main services')
    item = json.loads(local.run(['docker', 'inspect', CONTAINER], env, capture_output=True, text=True).stdout)[0]
    check_identity(item, selected)
    return selected


def compose(env, *args):
    env = dict(env, RECOVERY_MYSQL_PORT=str(port()))
    return local.run(['docker', 'compose', '--env-file', str(local.ROOT / '.env'), '-f',
                      str(local.ROOT / 'infra/compose.recovery.yml'), *args], env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop'])
    args = parser.parse_args()
    env = local.environment()
    exists = subprocess.run(['docker', 'inspect', CONTAINER], env=env, capture_output=True).returncode == 0
    # Inspect first, never adopt a same-name container without our recorded identity.
    if exists:
        verify(env)
    elif args.action == 'stop':
        return
    elif not CONFIG.exists():
        selected = 3310
        while str(selected) in {env[k] for k in ('MYSQL_PORT', 'API_PORT', 'WEB_PORT')} or not local.available(selected):
            selected += 1
            if selected > 65535:
                raise RuntimeError('No recovery port available')
        local.LOCAL.mkdir(exist_ok=True)
        CONFIG.write_text(json.dumps({'mysqlPort': selected}))
    if args.action == 'stop':
        compose(env, 'stop', 'mysql')
        return
    volume = subprocess.run(['docker', 'volume', 'inspect', VOLUME], env=env, capture_output=True, text=True)
    if volume.returncode == 0:
        labels = json.loads(volume.stdout)[0].get('Labels', {})
        if labels.get('local.northstar.project') != local.IDENTITY or labels.get('local.northstar.role') != ROLE:
            raise RuntimeError('Existing recovery volume identity mismatch')
    if not exists and not local.available(port()):
        raise RuntimeError('Recovery port occupied; refusing to stop its owner')
    compose(env, *(['start', '--wait', 'mysql'] if exists else ['up', '-d', '--wait', '--no-recreate', 'mysql']))
    verify(env)
    print('Recovery MySQL ready on 127.0.0.1:' + str(port()))


if __name__ == '__main__':
    main()
