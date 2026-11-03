#!/usr/bin/env python3
"""Foreground supervisor: build correct proxy then own/stop API and web child PIDs."""
import os,subprocess,time,json
import qa_runtime as q
p=q.start_api();web=None
try:
    env=dict(os.environ,API_PORT='8186',PATH='/opt/homebrew/opt/node@22/bin:'+os.environ['PATH'])
    with (q.OUT/'logs/browser-build.log').open('w') as f:r=subprocess.run(['npm','run','build'],cwd=q.QA,env=env,stdout=f,stderr=subprocess.STDOUT)
    assert r.returncode==0,'build failed'
    bid=(q.QA/'apps/web/.next/BUILD_ID').read_text().strip()
    config=json.loads((q.QA/'apps/web/.next/required-server-files.json').read_text())
    assert '127.0.0.1:8186' in json.dumps(config)
    log=(q.PRIVATE/'runtime-web.log').open('ab')
    web=subprocess.Popen(['node',str(q.QA/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3197'],cwd=q.QA/'apps/web',env=env,stdout=log,stderr=subprocess.STDOUT)
    (q.OUT/'logs/browser-identity.json').write_text(json.dumps({'buildId':bid,'api':q.API,'web':q.WEB,'database':q.state(),'owner':'local','proxy':8186,'build_exit_code':r.returncode},indent=2))
    print('BROWSER_READY build='+bid,flush=True)
    stop=q.PRIVATE/'stop-browser'
    for _ in range(1200):
        if stop.exists():stop.unlink();break
        assert web.poll() is None and p.poll() is None
        time.sleep(1)
finally:
    if web:q.stop(web)
    q.stop(p)
    print('OWNED_CHILDREN_STOPPED',flush=True)
