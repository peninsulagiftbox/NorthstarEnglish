#!/usr/bin/env python3
"""Explicit Phase10B2 local release. Requires a source identity preflight and a fresh isolated restore.
Never restores over the personal DB, repairs history, deletes volumes, or submits learning attempts.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile
import local

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.local/phase10b2-release'
OUT=ROOT/'docs/handoff/evidence/phase10b2-deployment'
OLD=ROOT/'docs/handoff/evidence/phase10b1'
EXPECTED_DDL='8b32932f9447faf37a27dd449eb11106130d20637c887ce0bd0b8d2f5bdefa32'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')

def command(out,name,argv,env=None,cwd=ROOT,stdin=None,private=False,expected=(0,),timeout=600):
    env=env or local.environment();stamp=str(time.time_ns());start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(argv,cwd=cwd,env=env,input=stdin,capture_output=True,timeout=timeout)
    raw=p.stdout+b'\nSTDERR\n'+p.stderr
    for key,value in env.items():
        if 'PASSWORD' in key and value:raw=raw.replace(value.encode(),b'<REDACTED>')
    log_root=STATE/'private-command-logs'/out.name if private else out
    log=log_root/(name+'-'+stamp+'.log');log.parent.mkdir(parents=True,exist_ok=True);log.write_bytes(raw)
    row=dict(name=name,argv=[str(x) for x in argv],cwd=str(cwd),started=start,exitCode=p.returncode,gitSha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),log=str(log.relative_to(ROOT)),sha256=sha(log),private=private)
    with (out/'commands.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    print(json.dumps(dict(name=name,exitCode=p.returncode)),flush=True)
    if p.returncode not in expected:raise RuntimeError(name+' failed; retained log')
    return p

def source_hashes():
    paths=subprocess.check_output(['git','ls-files','apps','content','package.json','package-lock.json'],cwd=ROOT,text=True).splitlines()
    return {p:sha(ROOT/p) for p in paths if (ROOT/p).is_file()}

def safe_env():
    env=local.environment()
    env={k:v for k,v in env.items() if not k.startswith(('SPRING_','NORTHSTAR_')) and k not in ['JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','DB_NAME']}
    env.update(NORTHSTAR_DB_TEST='0',API_PORT='8085',WEB_PORT='3100',DB_NAME='northstar_english')
    return env

def build():
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
    private=STATE/stamp;out=OUT/stamp;workspace=private/'source';workspace.mkdir(parents=True);out.mkdir(parents=True)
    for name in ['apps/api','apps/web','content']:
        shutil.copytree(ROOT/name,workspace/name,ignore=shutil.ignore_patterns('target','.next','node_modules','*.tsbuildinfo'))
    for name in ['package.json','package-lock.json']:shutil.copyfile(ROOT/name,workspace/name)
    for name in ['node_modules','apps/web/node_modules']:
        if (ROOT/name).exists():(workspace/name).symlink_to(ROOT/name,target_is_directory=True)
    env=safe_env()
    command(out,'java-package',['apps/api/mvnw','-f','apps/api/pom.xml','package'],env,workspace)
    for name,argv in [('node-tests',['npm','test']),('typecheck',['npm','run','typecheck']),('lint',['npm','run','lint']),('web-build',['npm','run','build'])]:command(out,name,argv,env,workspace)
    classes=private/'migration-classes';classes.mkdir()
    c=load('deploy_campaign_build',OLD/'isolated_rehearsal.py')
    command(out,'compile-source-migration',[str(c.JAVA.parent/'javac'),'-cp',str(c.LIB/'*'),'-d',str(classes),str(ROOT/'scripts/phase10b2/ApprovedOrderMigration.java')],env)
    jar=workspace/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    routes=read(workspace/'apps/web/.next/routes-manifest.json')['rewrites'];routes=routes if isinstance(routes,list) else sum(routes.values(),[])
    assert any(x.get('destination')=='http://127.0.0.1:8085/api/v1/:path*' for x in routes)
    with zipfile.ZipFile(jar) as archive:
        assert hashlib.sha256(archive.read('BOOT-INF/classes/db/migration/V009_05__lesson_catalog_order.sql')).hexdigest()==EXPECTED_DDL
    release=dict(run=stamp,private=str(private.relative_to(ROOT)),workspace=str(workspace.relative_to(ROOT)),jarSha256=sha(jar),sourceFiles=source_hashes(),gitSha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    save(out/'release.json',release);(STATE/'LATEST').write_text(stamp+'\n');print('Release prepared: '+stamp,flush=True)

def context(run):
    assert run.isalnum();out=OUT/run;release=read(out/'release.json');private=ROOT/release['private']
    assert source_hashes()==release['sourceFiles'],'Application bytes changed since release build'
    jar=ROOT/release['workspace']/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar';assert sha(jar)==release['jarSha256']
    assert sha(ROOT/'apps/api/src/main/resources/db/migration/V009_05__lesson_catalog_order.sql')==EXPECTED_DDL
    return out,private,release,jar

def identity(m,c,env):
    item=local.verify_container(env)
    assert item['Id']==m.CONTAINER and item['State']['Status']=='running'
    data=json.loads(m.sql("SELECT JSON_OBJECT('uuid',@@server_uuid,'schema',DATABASE(),'project',(SELECT project_key FROM project_identity),'account',CURRENT_USER())"))
    assert data==dict(uuid=c.SOURCE_UUID,schema='northstar_english',project=local.IDENTITY,account='root@%')
    return data

def services():
    result={}
    for name,port in [('api',8085),('web',3100)]:
        record=read(ROOT/'.local'/(name+'.json'));assert local.owns_process(record),'Unowned source '+name
        listeners=subprocess.check_output(['lsof','-t','-iTCP:'+str(port),'-sTCP:LISTEN'],text=True).splitlines();assert len(set(listeners))==1
        pid=listeners[0];parent=subprocess.check_output(['ps','-p',pid,'-o','ppid='],text=True).strip();assert int(parent)==record['pid'],'Listener not owned by recorded supervisor'
        cwd=subprocess.check_output(['lsof','-a','-p',pid,'-d','cwd','-Fn'],text=True)
        assert 'n'+str(ROOT/'apps'/name)+'\n' in cwd
        commandline=subprocess.check_output(['ps','-p',pid,'-o','command='],text=True)
        if name=='api':
            assert str(ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar') in commandline
            assert '--northstar.content-root='+str(ROOT/'content') in commandline
            assert '--northstar.recording-root='+str(Path.home()/'Library/Application Support/NorthstarEnglish/recordings') in commandline
        result[name]=dict(record=record,listenerPid=int(pid),port=port)
    return result

def preflight(run):
    out,private,release,jar=context(run);m=load('source_read_preflight',OLD/'maintenance_backup.py');c=load('isolated_identity_preflight',OLD/'isolated_rehearsal.py');env=local.environment()
    data=identity(m,c,env);runtime=services()
    history=json.loads(m.sql("SELECT JSON_ARRAYAGG(JSON_OBJECT('version',version,'script',script,'checksum',checksum,'success',success)) FROM flyway_schema_history"))
    assert len(history)==13 and all(x['success']==1 for x in history)
    assert m.sql('SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1').strip()=='009.04'
    assert shutil.disk_usage(ROOT).free>6*1024**3
    save(private/'old-services.json',runtime)
    save(out/'preflight.json',dict(status='PASS',identity=data,services=runtime,history=history,releaseJarSha256=release['jarSha256'],sourceWrites=False))
    save(out/'preflight-readonly-commands.json',m.RECORDS)
    save(out/'authorization.json',dict(userInstruction='也执行个人库迁移与本地部署',scope='Verified personal V009.04 -> frozen V009.05 only; fresh backup and isolated restore; deploy tested backend/frontend on existing origin',noApprovalForSourceRestore=True))
    print('Preflight PASS; no services stopped or source data written',flush=True)

def stop_record(record):
    assert local.owns_process(record),'Refuse to signal unowned process'
    os.kill(record['pid'],signal.SIGTERM)
    for _ in range(100):
        if not local.owns_process(record):return
        time.sleep(.2)
    raise RuntimeError('Owned service stop timeout')

def execute(run):
    out,private,release,jar=context(run);assert read(out/'preflight.json')['status']=='PASS';assert read(out/'authorization.json')['userInstruction']=='也执行个人库迁移与本地部署'
    env=safe_env();m=load('source_backup_execution',OLD/'maintenance_backup.py');c=load('isolated_restore_execution',OLD/'isolated_rehearsal.py');runtime=load('media_execution',OLD/'runtime_media_preflight.py');order=load('order_compare_execution',ROOT/'scripts/phase10b2_isolated.py')
    before_services=services();assert before_services==read(private/'old-services.json'),'Source processes changed since preflight'
    identity(m,c,env)
    old_jar=ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar';shutil.copyfile(old_jar,private/'previous-api.jar')
    paths=dict(content=ROOT/'content',recordings=Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english')
    result=dict(status='BLOCKED',sourceMigrationAttempted=False,servicesRestored=False);owned=[];created=False
    try:
        for name in ['web','api']:stop_record(before_services[name]['record'])
        for port in [3100,8085]:assert local.available(port),'A source listener remains'
        assert int(m.sql("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE DB='northstar_english' AND ID<>CONNECTION_ID()"))==0
        assert int(m.sql('SELECT COUNT(*) FROM information_schema.INNODB_TRX WHERE trx_mysql_thread_id<>CONNECTION_ID()'))==0
        before=m.snapshot();backup=private/'backup';backup.mkdir();save(backup/'source-snapshot.json',before)
        (backup/'restore.sql').write_text(m.restore_sql(before))
        dump='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --protocol=TCP -h127.0.0.1 -uroot --single-transaction --skip-lock-tables --no-tablespaces --set-gtid-purged=OFF --hex-blob --order-by-primary --skip-add-drop-table --skip-add-locks --skip-disable-keys --skip-dump-date northstar_english'
        p=command(out,'fresh-sql-dump',[m.DOCKER,'exec',m.CONTAINER,'sh','-c',dump],env,private=True);(backup/'source.sql').write_bytes(p.stdout)
        media={}
        for name,path in paths.items():
            media[name]=runtime.inventory(path);shutil.copytree(path,backup/name);assert runtime.inventory(backup/name)==media[name]
        save(backup/'media-manifest.json',media)
        manifest=[dict(path=str(p.relative_to(backup)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(backup.rglob('*')) if p.is_file()]
        save(backup/'SHA256SUMS.json',manifest)
        assert m.snapshot()==before and all(runtime.inventory(p)==media[k] for k,p in paths.items())
        c.PRIVATE=private/'isolated';c.PRIVATE.mkdir();c.OUT=out/'isolated';c.OUT.mkdir();c.NAMESPACE='northstar-order-release-'+run.lower();c.BACKUP=backup;c.PATCHED_JAR=jar
        port=3354
        while port<3399 and (not c.available(port) or not c.available(8093+port-3313)):port+=1
        assert port<3399;c.ROLES=['reserved'+str(i) for i in range(port-3313)]+['fresh']
        original_call=c.call;nonce=str(time.time_ns())
        def unique_call(name,*args,**kwargs):return original_call(nonce+'-'+name,*args,**kwargs)
        c.call=unique_call
        app_grants=m.sql("SHOW GRANTS FOR 'northstar_app'@'%'")
        def actual_grants(role):
            grants='\n'.join(line+';' for line in app_grants.splitlines() if ' ON `northstar_english`.' in line)
            assert grants;c.sql(role,grants)
        c.grant_app=actual_grants
        c.create('fresh');created=True;c.prepare_files('fresh');c.restore('fresh');c.compare(before,c.snapshot('fresh','fresh-restored-v00904'))
        d=c.verify('fresh');cred=read(c.PRIVATE/'fresh/credentials.json')
        migration_env=dict(env,TARGET_MYSQL_PORT=str(d['port']),EXPECTED_TARGET_UUID=d['uuid'],TARGET_PASSWORD=cred['migrator'],TARGET_USER='northstar_migrator',MIGRATION_TARGET='009.05')
        c.call('fresh-upgrade-flyway',[str(c.JAVA),'-cp',str(c.CLASSES)+os.pathsep+str(c.LIB/'*'),'MigrationHarness',str(ROOT/'apps/api/src/main/resources/db/migration')],env=migration_env,private=True)
        upgraded=c.snapshot('fresh','fresh-upgraded-v00905');order.compare_order(before,upgraded)
        for i in range(2):
            handle=c.start_api('fresh',True)
            try:c.read_application('fresh',handle)
            finally:c.end_api('fresh',handle)
            c.compare(upgraded,c.snapshot('fresh','release-start-'+str(i)));c.media_check('fresh')
        c.stop('fresh');save(out/'fresh-backup-isolated-validation.json',dict(status='PASS',uuid=d['uuid'],port=d['port'],restoredFromFreshBackup=True,oldColumnsExact=True,twoNewJarStartsExact=True,mediaExact=True,jarSha256=sha(jar),backupManifestSha256=sha(backup/'SHA256SUMS.json')))
        identity(m,c,env);assert m.snapshot()==before,'Source drift since fresh backup'
        assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
        source_env=dict(env,NORTHSTAR_APPROVED_ACTION='phase10b2-source-order-v1',EXPECTED_SOURCE_UUID=c.SOURCE_UUID)
        result['sourceMigrationAttempted']=True
        command(out,'approved-source-v00905',[str(c.JAVA),'-cp',str(private/'migration-classes')+os.pathsep+str(c.LIB/'*'),'ApprovedOrderMigration',str(ROOT/'apps/api/src/main/resources/db/migration')],source_env)
        after=m.snapshot();order.compare_order(before,after);save(private/'source-after-v00905.json',after)
        assert m.sql('SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1').strip()=='009.05'
        assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
        result['sourceOldColumnsExact']=True
        shutil.copyfile(jar,old_jar);assert sha(old_jar)==release['jarSha256']
        next_dir=ROOT/'apps/web/.next';next_dir.rename(private/'previous-web-build');shutil.copytree(ROOT/release['workspace']/'apps/web/.next',next_dir)
        api_argv=[str(c.JAVA),'-jar',str(old_jar),'--northstar.recording-root='+str(paths['recordings'].parent),'--northstar.content-root='+str(paths['content'])]
        def get(path,port=8085):
            with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=15) as response:body=response.read();status=response.status
            with (out/'http-reads.jsonl').open('a') as f:f.write(json.dumps(dict(method='GET',port=port,path=path if '/recordings/' not in path else '[private recording audio]',status=status,sha256=hashlib.sha256(body).hexdigest()))+'\n')
            return body
        for i in range(2):
            local.start_process('api',api_argv,ROOT/'apps/api',env,str(old_jar));record=read(ROOT/'.local/api.json');owned.append(record);local.wait_health('http://127.0.0.1:8085/api/v1/health')
            assert json.loads(get('/api/v1/health'))['migrationVersion']=='009.05'
            for path in ['/books','/lessons','/lessons/demo-01/versions','/lessons/demo-01?versionId=demo-01-v1','/lessons/demo-01?versionId=demo-01-v2','/study/resume','/reviews/due','/writing?lessonId=demo-01&versionId=demo-01-v2']:get('/api/v1'+path)
            c.compare(after,m.snapshot());assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
            if i==0:stop_record(record);owned.remove(record)
        export=json.loads(get('/api/v1/data/export'));assert json.loads(export['payloadJson'])['schemaVersion']=='009.05';save(private/'source-v00905-export.json',export)
        cli=ROOT/'node_modules/next/dist/bin/next'
        local.start_process('web',['node',str(cli),'start','--hostname','127.0.0.1','--port','3100'],ROOT/'apps/web',env,str(cli));owned.append(read(ROOT/'.local/web.json'));local.wait_health('http://127.0.0.1:3100/api/v1/health')
        assert json.loads(get('/api/v1/health',3100))['migrationVersion']=='009.05'
        get('/courses',3100);get('/dashboard',3100);c.compare(after,m.snapshot());assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
        result.update(status='PASS',servicesRestored=True,sourceVersion='009.05',newJarTwoStartsExact=True,webProxyAndPages=True,mediaExact=True,exportVersion='009.05',jarSha256=sha(old_jar),backupManifestSha256=sha(backup/'SHA256SUMS.json'),sourceLearningTestSubmissions=0,services=owned)
    except Exception as error:
        result['reason']=type(error).__name__+': '+str(error)
        for record in reversed(owned):
            if local.owns_process(record):stop_record(record)
        raise
    finally:
        if created:
            try:c.stop('fresh')
            except Exception:result['isolatedStopNeedsInspection']=True
        save(out/'result.json',result);save(out/'source-readonly-commands.json',m.RECORDS)
        if c.RECORDS:save(out/'isolated-commands.json',c.RECORDS)
    print(json.dumps({k:v for k,v in result.items() if k not in ['services']},ensure_ascii=False),flush=True)

if __name__=='__main__':
    os.umask(0o077);parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','preflight','execute']);parser.add_argument('run',nargs='?');args=parser.parse_args()
    if args.action=='build':build()
    elif args.action=='preflight':preflight(args.run)
    else:execute(args.run)
