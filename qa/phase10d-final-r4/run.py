#!/usr/bin/env python3
"""Independent final QA: create-only database, isolated builds, explicit evidence journal."""
import concurrent.futures, datetime, hashlib, json, os, secrets, shutil, socket, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).resolve().parent
OUT=TOOLS/'evidence'
PRIVATE=ROOT/'.local/qa-final-r4'
SOURCE=PRIVATE/'source'
JAVA=ROOT/'.local/jdk21/jdk-21.0.12.1+1/Contents/Home/bin/java'
NODE='/opt/homebrew/opt/node@22/bin'
DOCKER='/Applications/Docker.app/Contents/Resources/bin/docker'
MYSQL='/usr/local/mysql/bin/mysql'
NAME='northstar-qa-final-r4-20261102'
SCHEMA='northstar_phase01_test'
JAR=ROOT/'output/review/northstar-phase10d2-p1-candidate.jar'
JAR_SHA='771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6'
API_PORT=8191
WEB_PORT=3198
API=f'http://127.0.0.1:{API_PORT}/api/v1'
WEB=f'http://127.0.0.1:{WEB_PORT}'
IMAGE='sha256:c36050afdca850f23cef85703f84c7531a5ae155a11b5ee1c60acb09937c4084'
OUT.mkdir(parents=True,exist_ok=True)
PRIVATE.mkdir(parents=True,exist_ok=True)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def credentials(): return json.loads((PRIVATE/'credentials.json').read_text()) if (PRIVATE/'credentials.json').exists() else {}
def journal(row):
    row.update(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidateManifest=sha(OUT/'qa-final-candidate-manifest.sha256') if (OUT/'qa-final-candidate-manifest.sha256').exists() else None,jarSha256=JAR_SHA)
    with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
def run(label,args,env=None,stdin=None,cwd=ROOT,check=True,timeout=600):
    start=time.time_ns()
    p=subprocess.run([str(a) for a in args],cwd=cwd,env=env,input=stdin,capture_output=True,text=True,timeout=timeout)
    text=p.stdout+'\nSTDERR\n'+p.stderr
    for value in credentials().values():text=text.replace(value,'<REDACTED>')
    if env:
        for k,v in env.items():
            if 'PASSWORD' in k and v:text=text.replace(v,'<REDACTED>')
    path=OUT/(label+'.log');path.write_text(text)
    journal(dict(label=label,argv=[str(a) for a in args],cwd=str(cwd),startedNs=start,endedNs=time.time_ns(),exitCode=p.returncode,log=path.name,logSha256=sha(path)))
    print(label,'exit='+str(p.returncode),flush=True)
    if check and p.returncode:raise RuntimeError(label+' failed; see retained log')
    return p
