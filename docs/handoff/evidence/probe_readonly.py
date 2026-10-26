#!/usr/bin/env python3
"""GET only, never export personal history or start/migrate an application."""
import datetime
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import local
config = local.read_env(ROOT / '.env') if (ROOT / '.env').exists() else {}
records = []
for name, port in [('api', config.get('API_PORT', '8085')), ('web', config.get('WEB_PORT', '3100')), ('isolated-api', '8086'), ('isolated-web', '3101')]:
    url = f'http://127.0.0.1:{port}/api/v1/health'
    item = dict(service=name, url=url, method='GET')
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.load(response)
            item.update(httpStatus=response.status, projectMatches=payload.get('project') == local.IDENTITY,
                status=payload.get('status'), migrationVersion=payload.get('migrationVersion'),
                isolated=response.headers.get('X-Northstar-Test-Database'), cacheControl=response.headers.get('Cache-Control'))
            if item['projectMatches'] and payload.get('status') == 'UP':
                for endpoint in ['books', 'lessons', 'capabilities']:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/{endpoint}', timeout=5) as r:
                        data = json.load(r)
                        if endpoint == 'capabilities':
                            item[endpoint] = {k: data.get(k) for k in ['phase','aiEnabled','asrEnabled','pronunciationScoringEnabled']}
                        else:
                            item[endpoint] = dict(count=len(data), availability=sorted(set(row.get('availability','') for row in data)))
                for version in ['demo-01-v1', 'demo-01-v2']:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/lessons/demo-01?versionId={version}', timeout=5) as r:
                        data = json.load(r)
                        item[version] = dict(versionMatches=data.get('versionId') == version, sentences=len(data.get('sentences', [])))
    except Exception as exc:
        item.update(result='NOT VERIFIED', errorType=type(exc).__name__, error=str(exc))
    records.append(item)
    print(name, item.get('httpStatus', item.get('errorType')), flush=True)
result = dict(at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    command='python3 docs/handoff/evidence/probe_readonly.py', records=records)
Path(__file__).with_name('runtime-probes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
sys.exit(0 if all(r.get('httpStatus') == 200 for r in records) else 1)
