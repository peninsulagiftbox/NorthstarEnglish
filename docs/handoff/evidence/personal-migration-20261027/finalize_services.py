#!/usr/bin/env python3
"""Start only verified Northstar services after migration; no synthetic learning submissions."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare import load,ROOT,HERE,OLD

def main():
    assert len(sys.argv)==2 and sys.argv[1].isalnum()
    run=sys.argv[1];os.umask(0o077)
    private=ROOT/'.local/personal-migration'/run
    out=HERE/run/'service-verification';out.mkdir()
    migration=json.loads((HERE/run/'personal-execution/result.json').read_text())
    assert migration['status']=='PERSONAL_MIGRATION_PASS_SERVICES_STILL_STOPPED'
    c=load('campaign',OLD/'isolated_rehearsal.py');m=load('backup',OLD/'maintenance_backup.py');local=load('local',ROOT/'scripts/local.py');runtime=load('runtime',OLD/'runtime_media_preflight.py')
    expected=json.loads((private/'source-after-009.04.json').read_text())
    media=json.loads((private/'backup/media-manifest.json').read_text())
    paths={'recordings':Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english','content':ROOT/'content'}
    compatibility=json.loads((HERE/run/'application-compatibility/result.json').read_text())
    assert c.digest(c.OLD_JAR)==compatibility['applicationJarSha256']
    result={'status':'BLOCKED','sourceSyntheticLearningWrites':False};events=[];owned=[]
    def save(path,value):
        with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    def get(path,port=8085):
        with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=15) as response:
            body=response.read();safe_path=re.sub(r'(/recordings/)[^/]+(/audio)',r'\1[private-id]\2',path);events.append({'method':'GET','path':safe_path,'port':port,'status':response.status,'bodySha256':hashlib.sha256(body).hexdigest()})
            return body
    def stop_owned(record):
        assert local.owns_process(record),'Will not signal a mismatched process'
        os.kill(record['pid'],signal.SIGTERM)
        for _ in range(100):
            if not local.owns_process(record):return
            time.sleep(.2)
        raise RuntimeError('Owned project service did not stop')
    try:
        env=local.environment();item=local.verify_container(env);assert item['Id']==m.CONTAINER
        assert m.sql('SELECT @@server_uuid').strip()==c.SOURCE_UUID
        c.compare(expected,m.snapshot())
        env={k:v for k,v in env.items() if not k.startswith(('SPRING_','NORTHSTAR_')) and k not in ['JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','DB_NAME']}
        env.update(DB_NAME='northstar_english')
        for port in [8085,3100]:assert local.available(port),'Service port unexpectedly occupied'
        save(private/'previous-service-records.json',{name:json.loads((ROOT/'.local'/f'{name}.json').read_text()) for name in ['api','web']})
        argv=[str(c.JAVA),'-jar',str(c.OLD_JAR),'--northstar.recording-root='+str(paths['recordings'].parent),'--northstar.content-root='+str(paths['content'])]
        for attempt in range(2):
            local.start_process('api',argv,ROOT/'apps/api',env,str(c.OLD_JAR))
            record=json.loads((ROOT/'.local/api.json').read_text());owned.append(record)
            events.append({'action':'start-api','supervisorPid':record['pid'],'jarSha256':c.digest(c.OLD_JAR)})
            local.wait_health('http://127.0.0.1:8085/api/v1/health')
            health=json.loads(get('/api/v1/health'));assert health['migrationVersion']=='009.04'
            for path in ['/books','/lessons','/study/resume','/reviews/due','/writing?lessonId=demo-01&versionId=demo-01-v2','/lessons/demo-01?versionId=demo-01-v1','/lessons/demo-01?versionId=demo-01-v2']:
                get('/api/v1'+path)
            for row in expected['personal_recording']['rows']:
                data={k:None if v is None else bytes.fromhex(v).decode() for k,v in zip(expected['personal_recording']['columns'],row)}
                if data['status']=='ready':
                    content=get('/api/v1/recordings/'+data['id']+'/audio')
                    assert len(content)==int(data['byte_size']) and hashlib.sha256(content).hexdigest()==data['sha256']
            c.compare(expected,m.snapshot())
            assert all(runtime.inventory(path)==media[name] for name,path in paths.items())
            if attempt==0:
                stop_owned(record);owned.remove(record);events.append({'action':'stop-only-new-api','supervisorPid':record['pid']})
        # Source export is a read-only endpoint. Save all private rows only under .local.
        export=get('/api/v1/data/export');save(private/'source-v009-export.json',json.loads(export))
        envelope=json.loads(export);payload=json.loads(envelope['payloadJson'])
        assert payload['schemaVersion']=='009.04' and hashlib.sha256(envelope['payloadJson'].encode()).hexdigest()==envelope['sha256']
        node=Path('/opt/homebrew/opt/node@22/bin/node');assert node.is_file()
        cli=ROOT/'node_modules/next/dist/bin/next'
        routes=json.loads((ROOT/'apps/web/.next/routes-manifest.json').read_text())['rewrites']
        routes=routes if isinstance(routes,list) else sum(routes.values(),[])
        assert any(route.get('destination')=='http://127.0.0.1:8085/api/v1/:path*' for route in routes),'Web build routes to an unexpected API'
        local.start_process('web',[str(node),str(cli),'start','--hostname','127.0.0.1','--port','3100'],ROOT/'apps/web',env,str(cli))
        record=json.loads((ROOT/'.local/web.json').read_text());owned.append(record)
        local.wait_health('http://127.0.0.1:3100/api/v1/health')
        assert json.loads(get('/api/v1/health',3100))['migrationVersion']=='009.04'
        get('/',3100);get('/dashboard',3100)
        c.compare(expected,m.snapshot())
        assert all(runtime.inventory(path)==media[name] for name,path in paths.items())
        result.update(status='PASS',sourceVersion='009.04',oldAndNewRowsExactAcrossTwoSourceStarts=True,mediaHashesUnchanged=True,sourceExportVersion='009.04',web='http://127.0.0.1:3100',services=[{'supervisorPid':r['pid'],'cwd':r['cwd']} for r in owned],jarSha256=c.digest(c.OLD_JAR),sourceWriteScope='Approved frozen migration/history only; startup/read checks changed no rows')
    except Exception as error:
        result['reason']=type(error).__name__+': '+str(error)
        # Keep write services stopped on any unexplained difference; never stop MySQL.
        for record in reversed(owned):
            try:stop_owned(record)
            except Exception as stop_error:events.append({'stopError':type(stop_error).__name__,'pid':record['pid']})
    finally:
        save(out/'result.json',result);save(out/'events.json',events);save(out/'source-readonly-commands.json',m.RECORDS)
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='PASS' else 2

if __name__=='__main__':sys.exit(main())
