#!/usr/bin/env python3
"""Approved fixed personal migration; requires a freshly verified backup and stopped services."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phase10b1'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def decode(data):return [dict(zip(data['columns'],[None if v is None else bytes.fromhex(v).decode() for v in row])) for row in data['rows']]

def main():
    assert len(sys.argv)==3 and sys.argv[1]=='--execute-approved-personal-migration'
    os.umask(0o077)
    run=sys.argv[2]; assert run.isalnum()
    prepared=HERE/run; pre=json.loads((prepared/'result.json').read_text())
    assert pre['status']=='FRESH_BACKUP_RESTORE_AND_CANDIDATE_PASS' and pre['isolatedStopped']
    compatibility=json.loads((prepared/'application-compatibility/result.json').read_text())
    assert compatibility['status']=='PASS' and compatibility['fullV009RestoreAndRestartPass']
    authorization=json.loads((HERE/'authorization.json').read_text())
    assert authorization['independentReviewWaiver']=='明确豁免，按冻结候选完成迁移'
    private=ROOT/'.local/personal-migration'/run
    backup=private/'backup'
    assert hashlib.sha256((backup/'SHA256SUMS.json').read_bytes()).hexdigest()==pre['backupManifestSha256']
    for row in json.loads((backup/'SHA256SUMS.json').read_text()):
        p=backup/row['path']; assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
    out=prepared/'personal-execution';out.mkdir()
    m=load('backup',OLD/'maintenance_backup.py');c=load('campaign',OLD/'isolated_rehearsal.py');runtime=load('runtime',OLD/'runtime_media_preflight.py');local=load('local',ROOT/'scripts/local.py')
    records=[];result={'status':'BLOCKED','sourceWriteAttempted':False,'versionsExecuted':[],'servicesStarted':False}
    def save(path,value):
        with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    def verify_identity():
        env=local.environment();item=local.verify_container(env)
        assert item['Id']==m.CONTAINER and item['State']['Status']=='running'
        identity=json.loads(m.sql("SELECT JSON_OBJECT('uuid',@@server_uuid,'schema',DATABASE(),'project',(SELECT project_key FROM project_identity),'account',CURRENT_USER())"))
        assert identity==pre['identity'];return env
    def journal():
        (out/'commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    try:
        env=verify_identity()
        assert c.digest(c.OLD_JAR)==compatibility['applicationJarSha256'],'Application changed since isolated compatibility validation'
        save(out/'account-grants.json',{'root':m.sql('SHOW GRANTS FOR CURRENT_USER'),'migrator':m.sql("SHOW GRANTS FOR 'northstar_migrator'@'%'"),'app':m.sql("SHOW GRANTS FOR 'northstar_app'@'%'"),'note':'Existing account grants checked read-only; no grant/secret changes'})
        for port in [8085,3100]:
            p=subprocess.run(['lsof','-nP','-iTCP:'+str(port),'-sTCP:LISTEN'],capture_output=True,text=True)
            assert p.returncode==1 and not p.stdout,'Source services must remain stopped'
        assert int(m.sql('SELECT COUNT(*) FROM information_schema.INNODB_TRX WHERE trx_mysql_thread_id<>CONNECTION_ID()'))==0
        assert int(m.sql("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() AND DB='northstar_english'"))==0
        before=json.loads((backup/'source-snapshot.json').read_text());assert m.snapshot()==before,'Backup no longer fresh: source rows/schema changed'
        media=json.loads((backup/'media-manifest.json').read_text())
        paths={'recordings':Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english','content':ROOT/'content'}
        assert all(runtime.inventory(p)==media[k] for k,p in paths.items()),'Backup no longer fresh: media changed'
        manifest=json.loads((OLD/'candidate/candidate-manifest.json').read_text())
        directory=ROOT/'apps/api/src/main/resources/db/migration'
        assert {p.name for p in directory.glob('*.sql')}=={h['script'] for h in decode(before['flyway_schema_history']) if h['type']=='SQL'}|{Path(x['path']).name for x in manifest['files']}
        for item in manifest['files']:
            p=directory/Path(item['path']).name; assert c.digest(p)==item['sha256']
        for h in decode(before['flyway_schema_history']):
            if h['type']=='SQL':
                p=directory/h['script'];assert p.read_bytes()==subprocess.run(['git','show','HEAD:'+str(p.relative_to(ROOT))],capture_output=True,check=True).stdout
        migration_env={k:v for k,v in env.items() if not k.startswith(('SPRING_','NORTHSTAR_')) and k not in ['JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS']}
        migration_env.update(APPROVAL_SCOPE='personal-migration-20261027',APPROVED_MIGRATION_DIRECTORY=str(directory))
        for version in manifest['versions']:
            verify_identity()
            argv=[str(c.JAVA),'-cp',str(ROOT/'.local/personal-migration-tools/classes')+os.pathsep+str(c.LIB/'*'),'ApprovedPersonalMigration','--execute-approved-personal-migration',version,str(directory)]
            started=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
            result['sourceWriteAttempted']=True
            p=subprocess.run(argv,env=migration_env,capture_output=True,timeout=90)
            log=out/('flyway-'+version+'.log');log.write_bytes(p.stdout+b'\nSTDERR\n'+p.stderr)
            records.append({'argv':argv,'started':started,'returncode':p.returncode,'log':str(log.relative_to(ROOT)),'sha256':c.digest(log)})
            journal()
            assert p.returncode==0,'Flyway failed: preserve source schema/history and keep services stopped'
            result['versionsExecuted'].append(version)
            current=m.snapshot();save(private/('source-after-'+version+'.json'),current)
            c.compare(before,current,allow_new=True,paragraph_column_required=version!='009.01')
            save(out/('after-'+version+'.json'),{'oldColumnsExact':True,'counts':{t:len(v['rows']) for t,v in current.items()},'snapshotSha256':c.digest(private/('source-after-'+version+'.json')),'schema':{t:v['createSql'] for t,v in current.items()}})
        final=current
        paragraphs=decode(final['paragraph']); assert len(paragraphs)==2
        mapping={'demo-01-v1':'af61b21b-371a-4550-85a2-8301db66a325','demo-01-v2':'a214bafb-e722-4f77-b5ed-62311f41b116'}
        assert all(p['id']==mapping[p['version_id']] and p['stable_key']=='original-dialogue' and p['sequence_no']=='1' for p in paragraphs)
        assert all(s['paragraph_id']==mapping[s['lesson_version_id']] for s in decode(final['sentence']))
        history=decode(final['flyway_schema_history']); new=[h for h in history if h['version'] in manifest['versions']]
        assert len(history)==len(before['flyway_schema_history']['rows'])+4 and len(new)==4
        for h in new:
            crc=0
            for line in (directory/h['script']).read_text(encoding='utf-8-sig').splitlines():crc=zlib.crc32(line.encode(),crc)
            assert h['success']=='1' and h['type']=='SQL' and int(h['checksum'])==(crc if crc<2**31 else crc-2**32)
        expected=json.loads((private/'isolated/fresh/after-new-start-1.json').read_text())
        assert {t:v['createSql'] for t,v in final.items()}=={t:v['createSql'] for t,v in expected.items()},'Source schema differs from fresh rehearsal'
        assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
        argv=[str(c.JAVA),'-cp',str(ROOT/'.local/personal-migration-tools/classes')+os.pathsep+str(c.LIB/'*'),'ApprovedPersonalMigration','--execute-approved-personal-migration','validate',str(directory)]
        p=subprocess.run(argv,env=migration_env,capture_output=True,timeout=45)
        (out/'flyway-validate.log').write_bytes(p.stdout+b'\nSTDERR\n'+p.stderr)
        records.append({'argv':argv,'returncode':p.returncode,'log':str((out/'flyway-validate.log').relative_to(ROOT))});journal();assert p.returncode==0
        result.update(status='PERSONAL_MIGRATION_PASS_SERVICES_STILL_STOPPED',oldColumnsExact=True,mediaHashesUnchanged=True,sourceVersion='009.04',schemaMatchesFreshRehearsal=True,historyCrc32Matches=True,sourceWriteScope='Four frozen V009 migrations and Flyway history only; no test learning writes',privateBackup=str(backup.relative_to(ROOT)))
    except Exception as error:
        result['reason']=type(error).__name__+': '+str(error)
        try:
            save(private/'source-on-failure.json',m.snapshot());result['failureStateCaptured']=True
        except Exception:result['failureStateCaptured']=False
    finally:
        save(out/'source-readonly-commands.json',m.RECORDS);journal();save(out/'result.json',result)
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='PERSONAL_MIGRATION_PASS_SERVICES_STILL_STOPPED' else 2

if __name__=='__main__':sys.exit(main())
