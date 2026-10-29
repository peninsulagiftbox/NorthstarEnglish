#!/usr/bin/env python3
"""Approved Phase10B3 Git/local release. Fresh backup -> new restore -> same compiled guard -> source.
No source restore, history repair, content initialization, learning submissions or volume deletion.
"""
import argparse,datetime,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,urllib.request,zipfile
from pathlib import Path
import local
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('release_helpers_b3',ROOT/'scripts/deploy-phase10b2.py')
base.STATE=ROOT/'.local/phase10b3-release';base.OUT=ROOT/'docs/handoff/evidence/phase10b3-deployment'
STATE,OUT=base.STATE,base.OUT
sha,read,save,command=base.sha,base.read,base.save,base.command
OLD=base.OLD

def hashes(root):
    files=[]
    for prefix in ['apps/api/src','apps/web/src','apps/web/tests']:
        files.extend(p for p in (root/prefix).rglob('*') if p.is_file())
    for name in ['package.json','package-lock.json','apps/api/pom.xml','apps/web/package.json','apps/web/next.config.ts']:
        files.append(root/name)
    return {str(p.relative_to(root)):sha(p) for p in sorted(files)}

def context(run):
    assert run.isalnum();out=OUT/run;private=STATE/run;release=read(out/'release.json');workspace=ROOT/release['workspace'];jar=workspace/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    assert sha(jar)==release['jarSha256'] and hashes(workspace)==release['builtFiles']
    accepted=read(ROOT/'docs/handoff/evidence/phase10b3/delivery-audit.json')
    for item in accepted['businessSourceMatchesBuild']:
        if item['path'].startswith('apps/api/'):assert sha(ROOT/item['path'])==item['sha256'],'API source changed since acceptance'
    for item in read(ROOT/'docs/handoff/evidence/phase10b3/frozen-migrations-appended.json'):assert sha(ROOT/item['path'])==item['sha256']
    return out,private,release,workspace,jar

def build(include_ui):
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%dT%H%M%S');private=STATE/stamp;out=OUT/stamp;workspace=private/'source';workspace.mkdir(parents=True);out.mkdir(parents=True)
    accepted=read(ROOT/'docs/handoff/evidence/phase10b3/delivery-audit.json');tested=ROOT/'.local/phase10b3/source-final'
    for name in ['apps/api','apps/web','content']:
        shutil.copytree(ROOT/name,workspace/name,ignore=shutil.ignore_patterns('target','.next','node_modules','*.tsbuildinfo'))
    for name in ['package.json','package-lock.json']:shutil.copyfile(ROOT/name,workspace/name)
    for name in ['node_modules','apps/web/node_modules']:
        if (ROOT/name).exists():(workspace/name).symlink_to(ROOT/name,target_is_directory=True)
    if not include_ui:
        for name in ['apps/web/src/app/globals.css','apps/web/src/components/CatalogPages.tsx']:
            expected=next(x['sha256'] for x in accepted['businessSourceMatchesBuild'] if x['path']==name)
            assert sha(tested/name)==expected;shutil.copyfile(tested/name,workspace/name)
    jar=workspace/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar';jar.parent.mkdir()
    source_jar=tested/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar';assert sha(source_jar)==accepted['finalCandidate']['finalJarSha256'];shutil.copyfile(source_jar,jar)
    for item in accepted['businessSourceMatchesBuild']:
        if item['path'].startswith('apps/api/'):assert sha(workspace/item['path'])==item['sha256']
    env=base.safe_env()
    for name,argv in [('node-tests',['npm','test']),('typecheck',['npm','run','typecheck']),('lint',['npm','run','lint']),('web-build',['npm','run','build'])]:command(out,name,argv,env,workspace)
    c=load('release_guard_libraries',OLD/'isolated_rehearsal.py');classes=private/'migration-classes';classes.mkdir()
    command(out,'compile-approved-identity-guard',[str(c.JAVA.parent/'javac'),'-cp',str(c.LIB/'*'),'-d',str(classes),str(ROOT/'scripts/phase10b3/ApprovedIdentityMigration.java')],env)
    routes=read(workspace/'apps/web/.next/routes-manifest.json')['rewrites'];routes=routes if isinstance(routes,list) else sum(routes.values(),[])
    assert any(x.get('destination')=='http://127.0.0.1:8085/api/v1/:path*' for x in routes)
    with zipfile.ZipFile(jar) as archive:
        for item in read(ROOT/'docs/handoff/evidence/phase10b3/frozen-migrations-appended.json'):
            assert hashlib.sha256(archive.read('BOOT-INF/classes/db/migration/'+Path(item['path']).name)).hexdigest()==item['sha256']
    save(out/'release.json',dict(run=stamp,workspace=str(workspace.relative_to(ROOT)),jarSha256=sha(jar),builtFiles=hashes(workspace),includeUiHead=include_ui,acceptedBusinessJarReused=True,gitSha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),guardSha256=sha(ROOT/'scripts/phase10b3/ApprovedIdentityMigration.java'),guardClassSha256=sha(classes/'ApprovedIdentityMigration.class')))
    (STATE/'LATEST').write_text(stamp+'\n');print('Release prepared: '+stamp,flush=True)

