#!/usr/bin/env python3
"""Pinned Playwright CLI on the verified Phase10B3 test origin only."""
import json,re,sys,urllib.request
from pathlib import Path
import phase10b3
r=phase10b3.runner
state=json.loads((r.STATE/'browser-services.json').read_text());assert state['webPort']==3169 and state['apiPort']==8149 and state['uuid']!='104d5d9d-cd3f-11f1-8da4-920f115cf5cb'
base='http://127.0.0.1:'+str(state['webPort'])
with urllib.request.urlopen(base+'/api/v1/health',timeout=8) as response:
    assert response.headers['X-Northstar-Test-Database']=='true';assert json.load(response)['migrationVersion']=='009.15'
cli=None
for path in sorted((Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json')):
    if json.loads(path.read_text()).get('version')=='0.1.22':cli=path.parent/'playwright-cli.js';break
assert cli,'Pinned existing CLI required; no global installation'
command=['node',str(cli),'--session=northstar-phase10b3'];e=r.environment()
(ROOT:=r.ROOT/'output/playwright/phase10b3-demo').mkdir(parents=True,exist_ok=True)
script=sys.argv[1];assert script in ['full-learning-loop.js','phase10b2-browser-smoke.js','phase10b3-browser-smoke.js']
code=(r.ROOT/'scripts'/script).read_text().replace('output/playwright/phase10b2-demo/','output/playwright/phase10b3-demo/').replace('output/playwright/phase10b2-','output/playwright/phase10b3-')
if script=='phase10b2-browser-smoke.js':
    # Same scenarios, explicitly updated for the new schema and reviewed-mapping fallback label.
    code=code.replace("migrationVersion==='009.05'","migrationVersion==='009.15'").replace("name:'版本 1 · 历史',exact:true","name:'版本 1 · 历史 · 无确定映射',exact:true")
try:
    r.record('browser-open',command+['open',base],env=e,cwd=r.ROOT)
    r.record('browser-snapshot',command+['snapshot'],env=e,cwd=r.ROOT)
    result=r.record('browser-'+script,command+['run-code',code],env=e,cwd=r.ROOT,timeout=300)
    output=result.stdout.decode();assert re.search(r'"passed"\s*:\s*true',output) and '### Error' not in output,'Browser assertions failed; original log retained'
finally:r.record('browser-close',command+['close'],env=e,cwd=r.ROOT,expected=(0,1))
