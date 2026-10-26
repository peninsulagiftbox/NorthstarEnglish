#!/usr/bin/env python3
"""Read-only loopback HTTP, binding, static secret and application-log checks."""
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.request
import local


def main():
    env = local.environment()
    acceptance = os.getenv('NORTHSTAR_PHASE09R') == '1'
    if acceptance:
        import phase09r
        kind = os.environ['NORTHSTAR_PHASE09R_KIND']
        env = phase09r.verify(kind)
    else:
        local.verify_container(env)
    base = 'http://127.0.0.1:' + env['API_PORT'] + '/api/v1'
    def check(path, status=200, method='GET', headers=None, data=None):
        request = urllib.request.Request(base + path, method=method, headers=headers or {}, data=data)
        try:
            result = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            result = error
        assert result.status == status, (path, result.status, status)
        assert result.headers.get('Access-Control-Allow-Origin') is None
        if status == 200:
            assert 'no-store' in result.headers.get('Cache-Control', '')
            assert result.headers.get('X-Content-Type-Options') == 'nosniff'
        body = result.read()
        assert b'java.lang.' not in body and b'stackTrace' not in body
        return body
    check('/health')
    check('/health', 403, headers={'Origin': 'https://untrusted.example'})
    check('/health', 403, headers={'Host': 'untrusted.example'})
    check('/settings', 403, method='POST', data=b'{}')
    check('/settings', 403, method='POST', headers={'Origin': 'https://untrusted.example', 'X-Northstar-Request': 'local-workspace', 'Content-Type': 'application/json'}, data=b'{}')
    check('/settings', 403, method='POST', headers={'Origin': 'http://127.0.0.1:' + env['WEB_PORT'], 'X-Northstar-Request': 'local-workspace', 'Content-Type': 'text/plain'}, data=b'{}')
    check('/health', 403, method='OPTIONS', headers={'Origin': 'https://untrusted.example'})
    check('/missing', 404)
    for key in ('WEB_PORT', 'API_PORT'):
        result = subprocess.run(['lsof', '-nP', '-iTCP:' + env[key], '-sTCP:LISTEN', '-Fn'], capture_output=True, text=True, check=True)
        addresses = [line[1:] for line in result.stdout.splitlines() if line.startswith('n')]
        assert addresses and all(a == '127.0.0.1:' + env[key] for a in addresses), 'Unexpected network binding'
    secrets = [env[k].encode() for k in ('DB_PASSWORD', 'DB_MIGRATION_PASSWORD', 'MYSQL_ROOT_PASSWORD')]
    asset_root = phase09r.STATE / kind / 'workspace/apps/web/.next/static' if acceptance else local.ROOT / 'apps/web/.next/static'
    assets = list(asset_root.rglob('*.js'))
    assert assets, 'Build assets missing'
    for file in assets:
        content = file.read_bytes()
        assert not any(secret in content for secret in secrets), 'Credential found in browser JS'
    with urllib.request.urlopen('http://127.0.0.1:' + env['WEB_PORT'] + '/settings', timeout=10) as response:
        html = response.read()
    assert not any(secret in html for secret in secrets), 'Credential found in HTML'
    log_root = phase09r.STATE / kind if acceptance else local.LOCAL
    names = ('phase09r-api.log','phase09r-web.log') if acceptance else ('api.log', 'web.log', 'phase09-api.log', 'phase09-web.log', 'phase09-restore-api.log', 'phase09-restore-web.log')
    for name in names:
        file = log_root / name
        if file.exists():
            content = file.read_bytes()
            assert not any(secret in content for secret in secrets), 'Credential found in runtime log'
            assert b'phase09-' not in content and b'window.__xss' not in content, 'Synthetic private input found in runtime log'
    print(json.dumps({'passed': True, 'checks': ['Host/Origin/write-header/content-type/CORS rejection', 'no-store/nosniff and redacted errors', 'API/Web bind only to 127.0.0.1', 'browser JS/HTML contain no configured DB secrets', 'application logs contain no DB secrets or synthetic private input'], 'javascriptAssetsChecked': len(assets)}))


if __name__ == '__main__':
    main()