def modules(tag):
    return (load('source_'+tag,OLD/'maintenance_backup.py'),load('isolated_'+tag,OLD/'isolated_rehearsal.py'),load('media_'+tag,OLD/'runtime_media_preflight.py'),load('b3_comparison_'+tag,ROOT/'scripts/phase10b3_isolated.py'))

def preflight(run):
    out,private,release,workspace,jar=context(run);m,c,runtime,b3=modules('preflight');env=base.safe_env();identity=base.identity(m,c,env);processes=base.services()
    history=json.loads(m.sql("SELECT JSON_ARRAYAGG(JSON_OBJECT('version',version,'script',script,'checksum',checksum,'success',success)) FROM flyway_schema_history"))
    assert len(history)==14 and all(x['success']==1 for x in history)
    assert len(m.sql('SHOW TABLES').splitlines())==38,'Unexpected pre-migration schema; do not start maintenance'
    assert m.sql('SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1').strip()=='009.05'
    assert m.sql("SELECT COUNT(*) FROM lesson WHERE id<>'demo-01'").strip()=='0'
    assert shutil.disk_usage(ROOT).free>6*1024**3
    save(private/'old-services.json',processes)
    save(out/'preflight.json',dict(status='PASS',identity=identity,history=history,services=processes,sourceWrites=False))
    save(out/'authorization.json',dict(userInstruction='审核通过，提交github并在本地进行部署',scope='Reviewed Phase10B3 frozen 009.05->009.15; fresh private backup and same-entry-point isolated restore before source maintenance',sourceRestoreAuthorized=False))
    save(out/'preflight-readonly-commands.json',m.RECORDS);print('Preflight PASS: personal DB unchanged',flush=True)

def compare_upgrade(before,after,b3):
    b3.compare_old(before,after)
    assert set(after)-set(before)=={'sentence_identity','paragraph_identity','version_sentence_map','content_validation','publication_audit'}
    additions={'sentence':{'identity_id'},'paragraph':{'lesson_id','identity_id'},'lesson_version':{'publication_state','content_readiness','schema_version','published_at'}}
    for name,data in before.items():
        new=after[name];assert data['primaryKey']==new['primaryKey'];assert set(new['columns'])-set(data['columns'])==additions.get(name,set())
        oldlines={line.strip().rstrip(',') for line in data['createSql'].splitlines()};newlines={line.strip().rstrip(',') for line in new['createSql'].splitlines()}
        for column in data['columns']:
            original=next(x for x in oldlines if x.startswith('`'+column+'` '));assert original in newlines,name+': existing column definition changed'
        for line in oldlines:
            if line.startswith('CONSTRAINT ') or line.startswith('UNIQUE KEY ') or line.startswith('PRIMARY KEY '):
                if name=='lesson' and '`lesson_chk_1`' in line:continue
                if name=='audio_asset' and '`audio_asset_chk_1`' in line:continue
                assert line in newlines,name+': existing constraint changed'
    assert len(after['sentence_identity']['rows'])==20 and len(after['paragraph_identity']['rows'])==2
    assert all(not after[name]['rows'] for name in ['version_sentence_map','content_validation','publication_audit'])


def guard(out,private,c,env,name,rehearse=False):
    assert sha(ROOT/'scripts/phase10b3/ApprovedIdentityMigration.java')==read(out/'release.json')['guardSha256']
    assert sha(private/'migration-classes/ApprovedIdentityMigration.class')==read(out/'release.json')['guardClassSha256']
    return command(out,name,[str(c.JAVA),'-cp',str(private/'migration-classes')+os.pathsep+str(c.LIB/'*'),'ApprovedIdentityMigration']+(['--rehearse'] if rehearse else [])+[str(ROOT/'apps/api/src/main/resources/db/migration')],env,private=True)