def env():
    e={k:v for k,v in os.environ.items() if not k.startswith(('SPRING_','NORTHSTAR_')) and k not in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')}
    e.update(JAVA_HOME=str(JAVA.parent.parent),PATH=NODE+':'+str(JAVA.parent)+':'+os.environ['PATH'],API_PORT=str(API_PORT),WEB_PORT=str(WEB_PORT))
    if (PRIVATE/'identity.json').exists():
        d=identity();c=credentials()
        e.update(DB_NAME=SCHEMA,MYSQL_PORT=str(d['port']),DB_PASSWORD=c['app'],DB_MIGRATION_PASSWORD=c['migrator'],NORTHSTAR_DB_TEST='1',NORTHSTAR_FINAL_QA='1',NORTHSTAR_EXPECTED_DB_UUID=d['uuid'],NORTHSTAR_CONTENT_ROOT=str(PRIVATE/'content'),NORTHSTAR_RECORDING_ROOT=str(PRIVATE/'recordings'),NORTHSTAR_TEST_AUDIO=str(ROOT/'.local/phase10b2/audio/original-test-tone.mp3'))
    return e
def freeze():
    old=json.loads((ROOT/'qa/phase10d2-p1/evidence/candidate-inputs.json').read_text())
    drift=[f for f,h in old.items() if sha(ROOT/f)!=h]
    assert not drift,('P1 candidate input drift',drift)
    files=set(old)
    for folder in ['content','infra','qa/phase10d','qa/phase10d2','qa/phase10d2-p1','qa/phase10d-final-r4']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in ('.py','.java','.ts','.js','.mjs','.json','.sql','.sh','.yaml','.yml') and 'evidence' not in p.relative_to(ROOT/folder).parts and '__pycache__' not in p.parts:files.add(str(p.relative_to(ROOT)))
    for p in (ROOT/'apps/web/e2e').glob('*'):
        if p.is_file():files.add(str(p.relative_to(ROOT)))
    for f in ('apps/web/playwright.config.ts','AGENTS.md'):
        if (ROOT/f).exists():files.add(f)
    files.add('.local/phase10b2/audio/original-test-tone.mp3')
    for p in (ROOT/'.local/d02-p1/database/p1/content/demo-01').rglob('*'):
        if p.is_file():files.add(str(p.relative_to(ROOT)))
    manifest=''.join(sha(ROOT/f)+'  '+f+'\n' for f in sorted(files))
    (OUT/'qa-final-candidate-manifest.sha256').write_text(manifest)
    SOURCE.mkdir(exist_ok=True)
    for f in sorted(files):
        target=SOURCE/f;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/f,target)
    assert sha(JAR)==JAR_SHA
    for f in ['node_modules','apps/web/node_modules']:
        if (ROOT/f).exists() and not (SOURCE/f).exists():(SOURCE/f).symlink_to(ROOT/f,target_is_directory=True)
    helper=SOURCE/'apps/api/src/test/java/local/northstar/knowledge/FinalQaFixture.java'
    shutil.copy2(TOOLS/'FinalQaFixture.java',helper)
    save('candidate-identity.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),manifestSha256=sha(OUT/'qa-final-candidate-manifest.sha256'),inputCount=len(files),jar=str(JAR.relative_to(ROOT)),jarSha256=JAR_SHA,qaFixtureCopy={'from':'qa/phase10d-final-r4/FinalQaFixture.java','to':str(helper.relative_to(SOURCE)),'sha256':sha(helper)},sourceCopy=str(SOURCE)))
    run('git-status',['git','status','--short','--untracked-files=all'])
    run('java-version',[JAVA,'-version']);run('node-version',[NODE+'/node','--version']);run('npm-version',[NODE+'/npm','--version'],env=env())
    save('migration-inputs.json',{p.name:sha(p) for p in sorted((ROOT/'apps/api/src/main/resources/db/migration').glob('*.sql'))})
    print('FROZEN',len(files),'inputs',flush=True)
def identity(): return json.loads((PRIVATE/'identity.json').read_text())
def sql(query,label=None,check=True,schema=SCHEMA):
    d=identity();assert d['name']==NAME and d['port']!=3308 and d['schema']==SCHEMA
    e=dict(os.environ,MYSQL_PWD=credentials()['root'])
    args=[MYSQL,'--protocol=TCP','-h127.0.0.1','-P'+str(d['port']),'-uroot','-N','--batch','--raw']
    p=run(label or 'sql-'+str(time.time_ns()),args,env=e,stdin='SELECT @@server_uuid;'+('USE '+schema+';' if schema else '')+query,check=False)
    first,_,body=p.stdout.partition('\n');assert first==d['uuid'],'QA UUID mismatch'
    if check:assert p.returncode==0,p.stderr
    return body.rstrip('\n') if check else p
def create():
    assert not (PRIVATE/'identity.json').exists(),'create only'
    r=run('container-must-not-exist',[DOCKER,'inspect',NAME],check=False);assert r.returncode!=0
    port=3380
    while port<=3399:
        try:
            with socket.socket() as s:s.bind(('127.0.0.1',port))
            break
        except OSError:port+=1
    assert port<=3399
    c={k:secrets.token_hex(32) for k in ('root','app','migrator')}
    path=PRIVATE/'credentials.json';path.write_text(json.dumps(c));path.chmod(0o600)
    e=dict(os.environ,MYSQL_ROOT_PASSWORD=c['root'])
    volume=NAME+'-data'
    run('create-volume',[DOCKER,'volume','create','--label','northstar.qa=final-r4',volume])
    cid=run('create-container',[DOCKER,'run','--pull=never','-d','--name',NAME,'--label','northstar.qa=final-r4','--restart=no','--memory=1g','--cpus=2','-p',f'127.0.0.1:{port}:3306','-e','MYSQL_ROOT_PASSWORD','-v',volume+':/var/lib/mysql',IMAGE,'--default-time-zone=+00:00'],e).stdout.strip()
    for _ in range(90):
        p=subprocess.run([MYSQL,'--protocol=TCP','-h127.0.0.1','-P'+str(port),'-uroot','-N','-e','SELECT VERSION(),@@server_uuid'],env=dict(os.environ,MYSQL_PWD=c['root']),capture_output=True,text=True)
        if p.returncode==0:break
        time.sleep(.5)
    assert p.returncode==0,'MySQL TCP readiness failed'
    version,dbuuid=p.stdout.strip().split('\t')
    d=dict(name=NAME,containerId=cid,port=port,schema=SCHEMA,version=version,uuid=dbuuid,volume=volume,appAccount='northstar_app',migratorAccount='northstar_migrator',content=str(PRIVATE/'content'),recordings=str(PRIVATE/'recordings'))
    (PRIVATE/'identity.json').write_text(json.dumps(d));save('database-identity.json',d)
    run('container-mounts',[DOCKER,'inspect','--format','{{json .Mounts}}',cid])
    sql("CREATE DATABASE "+SCHEMA+" CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; CREATE TABLE "+SCHEMA+".project_identity(project_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,created_at DATETIME(3) NOT NULL DEFAULT (UTC_TIMESTAMP(3))); INSERT INTO "+SCHEMA+".project_identity(project_key) VALUES ('northstar-english-local-v1'); CREATE USER 'northstar_app'@'%' IDENTIFIED BY '"+c['app']+"'; CREATE USER 'northstar_migrator'@'%' IDENTIFIED BY '"+c['migrator']+"'; GRANT SELECT,INSERT,UPDATE,DELETE ON "+SCHEMA+".* TO 'northstar_app'@'%'; GRANT ALL ON "+SCHEMA+".* TO 'northstar_migrator'@'%'; SET GLOBAL log_bin_trust_function_creators=1;",label='bootstrap',schema=None)
    (PRIVATE/'content').mkdir(exist_ok=True);(PRIVATE/'recordings').mkdir(exist_ok=True)
    shutil.copytree(ROOT/'.local/d02-p1/database/p1/content/demo-01',PRIVATE/'content/demo-01')
    run('initialize',[JAVA,'-jar',JAR,'--spring.main.web-application-type=none','--northstar.initialize-content=true'],env=env())
    sql('SELECT version,description,checksum,success FROM flyway_schema_history ORDER BY installed_rank',label='flyway-history')
def nodes():
    for script in ('test','typecheck','lint','build'):run('node-'+script,[NODE+'/npm','run',script],env=env(),cwd=SOURCE)
    save('web-identity.json',dict(buildId=(SOURCE/'apps/web/.next/BUILD_ID').read_text().strip(),manifestSha256=sha(OUT/'qa-final-candidate-manifest.sha256'),apiPort=API_PORT,node=subprocess.check_output([NODE+'/node','--version'],text=True).strip()))
def regressions():
    names='ConceptReviewIntegrationTest,KnowledgeSourcesIntegrationTest,KnowledgeConceptsTest,QuizScaleIntegrationTest,QuizReportR1IntegrationTest'
    test_env=env();test_env['WEB_PORT']='3196'
    run('java-regression-correct-origin',['bash',SOURCE/'apps/api/mvnw','-f',SOURCE/'apps/api/pom.xml','test','-Dtest='+names],env=test_env)
    run('java-package',['bash',SOURCE/'apps/api/mvnw','-f',SOURCE/'apps/api/pom.xml','package','-DskipTests'],env=env())
    import zipfile
    built=SOURCE/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    with zipfile.ZipFile(JAR) as a,zipfile.ZipFile(built) as b:
        keys={n for n in a.namelist() if n.startswith('BOOT-INF/classes/') and not n.endswith('/')}
        diff=[n for n in sorted(keys) if n not in b.namelist() or a.read(n)!=b.read(n)]
        save('jar-rebuild-comparison.json',dict(runtimeJarSha256=sha(JAR),rebuiltJarSha256=sha(built),comparedClassAndResourceFiles=len(keys),differentEntries=diff))
        assert not diff,'Rebuilt bytecode/resources differ from frozen runtime JAR'
def seed():
    run('seed-original-fixture',['bash',SOURCE/'apps/api/mvnw','-f',SOURCE/'apps/api/pom.xml','test','-Dtest=FinalQaFixture'],env=env())
def request(path,body=None):
    req=urllib.request.Request(API+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':WEB,'X-Northstar-Request':'local-workspace'})
    start=time.time_ns()
    try:
        with urllib.request.urlopen(req,timeout=60) as r:code,value=r.status,json.load(r)
    except urllib.error.HTTPError as error:code,value=error.code,json.load(error)
    with (OUT/'http.jsonl').open('a') as f:f.write(json.dumps(dict(path=path,request=body,status=code,response=value,startNs=start,endNs=time.time_ns()),ensure_ascii=False)+'\n')
    return code,value
def start_api():
    with socket.socket() as s:s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',API_PORT))
    assert sha(JAR)==JAR_SHA
    log=(PRIVATE/('api-'+str(time.time_ns())+'.log')).open('wb')
    p=subprocess.Popen([str(JAVA),'-jar',str(JAR)],env=env(),cwd=SOURCE,stdout=log,stderr=subprocess.STDOUT)
    for _ in range(100):
        assert p.poll() is None,'API exited; private log retained'
        try:
            if request('/health')[1].get('migrationVersion')=='012.11':return p
        except OSError:pass
        time.sleep(.4)
    stop(p);raise RuntimeError('API readiness timeout')
def stop(p):
    p.terminate()
    try:p.wait(timeout=20)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    journal(dict(label='stop-owned-child',pid=p.pid,exitCode=p.returncode))
if __name__=='__main__':
    action=sys.argv[1]
    {'freeze':freeze,'create':create,'nodes':nodes,'regressions':regressions,'seed':seed}[action]()
