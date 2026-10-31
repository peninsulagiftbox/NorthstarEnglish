#!/usr/bin/env python3
"""Own only isolated API/Web children; pinned Playwright session, no personal origin."""
import json,sys,time,subprocess,urllib.request,re
from pathlib import Path
import phase10c1_isolated as iso
r=iso.r
c=iso.campaign();role=(r.STATE/'ACTIVE_TEST_ROLE').read_text().strip() if (r.STATE/'ACTIVE_TEST_ROLE').exists() else 'empty';e=iso.env(c,role,'northstar_phase01_test');api=int(e['API_PORT']);web=int(e['WEB_PORT']);assert api==8155 and web==3175 and c.available(api) and c.available(web)
cli=None
for p in sorted((Path.home()/'.npm/_npx').glob('*/node_modules/@playwright/cli/package.json')):
 if json.loads(p.read_text()).get('version')=='0.1.22':cli=p.parent/'playwright-cli.js';break
assert cli,'Pinned CLI required';command=['node',str(cli),'--session=northstar-phase10c1']
script=sys.argv[1];assert script in ['phase10c1-browser-smoke.js','full-learning-loop.js','player-timeline-browser-smoke.js','phase10c1-capture-probe.js','phase10c1-navigation-smoke.js']
processes=[];streams=[]
try:
 argv=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+str(api),'--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']]
 for name,args,cwd in [('api',argv,r.COPY/'apps/api'),('web',['node',str(r.ROOT/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(web)],r.COPY/'apps/web')]:
  stream=(r.STATE/(name+'-browser-'+str(time.time_ns())+'.log')).open('xb');streams.append(stream);processes.append(subprocess.Popen(args,cwd=cwd,env=e,stdout=stream,stderr=subprocess.STDOUT))
 for _ in range(120):
  assert all(p.poll() is None for p in processes),'Isolated child exited'
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{web}/api/v1/health',timeout=2) as response:assert response.headers['X-Northstar-Test-Database']=='true';assert json.load(response)['migrationVersion']=='010.06'
   break
  except OSError:time.sleep(.25)
 else:raise RuntimeError('Isolated browser readiness timeout')
 (r.ROOT/'output/playwright/phase10c1').mkdir(parents=True,exist_ok=True);(r.ROOT/'output/playwright/phase10c1-demo').mkdir(parents=True,exist_ok=True)
 r.record('browser-open',command+['open',f'http://127.0.0.1:{web}']+(['--headed'] if script=='phase10c1-browser-smoke.js' else []),env=e,cwd=r.ROOT)
 r.record('browser-snapshot',command+['snapshot'],env=e,cwd=r.ROOT)
 code=(r.ROOT/'scripts'/script).read_text().replace('output/playwright/phase10b2-demo/','output/playwright/phase10c1-demo/')
 p=r.record('browser-'+script,command+['run-code',code],env=e,cwd=r.ROOT,timeout=300)
 output=p.stdout.decode()
 result=json.loads(output.split('### Result\n',1)[1].split('\n###',1)[0]) if '### Result\n' in output else {}
 if script=='phase10c1-capture-probe.js':
  import base64
  result=json.loads(output.split('### Result\n',1)[1].split('\n###',1)[0]);probe=result['probe'];encoded=probe.pop('base64',None)
  if encoded:(r.OUT/'output-capture-probe.webm').write_bytes(base64.b64decode(encoded))
  (r.OUT/'output-capture-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (r.OUT/(script+'.result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 assert re.search(r'"passed"\s*:\s*true',output) and '### Error' not in output,'Browser assertions failed; raw log retained'
finally:
 try:r.record('browser-close',command+['close'],env=e,cwd=r.ROOT,expected=(0,1))
 finally:
  for p in processes:
   if p.poll() is None:p.terminate()
  for p in processes:
   try:p.wait(timeout=20)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
  for stream in streams:stream.close()