def source_paths():return dict(content=ROOT/'content',recordings=Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english')

def install(out,private,release,jar,env,m,c,runtime,after,media,result):
    root_jar=ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar';next_dir=ROOT/'apps/web/.next';release_next=ROOT/release['workspace']/'apps/web/.next'
    assert not (private/'previous-web-build').exists();next_dir.rename(private/'previous-web-build');shutil.copytree(release_next,next_dir);shutil.copyfile(jar,root_jar)
    assert sha(root_jar)==release['jarSha256']
    paths=source_paths();api=[str(c.JAVA),'-jar',str(root_jar),'--northstar.content-root='+str(paths['content']),'--northstar.recording-root='+str(paths['recordings'].parent)]
    for i in range(2):
        local.start_process('api',api,ROOT/'apps/api',env,str(root_jar));record=read(ROOT/'.local/api.json');local.wait_health('http://127.0.0.1:8085/api/v1/health')
        for path in ['/health','/books','/lessons','/lessons/demo-01/versions','/lessons/demo-01?versionId=demo-01-v1','/lessons/demo-01?versionId=demo-01-v2','/study/resume','/reviews/due']:
            with urllib.request.urlopen('http://127.0.0.1:8085/api/v1'+path,timeout=10) as response:
                body=response.read();status=response.status
                if path=='/health':assert json.loads(body)['migrationVersion']=='009.15'
                if path.startswith('/lessons/demo-01?'):assert json.loads(body)['contentReadiness']=='legacy_unassessed'
            with (out/'http-reads.jsonl').open('a') as f:f.write(json.dumps(dict(method='GET',path=path,status=status,sha256=hashlib.sha256(body).hexdigest()))+'\n')
        assert m.snapshot()==after;assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
        if i==0:base.stop_record(record)
    cli=ROOT/'node_modules/next/dist/bin/next';local.start_process('web',['node',str(cli),'start','--hostname','127.0.0.1','--port','3100'],ROOT/'apps/web',env,str(cli));local.wait_health('http://127.0.0.1:3100/api/v1/health')
    with urllib.request.urlopen('http://127.0.0.1:3100/api/v1/health',timeout=10) as response:assert json.load(response)['migrationVersion']=='009.15'
    assert m.snapshot()==after;assert all(runtime.inventory(p)==media[k] for k,p in paths.items())
    result.update(status='PASS',sourceVersion='009.15',all38OriginalTablesColumnsExact=True,all43TablesExactAfterTwoRestarts=True,mediaExact=True,sourceLearningSubmissions=0,servicesRestored=True,jarSha256=sha(root_jar),webBuildId=(next_dir/'BUILD_ID').read_text().strip())


def execute(run):
    out,private,release,workspace,jar=context(run);assert read(out/'preflight.json')['status']=='PASS';assert read(out/'authorization.json')['userInstruction']=='审核通过，提交github并在本地进行部署'
    m,c,runtime,b3=modules('execute');env=base.safe_env();base.identity(m,c,env);processes=base.services();assert processes==read(private/'old-services.json')
    shutil.copyfile(ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar',private/'previous-api.jar');paths=source_paths()
    result=dict(status='BLOCKED',sourceMigrationAttempted=False,servicesRestored=False);created=False
    try:
        for name in ['web','api']:base.stop_record(processes[name]['record'])
        assert all(local.available(port) for port in [3100,8085])
        assert int(m.sql("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE DB='northstar_english' AND ID<>CONNECTION_ID()"))==0
        assert int(m.sql('SELECT COUNT(*) FROM information_schema.INNODB_TRX WHERE trx_mysql_thread_id<>CONNECTION_ID()'))==0
        before=m.snapshot();backup=private/'backup';backup.mkdir();save(backup/'source-snapshot.json',before);(backup/'restore.sql').write_text(m.restore_sql(before))
        dump='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump --protocol=TCP -h127.0.0.1 -uroot --single-transaction --skip-lock-tables --no-tablespaces --set-gtid-purged=OFF --hex-blob --order-by-primary --skip-add-drop-table --skip-add-locks --skip-disable-keys --skip-dump-date northstar_english'
        p=command(out,'fresh-source-sql-backup',[m.DOCKER,'exec',m.CONTAINER,'sh','-c',dump],env,private=True);(backup/'source.sql').write_bytes(p.stdout)
        media={}
        for name,path in paths.items():media[name]=runtime.inventory(path);shutil.copytree(path,backup/name);assert runtime.inventory(backup/name)==media[name]
        save(backup/'media-manifest.json',media);save(backup/'SHA256SUMS.json',[dict(path=str(p.relative_to(backup)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(backup.rglob('*')) if p.is_file()])
        assert m.snapshot()==before and all(runtime.inventory(path)==media[name] for name,path in paths.items())
        c.PRIVATE=private/'isolated';c.PRIVATE.mkdir();c.OUT=out/'isolated';c.OUT.mkdir();c.NAMESPACE='northstar-identity-release-'+run.lower();c.BACKUP=backup;c.PATCHED_JAR=jar
        port=3372
        while port<3399 and (not c.available(port) or not c.available(8093+port-3313)):port+=1
        assert port<3399;c.ROLES=['reserved'+str(i) for i in range(port-3313)]+['fresh'];original_call=c.call;nonce=str(time.time_ns());c.call=lambda name,*a,**kw:original_call(nonce+'-'+name,*a,**kw)
        app_grants=m.sql("SHOW GRANTS FOR 'northstar_app'@'%'")
        def grant_app(role):c.sql(role,'\n'.join(line+';' for line in app_grants.splitlines() if ' ON `northstar_english`.' in line))
        c.grant_app=grant_app;c.create('fresh');created=True;c.prepare_files('fresh');c.restore('fresh');assert c.snapshot('fresh','fresh-restored-00905')==before
        d=c.verify('fresh');cred=read(c.PRIVATE/'fresh/credentials.json');iso_env=dict(env,MYSQL_PORT=str(d['port']),DB_MIGRATION_PASSWORD=cred['migrator'],EXPECTED_TARGET_UUID=d['uuid'],NORTHSTAR_APPROVED_ACTION='phase10b3-isolated-v00915-v1')
        guard(out,private,c,iso_env,'same-compiled-guard-isolated',True)
        upgraded=c.snapshot('fresh','fresh-upgraded-00915');compare_upgrade(before,upgraded,b3)
        for i in range(2):
            handle=c.start_api('fresh',True)
            try:c.read_application('fresh',handle)
            finally:c.end_api('fresh',handle)
            assert c.snapshot('fresh','same-guard-restart-'+str(i))==upgraded;c.media_check('fresh')
        c.stop('fresh');save(out/'fresh-backup-isolated-validation.json',dict(status='PASS',sameCompiledGuard=True,oldColumnsExact=True,twoCandidateStartsExact=True,mediaExact=True,guardClassSha256=release['guardClassSha256'],backupManifestSha256=sha(backup/'SHA256SUMS.json')))
        base.identity(m,c,env);assert m.snapshot()==before and all(runtime.inventory(path)==media[name] for name,path in paths.items())
        result['sourceMigrationAttempted']=True
        guard(out,private,c,dict(env,EXPECTED_SOURCE_UUID=c.SOURCE_UUID,NORTHSTAR_APPROVED_ACTION='phase10b3-source-v00915-v1'),'approved-personal-00905-to-00915')
        after=m.snapshot();compare_upgrade(before,after,b3);save(private/'source-after-00915.json',after)
        assert m.sql('SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1').strip()=='009.15'
        assert all(runtime.inventory(path)==media[name] for name,path in paths.items())
        install(out,private,release,jar,env,m,c,runtime,after,media,result)
    except Exception as error:
        result['reason']=type(error).__name__+': '+str(error)
        # Before any DDL, a complete unchanged snapshot permits restoring only the old services.
        if not result['sourceMigrationAttempted'] and 'before' in locals() and m.snapshot()==before:
            old_jar=ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
            if local.available(8085):local.start_process('api',[str(c.JAVA),'-jar',str(old_jar),'--northstar.content-root='+str(paths['content']),'--northstar.recording-root='+str(paths['recordings'].parent)],ROOT/'apps/api',env,str(old_jar));local.wait_health('http://127.0.0.1:8085/api/v1/health')
            if local.available(3100):
                cli=ROOT/'node_modules/next/dist/bin/next';local.start_process('web',['node',str(cli),'start','--hostname','127.0.0.1','--port','3100'],ROOT/'apps/web',env,str(cli));local.wait_health('http://127.0.0.1:3100/api/v1/health')
            result['oldServicesRestoredBeforeDDL']=True
        raise
    finally:
        if created:
            try:c.stop('fresh')
            except Exception:result['isolatedStopNeedsInspection']=True
        save(out/('result-'+str(time.time_ns())+'.json'),result);save(out/'source-readonly-commands.json',m.RECORDS)
        if c.RECORDS:save(out/'isolated-commands.json',c.RECORDS)
    save(out/'DEPLOYED.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':
    os.umask(0o077);parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','preflight','execute']);parser.add_argument('run',nargs='?');parser.add_argument('--include-ui-head',action='store_true');args=parser.parse_args()
    if args.action=='build':build(args.include_ui_head)
    elif args.action=='preflight':preflight(args.run)
    else:execute(args.run)
