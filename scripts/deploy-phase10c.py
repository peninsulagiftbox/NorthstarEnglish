#!/usr/bin/env python3
"""Authorized local 009.15 -> 011.09 release: fresh backup, isolated rehearsal, then source.
Never restore over the personal database; keep backups and failed rehearsal resources.
"""
import copy, datetime, hashlib, json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path
import local
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
b=load('release_helpers_c',ROOT/'scripts/deploy-phase10b2.py')
b.STATE=ROOT/'.local/phase10c-release';b.OUT=ROOT/'docs/handoff/evidence/phase10c-deployment'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sources(root):
    paths=[p for prefix in ('apps/api/src','apps/web/src','apps/web/tests') for p in (root/prefix).rglob('*') if p.is_file()]
    paths += [root/p for p in ('package.json','package-lock.json','apps/api/pom.xml','apps/web/package.json','apps/web/next.config.ts')]
    return {str(p.relative_to(root)):sha(p) for p in sorted(paths)}
def health(port,path='/health'):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1'+path,timeout=20) as r:return json.load(r)
def build():
    run=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
    private=b.STATE/run;out=b.OUT/run;workspace=private/'source';workspace.mkdir(parents=True);out.mkdir(parents=True)
    for prefix in ('apps/api','apps/web','content'):
        shutil.copytree(ROOT/prefix,workspace/prefix,ignore=shutil.ignore_patterns('target','.next','node_modules','*.tsbuildinfo'))
    for name in ('package.json','package-lock.json'):shutil.copyfile(ROOT/name,workspace/name)
    (workspace/'node_modules').symlink_to(ROOT/'node_modules',target_is_directory=True)
    env=b.safe_env()
    for name,cmd in [('java-package',['apps/api/mvnw','-f','apps/api/pom.xml','package']),('web-tests',['npm','test']),('web-build',['npm','run','build']),('typecheck',['npm','run','typecheck']),('lint',['npm','run','lint'])]:
        b.command(out,name,cmd,env,workspace)
    routes=json.loads((workspace/'apps/web/.next/routes-manifest.json').read_text())['rewrites']
    routes=routes if isinstance(routes,list) else sum(routes.values(),[])
    assert any(r.get('destination')=='http://127.0.0.1:8085/api/v1/:path*' for r in routes)
    jar=workspace/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    b.save(out/'release.json',dict(run=run,sourceFiles=sources(ROOT),jarSha256=sha(jar),workspace=str(workspace.relative_to(ROOT))))
    (b.STATE/'LATEST').write_text(run);print('BUILD READY '+run,flush=True)
