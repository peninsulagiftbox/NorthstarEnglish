#!/usr/bin/env python3
"""Run regression or browsers only on the owned, identity-checked Phase10B2 test target."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import phase10b2 as r
import phase10b2_isolated as isolated


def setup():
    c=isolated.campaign();d=c.verify('empty')
    c.call('start-owned-empty',[c.DOCKER,'start',d['containerId']])
    for _ in range(60):
        p=c.call('owned-readiness',[c.DOCKER,'exec',d['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'],expected=(0,1),private=True)
        if p.returncode==0 and p.stdout.decode().strip()==d['uuid']:break
        time.sleep(.5)
    else:raise RuntimeError('Owned test DB not ready')
    assert d['port'] not in [3308,3311,3312] and d['uuid']!=c.SOURCE_UUID
    cred=json.loads((c.PRIVATE/'empty/credentials.json').read_text())
    env=r.environment();env.update(MYSQL_PORT=str(d['port']),API_PORT='8131',WEB_PORT='3151',DB_NAME='northstar_phase01_test',MYSQL_ROOT_PASSWORD=cred['root'],DB_PASSWORD=cred['app'],DB_MIGRATION_PASSWORD=cred['migrator'],NORTHSTAR_DB_TEST='1',NORTHSTAR_EXPECTED_DB_UUID=d['uuid'],NORTHSTAR_CONTENT_ROOT=str(c.PRIVATE/'empty/content'),NORTHSTAR_RECORDING_ROOT=str(c.PRIVATE/'empty/recordings'),NORTHSTAR_TEST_AUDIO=str(r.STATE/'audio/original-test-tone.mp3'))
    return c,env


def main():
    action=sys.argv[1];c,env=setup()
    if action=='integration':
        try:
            r.record('java-real-db-legacy',['apps/api/mvnw','-f','apps/api/pom.xml','-Dtest=*,!MultiCourseIntegrationTest','verify'],env=env)
            r.record('java-real-db-multicourse',['apps/api/mvnw','-f','apps/api/pom.xml','-Dtest=MultiCourseIntegrationTest','verify'],env=env)
        finally:c.save(c.OUT/('regression-commands-'+str(time.time_ns())+'.json'),c.RECORDS,exclusive=False)
    elif action=='final-protection':
        original_sql=c.sql
        def test_sql(role,query,**kwargs):return original_sql(role,'USE northstar_phase01_test;'+query,**kwargs)
        c.sql=test_sql
        before=c.snapshot('empty','final-test-before-startup')
        media_module=isolated.load('media_inventory_final',isolated.BASE/'runtime_media_preflight.py')
        paths=[c.PRIVATE/'empty/content',c.PRIVATE/'empty/recordings/northstar_phase01_test']
        media_before=[media_module.inventory(path) for path in paths]
        for i in range(2):
            handle=isolated.start(c,'empty',schema='northstar_phase01_test')
            try:
                assert c.http('empty',handle,'/lessons/fixture-a')['versionId']=='fixture-a-v2'
                assert len(c.http('empty',handle,'/lessons/fixture-b?versionId=fixture-b-v1')['sentences'])==24
                for endpoint in ['/study/resume','/reports','/writing?lessonId=demo-01&versionId=demo-01-v2','/recordings?lessonId=demo-01&versionId=demo-01-v2&sentenceId=demo-01-v2-s10']:
                    c.http('empty',handle,endpoint)
            finally:c.end_api('empty',handle)
            c.compare(before,c.snapshot('empty','final-test-after-startup-'+str(i)))
            assert [media_module.inventory(path) for path in paths]==media_before
        c.sql=original_sql
        for role in ['upgrade','recovery']:
            d=c.verify(role);c.call(role+'-start-owned-final',[c.DOCKER,'start',d['containerId']])
            for _ in range(60):
                probe=c.call(role+'-ready-final',[c.DOCKER,'exec',d['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'],expected=(0,1),private=True)
                if probe.returncode==0 and probe.stdout.decode().strip()==d['uuid']:break
                time.sleep(.5)
            else:raise RuntimeError('Owned final DB readiness timeout')
            original=c.snapshot(role,'final-artifact-before')
            handle=isolated.start(c,role)
            try:assert c.http(role,handle,'/lessons/demo-01')['versionId']=='demo-01-v1'
            finally:c.end_api(role,handle)
            c.compare(original,c.snapshot(role,'final-artifact-after'));c.media_check(role);c.stop(role)
        c.stop('empty')
        c.save(r.OUT/'final-data-protection.json',dict(status='PASS',all38TablesExactAfterTwoRestarts=True,allTestMediaExact=True,multiCourseRead=True,finalArtifactJarSha256=c.digest(c.PATCHED_JAR),oldBackupUpgradeAndRecoveryFinalArtifactExact=True,personalDatabaseAddressed=False))
        c.save(c.OUT/('final-protection-commands-'+str(time.time_ns())+'.json'),c.RECORDS)
    elif action=='browser-start':
        (r.STATE/'STOP_BROWSER').unlink(missing_ok=True)
        handle=isolated.start(c,'empty',schema='northstar_phase01_test')
        webport=3151;assert c.available(webport)
        log=r.STATE/'browser-web.log';stream=log.open('ab')
        web=subprocess.Popen(['node',str(r.COPY/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(webport)],cwd=r.COPY/'apps/web',env=env,stdout=stream,stderr=subprocess.STDOUT)
        state=dict(apiPid=handle[0].pid,webPid=web.pid,apiPort=8131,webPort=3151,containerId=c.state('empty')['containerId'],uuid=c.state('empty')['uuid'],cwd=str(r.COPY),jarSha256=c.digest(c.PATCHED_JAR))
        (r.STATE/'browser-services.json').write_text(json.dumps(state,indent=2)+'\n')
        (r.OUT/'browser-services.json').write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps(state),flush=True)
        # Keep ownership and handles until a stop request file appears; no orphaned personal services.
        try:
            while not (r.STATE/'STOP_BROWSER').exists():
                if web.poll() is not None:raise RuntimeError('Isolated Web exited')
                time.sleep(.5)
        finally:
            if web.poll() is None:web.terminate();web.wait(timeout=20)
            stream.close();c.end_api('empty',handle);c.stop('empty')
            c.save(c.OUT/('browser-lifecycle-'+str(time.time_ns())+'.json'),c.RECORDS,exclusive=False)
    else:raise SystemExit('integration | browser-start')

if __name__=='__main__':main()
