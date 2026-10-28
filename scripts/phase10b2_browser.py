#!/usr/bin/env python3
"""Playwright CLI acceptance against the running owned test origin only."""
import json
from pathlib import Path
import re
import sys
import urllib.request
import phase10b2 as r

base='http://127.0.0.1:3151'
state=json.loads((r.STATE/'browser-services.json').read_text())
assert state['webPort']==3151 and state['apiPort']==8131 and state['uuid']!='104d5d9d-cd3f-11f1-8da4-920f115cf5cb'
with urllib.request.urlopen(base+'/api/v1/health',timeout=8) as response:
    assert response.headers['X-Northstar-Test-Database']=='true'
    assert json.load(response)['migrationVersion']=='009.05'
cli=None
for path in sorted((Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json')):
    if json.loads(path.read_text()).get('version')=='0.1.22':cli=path.parent/'playwright-cli.js';break
assert cli,'Pinned existing Playwright CLI missing'
env=r.environment()
command=['node',str(cli),'--session=northstar-phase10b2']
(r.ROOT/'output/playwright').mkdir(parents=True,exist_ok=True)
(r.ROOT/'output/playwright/phase10b2-demo').mkdir(parents=True,exist_ok=True)
script=sys.argv[1]
assert script in ['phase10b2-browser-smoke.js','full-learning-loop.js']
try:
    r.record('browser-open',command+['open',base],env=env,cwd=r.ROOT)
    r.record('browser-snapshot',command+['snapshot'],env=env,cwd=r.ROOT)
    result=r.record('browser-'+script,command+['run-code',(r.ROOT/'scripts'/script).read_text()],env=env,cwd=r.ROOT,timeout=300)
    text=result.stdout.decode()
    assert re.search(r'"passed"\s*:\s*true',text) and '### Error' not in text,'Browser assertions failed; retain CLI output'
finally:r.record('browser-close',command+['close'],env=env,cwd=r.ROOT,expected=(0,1))