def execute(run):
    assert run.isalnum()
    private=b.STATE/run;out=b.OUT/run;release=b.read(out/'release.json');workspace=ROOT/release['workspace'];jar=workspace/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    assert sources(ROOT)==sources(workspace)==release['sourceFiles'] and sha(jar)==release['jarSha256']
    assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()==''
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    assert subprocess.check_output(['git','rev-parse','origin/main'],text=True).strip()==head,'Must push fixed candidate first'
    m=load('source_c',b.OLD/'maintenance_backup.py');c=load('isolation_c',b.OLD/'isolated_rehearsal.py');media=load('media_c',b.OLD/'runtime_media_preflight.py')
    cmp=load('comparison_c',ROOT/'scripts/phase10c1_isolated.py')
    env=b.safe_env();b.identity(m,c,env)
    assert health(8085)['migrationVersion']=='009.15' and health(3100)['migrationVersion']=='009.15'
    processes=b.services();paths=dict(content=ROOT/'content',recordings=Path.home()/'Library/Application Support/NorthstarEnglish/recordings/northstar_english')
    assert shutil.disk_usage(ROOT).free>4*1024**3
    b.save(private/'previous-services.json',processes);shutil.copyfile(ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar',private/'previous-api.jar')
    result=dict(gitSha=head,status='BLOCKED',sourceMigrationAttempted=False);created=False
    def source_write(sql):
        b.identity(m,c,env)
        return b.command(out,'source-privileges',[m.DOCKER,'exec','-i',m.CONTAINER,'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot northstar_english'],env,stdin=sql.encode(),private=True)
    def grants(role=None):
        query="SET GLOBAL log_bin_trust_function_creators=1; GRANT TRIGGER ON northstar_english.* TO 'northstar_migrator'@'%'; GRANT SELECT ON northstar_english.* TO 'northstar_app'@'%';"
        if role:c.sql(role,query)
        else:source_write(query)
    def app_grants(role=None):
        query="GRANT SELECT ON northstar_english.* TO 'northstar_app'@'%'; GRANT INSERT ON northstar_english.quiz_run_item TO 'northstar_app'@'%';"
        if role:c.sql(role,query)
        else:source_write(query)
    def migrate(e,name):
        b.command(out,name,[str(c.JAVA),'-jar',str(jar),'--spring.main.web-application-type=none','--northstar.initialize-content=false','--northstar.content-root='+e.get('NORTHSTAR_CONTENT_ROOT',str(paths['content'])),'--northstar.recording-root='+e.get('NORTHSTAR_RECORDING_ROOT',str(paths['recordings'].parent))],e,workspace/'apps/api',private=True)
    def start_personal():
        local.start_process('api',[str(c.JAVA),'-jar',str(ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'),'--northstar.content-root='+str(paths['content']),'--northstar.recording-root='+str(paths['recordings'].parent)],ROOT/'apps/api',env,str(ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'))
        local.wait_health('http://127.0.0.1:8085/api/v1/health')
        cli=ROOT/'node_modules/next/dist/bin/next';local.start_process('web',['node',str(cli),'start','--hostname','127.0.0.1','--port','3100'],ROOT/'apps/web',env,str(cli));local.wait_health('http://127.0.0.1:3100/api/v1/health')
    try:
        for name in ('web','api'):b.stop_record(processes[name]['record'])
        assert all(local.available(p) for p in (3100,8085))
        before=m.snapshot();backup=private/'backup';backup.mkdir();b.save(backup/'source-snapshot.json',before)
        clean=copy.deepcopy(before)
        for item in clean.values():
            ix=[i for i,col in enumerate(item['columns']) if col!='target_uniqueness_key'];item['columns']=[item['columns'][i] for i in ix];item['rows']=[[row[i] for i in ix] for row in item['rows']]
        (backup/'restore.sql').write_text(m.restore_sql(clean))
        dump=b.command(out,'fresh-sql-backup',[m.DOCKER,'exec',m.CONTAINER,'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF --hex-blob northstar_english'],env,private=True)
        (backup/'source.sql').write_bytes(dump.stdout)
        inventories={}
        for name,path in paths.items():
            inventories[name]=media.inventory(path);shutil.copytree(path,backup/name);assert media.inventory(backup/name)==inventories[name]
        b.save(backup/'media-manifest.json',inventories)
        assert m.snapshot()==before
        c.PRIVATE=private/'rehearsal';c.PRIVATE.mkdir();c.OUT=out/'rehearsal';c.OUT.mkdir();c.NAMESPACE='northstar-c-release-'+run.lower();c.BACKUP=backup;c.PATCHED_JAR=jar
        port=3380
        while not c.available(port):port+=1
        assert port<3399;c.ROLES=['reserved'+str(i) for i in range(port-3313)]+['fresh']
        c.create('fresh');created=True;c.prepare_files('fresh');c.restore('fresh')
        cmp.compare_old(before,c.snapshot('fresh','restored'))
        state=c.verify('fresh');cred=b.read(c.PRIVATE/'fresh/credentials.json')
        iso=dict(env,MYSQL_PORT=str(state['port']),DB_PASSWORD=cred['app'],DB_MIGRATION_PASSWORD=cred['migrator'],NORTHSTAR_CONTENT_ROOT=str(c.PRIVATE/'fresh/content'),NORTHSTAR_RECORDING_ROOT=str(c.PRIVATE/'fresh/recordings'))
        grants('fresh');migrate(iso,'rehearsal-migrate')
        app_grants('fresh');after_iso=c.snapshot('fresh','upgraded');cmp.compare_old(before,after_iso)
        assert c.sql('fresh','SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1',readonly=True).stdout.decode().strip()=='011.09'
        handle=c.start_api('fresh',True)
        try:
            assert health(handle[2])['migrationVersion']=='011.09';health(handle[2],'/quiz?lessonId=demo-01&versionId=demo-01-v2')
        finally:c.end_api('fresh',handle)
        assert c.snapshot('fresh','after-restart')==after_iso
        b.save(out/'rehearsal-PASS.json',dict(status='PASS',oldCellsExact=True,candidateRestartExact=True))
        assert m.snapshot()==before and all(media.inventory(p)==inventories[n] for n,p in paths.items())
        result['sourceMigrationAttempted']=True;grants();migrate(env,'personal-migrate');app_grants()
        after=m.snapshot();cmp.compare_old(before,after);b.save(private/'source-after.json',after)
        assert all(media.inventory(p)==inventories[n] for n,p in paths.items())
        (ROOT/'apps/web/.next').rename(private/'previous-web-build');shutil.copytree(workspace/'apps/web/.next',ROOT/'apps/web/.next');shutil.copyfile(jar,ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar')
        start_personal()
        for port in (8085,3100):
            assert health(port)['migrationVersion']=='011.09'
            for path in ('/books','/lessons/demo-01','/quiz?lessonId=demo-01&versionId=demo-01-v2','/reports'):
                health(port,path)
        assert m.snapshot()==after
        for name in ('web','api'):b.stop_record(b.read(ROOT/'.local'/ (name+'.json')))
        start_personal();assert health(8085)['migrationVersion']=='011.09' and health(3100)['migrationVersion']=='011.09';assert m.snapshot()==after
        result.update(status='PASS',version='011.09',oldCellsExact=True,twoRestartsExact=True,mediaExact=True,jarSha256=sha(jar),webBuildId=(ROOT/'apps/web/.next/BUILD_ID').read_text().strip(),backup=str(backup.relative_to(ROOT)))
    except Exception:
        if not result['sourceMigrationAttempted'] and 'before' in locals() and m.snapshot()==before:
            start_personal();result['oldServicesRestored']=True
        raise
    finally:
        if created:c.stop('fresh')
        b.save(out/'result.json',result)
    print(json.dumps(result),flush=True)
if __name__=='__main__':
    os.umask(0o077)
    if sys.argv[1:]==['build']:build()
    elif len(sys.argv)==3 and sys.argv[1]=='execute':execute(sys.argv[2])
    else:raise SystemExit('build | execute RUN')
