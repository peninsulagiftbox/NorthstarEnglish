#!/usr/bin/env python3
"""Run the unchanged frozen API beside the fixed main-tree Web build for retest."""
import subprocess, time
import run as q

api=q.start_api(); web=None
try:
    with __import__('socket').socket() as listener:
        listener.bind(('127.0.0.1', q.WEB_PORT))
    q.run('fix-web-build',[q.NODE+'/npm','run','build'],env=q.env(),cwd=q.ROOT/'apps/web')
    log=(q.PRIVATE/'fix-web.log').open('wb')
    web=subprocess.Popen([q.NODE+'/node',str(q.ROOT/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(q.WEB_PORT)],cwd=q.ROOT/'apps/web',env=q.env(),stdout=log,stderr=subprocess.STDOUT)
    for _ in range(100):
        assert web.poll() is None,'fixed Web exited'
        try:
            with __import__('urllib.request',fromlist=['urlopen']).urlopen(q.WEB+'/review',timeout=2) as response:
                if response.status==200:break
        except OSError:pass
        time.sleep(.3)
    else:raise RuntimeError('fixed Web readiness timeout')
    q.save('fix-runtime.json',dict(apiPid=api.pid,webPid=web.pid,api=q.API,web=q.WEB,jarSha256=q.JAR_SHA,buildId=(q.ROOT/'apps/web/.next/BUILD_ID').read_text().strip(),database=q.identity(),source='main working tree'))
    print('FIX_STACK_READY',flush=True)
    for _ in range(1800):
        if (q.PRIVATE/'stop-fix-browser').exists():break
        assert api.poll() is None and web.poll() is None
        time.sleep(1)
finally:
    if web:q.stop(web)
    q.stop(api)
    print('OWNED_CHILDREN_STOPPED',flush=True)
