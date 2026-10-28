#!/usr/bin/env python3
"""10B-1 C-F only. New Docker namespace; source port, UUID, container and media denied."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
RUN='20261027t154428'
NAMESPACE='northstar-english-phase10b1-'+RUN
PRIVATE=ROOT/'.local/phase10b1-isolated'/RUN
OUT=BASE/('isolated-'+RUN)
BACKUP=ROOT/'.local/phase10b1-backups/20261027T154428'
DOCKER='/Applications/Docker.app/Contents/Resources/bin/docker'
SOURCE_CONTAINER='bbf8c3f55c023dd7e16377417e31b54c742cb3ecf109fd57f22c152babc58fd0'
SOURCE_UUID='104d5d9d-cd3f-11f1-8da4-920f115cf5cb'
IMAGE='mysql:8.4.9@sha256:c36050afdca850f23cef85703f84c7531a5ae155a11b5ee1c60acb09937c4084'
JAVA=ROOT/'.local/jdk21/jdk-21.0.12.1+1/Contents/Home/bin/java'
CLASSES=ROOT/'.local/phase10b1-tools/classes'
LIB=ROOT/'.local/phase10b1-tools/lib'
OLD_JAR=ROOT/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
PATCHED_JAR=ROOT/'.local/phase10b1-tools/northstar-isolated-candidate.jar'
ROLES=['upgrade','empty','fault-ddl-01','fault-ddl-02','fault-ddl-04','fault-history','fault-dml',
       'recover-ddl-01','recover-ddl-02','recover-ddl-04','recover-history','recover-dml']
RECORDS=[]
VERIFIED={}


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,value,exclusive=True):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x' if exclusive else 'w') as f: f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    path.chmod(0o600)


def call(name,argv,stdin=None,env=None,expected=(0,),timeout=60,private=False):
    start=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    p=subprocess.run(argv,input=stdin,capture_output=True,env=env,timeout=timeout)
    log=PRIVATE/'logs'/(str(len(RECORDS))+'-'+name+'.txt')
    log.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    log.write_bytes(p.stdout+b'\nSTDERR\n'+p.stderr); log.chmod(0o600)
    record=dict(name=name,argv=[str(x) for x in argv],started=start,returncode=p.returncode,
                rawLog=str(log.relative_to(ROOT)),rawLogSha256=digest(log),privateOutput=private)
    if stdin is not None:
        record['stdinSha256']=hashlib.sha256(stdin).hexdigest()
        if not private: record['stdinSql']=stdin.decode()
    if not private:
        record['stdout']=p.stdout.decode(errors='replace'); record['stderr']=p.stderr.decode(errors='replace')
    RECORDS.append(record)
    with (OUT/'commands.jsonl').open('a') as journal: journal.write(json.dumps(record,ensure_ascii=False)+'\n')
    if p.returncode not in expected: raise RuntimeError(name+' exited '+str(p.returncode)+'; see controlled raw log')
    return p


def available(port):
    try:
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.bind(('127.0.0.1',port))
        return True
    except OSError: return False


def state(role):
    assert role in ROLES
    data=json.loads((PRIVATE/role/'state.json').read_text())
    assert data['namespace']==NAMESPACE and data['containerId']!=SOURCE_CONTAINER
    assert 3313<=data['port']<=3399
    return data


def verify(role):
    d=state(role)
    p=call(role+'-verify',[DOCKER,'inspect','--format',
        '{"id":{{json .Id}},"labels":{{json .Config.Labels}},"ports":{{json .HostConfig.PortBindings}},"mounts":{{json .Mounts}}}',d['containerId']])
    item=json.loads(p.stdout)
    assert item['id']==d['containerId'] and item['id']!=SOURCE_CONTAINER
    assert item['labels']['local.northstar.rehearsal']==NAMESPACE and item['labels']['local.northstar.role']==role
    assert item['ports']['3306/tcp']==[{'HostIp':'127.0.0.1','HostPort':str(d['port'])}]
    assert any(m.get('Name')==d['volume'] and m['Destination']=='/var/lib/mysql' for m in item['mounts'])
    return d


def sql(role,query,expected=(0,),private=False,readonly=False):
    d=state(role)
    refresh=not readonly or role not in VERIFIED or time.monotonic()-VERIFIED[role]>5
    if refresh: d=verify(role)
    shell='MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot --database=northstar_english --batch --raw --skip-column-names'
    if readonly: query="SET SESSION time_zone='+00:00';\nSTART TRANSACTION READ ONLY;\n"+query+';\nROLLBACK;'
    # Always verify target UUID on the same pinned container before any target SQL action.
    if refresh:
        check=call(role+'-uuid',[DOCKER,'exec',d['containerId'],'sh','-c',
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'])
        assert check.stdout.decode().strip()==d['uuid'] and d['uuid']!=SOURCE_UUID
        VERIFIED[role]=time.monotonic()
    return call(role+'-sql',[DOCKER,'exec','-i',d['containerId'],'sh','-c',shell],stdin=query.encode(),expected=expected,private=private)


def create(role):
    folder=PRIVATE/role; folder.mkdir(mode=0o700,exist_ok=False)
    name=NAMESPACE+'-'+role; volume=name.replace('-','_')+'_data'
    for argv in [[DOCKER,'inspect',name],[DOCKER,'volume','inspect',volume]]:
        p=call(role+'-must-not-exist',argv,expected=(0,1),private=True)
        assert p.returncode!=0,'Refuse to adopt existing resource'
    port=3313+ROLES.index(role)
    assert available(port),'Target port occupied; will not stop owner'
    credentials={k:secrets.token_hex(32) for k in ['root','app','migrator','fault']}
    save(folder/'credentials.json',credentials)
    call(role+'-volume',[DOCKER,'volume','create','--label','local.northstar.rehearsal='+NAMESPACE,'--label','local.northstar.role='+role,volume])
    env=dict(os.environ,MYSQL_ROOT_PASSWORD=credentials['root'],MYSQL_DATABASE='northstar_english')
    p=call(role+'-create',[DOCKER,'run','--pull=never','-d','--name',name,'--restart=no','--memory=1g','--cpus=1',
       '--label','local.northstar.rehearsal='+NAMESPACE,'--label','local.northstar.role='+role,
       '-p','127.0.0.1:'+str(port)+':3306','--mount','type=volume,src='+volume+',dst=/var/lib/mysql',
       '-e','MYSQL_ROOT_PASSWORD','-e','MYSQL_DATABASE',IMAGE,
       '--character-set-server=utf8mb4','--collation-server=utf8mb4_0900_ai_ci','--default-time-zone=+00:00'],env=env)
    cid=p.stdout.decode().strip(); assert re.fullmatch('[0-9a-f]{64}',cid) and cid!=SOURCE_CONTAINER
    for _ in range(80):
        p=call(role+'-startup-probe',[DOCKER,'exec',cid,'sh','-c',
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'],expected=(0,1),private=True)
        if p.returncode==0:
            server_uuid=p.stdout.decode().strip()
            if server_uuid and server_uuid!=SOURCE_UUID: break
        time.sleep(1)
    else: raise RuntimeError('Isolated MySQL startup timed out')
    for previous in PRIVATE.glob('*/state.json'):
        assert json.loads(previous.read_text())['uuid']!=server_uuid,'Target UUID reused'
    save(folder/'state.json',dict(namespace=NAMESPACE,role=role,container=name,containerId=cid,volume=volume,port=port,uuid=server_uuid))
    verify(role)
    assert int(sql(role,'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()',readonly=True).stdout)==0
    bootstrap="CREATE USER 'northstar_app'@'%' IDENTIFIED BY '"+credentials['app']+"';\nCREATE USER 'northstar_migrator'@'%' IDENTIFIED BY '"+credentials['migrator']+"';\nCREATE USER 'northstar_fault_migrator'@'%' IDENTIFIED BY '"+credentials['fault']+"';\n"
    bootstrap+="GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_english.* TO 'northstar_migrator'@'%';\nGRANT SELECT,UPDATE,CREATE,ALTER,INDEX,REFERENCES ON northstar_english.* TO 'northstar_fault_migrator'@'%';\n"
    sql(role,bootstrap,private=True)
    save(OUT/(role+'-identity.json'),{k:v for k,v in state(role).items()})


def stop(role):
    d=verify(role)
    call(role+'-stop-owned',[DOCKER,'stop','--time','20',d['containerId']],timeout=30)


def prepare_files(role):
    folder=PRIVATE/role
    shutil.copytree(BACKUP/'content',folder/'content')
    (folder/'recordings').mkdir(mode=0o700)
    if role!='empty': shutil.copytree(BACKUP/'recordings',folder/'recordings/northstar_english')


def restore(role):
    safe=BACKUP/'restore.sql'
    text=safe.read_text()
    assert not re.search(r'FOREIGN_KEY_CHECKS|DISABLE KEYS|DROP\s+(DATABASE|TABLE)|REPAIR|CLEAN',text,re.I)
    assert int(sql(role,'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE()',readonly=True).stdout)==0
    sql(role,text,private=True)
    grant_app(role)


def grant_app(role):
    grants=json.loads((BASE/'recovery-20261027/a1/grants.json').read_text())['app']
    target='\n'.join(line+';' for line in grants.splitlines() if ' ON `northstar_english`.' in line)
    assert target
    sql(role,target)


def snapshot(role,tag):
    result={}
    tables=sql(role,'SHOW TABLES',readonly=True).stdout.decode().splitlines()
    for table in tables:
        assert re.fullmatch('[a-z_]+',table)
        names=sql(role,"SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='"+table+"' ORDER BY ORDINAL_POSITION",readonly=True).stdout.decode().splitlines()
        pk=sql(role,"SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='"+table+"' AND INDEX_NAME='PRIMARY' ORDER BY SEQ_IN_INDEX",readonly=True).stdout.decode().splitlines()
        assert pk and all(re.fullmatch('[a-z][a-z0-9_]*',n) for n in names+pk)
        expression=','.join('HEX(CAST(`'+n+'` AS BINARY))' for n in names)
        rows=[json.loads(line) for line in sql(role,'SELECT JSON_ARRAY('+expression+') FROM `'+table+'` ORDER BY '+','.join('`'+n+'`' for n in pk),readonly=True,private=True).stdout.decode().splitlines()]
        create=sql(role,'SHOW CREATE TABLE `'+table+'`',readonly=True).stdout.decode().split('\t',1)[1].strip()
        result[table]=dict(columns=names,primaryKey=pk,rows=rows,createSql=create)
    save(PRIVATE/role/(tag+'.json'),result)
    save(OUT/(role+'-'+tag+'-summary.json'),dict(tables=len(result),counts={t:len(v['rows']) for t,v in result.items()},
          privateSnapshot=str((PRIVATE/role/(tag+'.json')).relative_to(ROOT)),sha256=digest(PRIVATE/role/(tag+'.json'))))
    return result


def compare(expected,actual,allow_new=False,paragraph_column_required=True):
    differences=[]
    for table,data in expected.items():
        if table not in actual: differences.append(table+':missing'); continue
        other=actual[table]; names=data['columns']
        if not all(n in other['columns'] for n in names): differences.append(table+':old columns missing'); continue
        rows=[[row[other['columns'].index(n)] for n in names] for row in other['rows']]
        if table=='flyway_schema_history' and allow_new:
            old_pk=set(tuple(row[names.index(n)] for n in data['primaryKey']) for row in data['rows'])
            rows=[row for row in rows if tuple(row[names.index(n)] for n in data['primaryKey']) in old_pk]
        if rows!=data['rows']: differences.append(table+':old cells differ')
        if not allow_new and other['createSql']!=data['createSql']: differences.append(table+':schema differs')
        if allow_new and table!='sentence' and other['createSql']!=data['createSql']:
            differences.append(table+':unapproved schema differs')
        wanted={'paragraph_id'} if table=='sentence' and paragraph_column_required else set()
        if allow_new and set(other['columns'])-set(names) != wanted:
            differences.append(table+':unapproved new columns')
        if allow_new and table=='sentence':
            def normalize(sql,filtered):
                lines=sql.splitlines()
                if filtered: lines=[line for line in lines if not re.match(r'\s*`paragraph_id`\s',line) and '`ix_sentence_paragraph_version`' not in line and '`fk_sentence_paragraph_version`' not in line]
                return sorted(line.strip().rstrip(',') for line in lines)
            if normalize(data['createSql'],False)!=normalize(other['createSql'],True): differences.append(table+':old constraints/indexes changed')
    extra=set(actual)-set(expected)
    if extra!=({'paragraph'} if allow_new else set()): differences.append('unapproved extra tables')
    assert not differences,'Unexplained differences: '+','.join(differences)


def media_check(role):
    spec=importlib.util.spec_from_file_location('runtime',BASE/'runtime_media_preflight.py')
    runtime=importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
    expected=json.loads((BACKUP/'media-manifest.json').read_text())
    assert runtime.inventory(PRIVATE/role/'content')==expected['content']
    if role!='empty': assert runtime.inventory(PRIVATE/role/'recordings/northstar_english')==expected['recordings']


def harness(role,target=None,initialize=False,fault_account=False,expected=(0,)):
    d=verify(role); creds=json.loads((PRIVATE/role/'credentials.json').read_text())
    env={k:v for k,v in os.environ.items() if not k.startswith(('SPRING_','NORTHSTAR_')) and k not in ['JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS']}
    env.update(TARGET_MYSQL_PORT=str(d['port']),EXPECTED_TARGET_UUID=d['uuid'],TARGET_PASSWORD=creds['fault' if fault_account else 'migrator'],
               TARGET_USER='northstar_fault_migrator' if fault_account else 'northstar_migrator')
    if target: env['MIGRATION_TARGET']=target
    if initialize: env['INITIALIZE_EMPTY_IDENTITY']='true'
    return call(role+'-flyway-'+str(target),[str(JAVA),'-cp',str(CLASSES)+os.pathsep+str(LIB/'*'),'MigrationHarness',
        str(ROOT/'apps/api/src/main/resources/db/migration'),str(BASE/'candidate')],env=env,expected=expected,private=True,timeout=90)


def start_api(role,patched=False):
    d=verify(role); creds=json.loads((PRIVATE/role/'credentials.json').read_text())
    api=8093+ROLES.index(role); web=3113+ROLES.index(role)
    assert available(api),'API port occupied'
    env={k:v for k,v in os.environ.items() if not k.startswith(('SPRING_','NORTHSTAR_')) and k not in ['JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS']}
    env.update(MYSQL_PORT=str(d['port']),DB_NAME='northstar_english',DB_PASSWORD=creds['app'],DB_MIGRATION_PASSWORD=creds['migrator'],API_PORT=str(api),WEB_PORT=str(web))
    jar=PATCHED_JAR if patched else OLD_JAR
    argv=[str(JAVA),'-jar',str(jar),'--server.address=127.0.0.1','--server.port='+str(api),
          '--spring.datasource.url=jdbc:mysql://127.0.0.1:'+str(d['port'])+'/northstar_english?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true',
          '--spring.flyway.url=jdbc:mysql://127.0.0.1:'+str(d['port'])+'/northstar_english?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true',
          '--northstar.recording-root='+str(PRIVATE/role/'recordings'),'--northstar.content-root='+str(PRIVATE/role/'content')]
    log=PRIVATE/role/('api-'+str(time.time_ns())+'.log')
    stream=log.open('xb'); log.chmod(0o600)
    process=subprocess.Popen(argv,env=env,cwd=ROOT/'apps/api',stdout=stream,stderr=subprocess.STDOUT)
    RECORDS.append(dict(name=role+'-start-api',argv=argv,pid=process.pid,log=str(log.relative_to(ROOT)),jarSha256=digest(jar)))
    save(OUT/'commands.json',RECORDS,exclusive=False)
    for _ in range(60):
        if process.poll() is not None: raise RuntimeError(role+' API exited before health; see private log')
        try:
            with urllib.request.urlopen('http://127.0.0.1:'+str(api)+'/api/v1/health',timeout=1) as response: health=json.load(response)
            if health.get('status')=='UP' and health.get('project')=='northstar-english-local-v1': return process,stream,api,web
        except (OSError,ValueError): pass
        time.sleep(.5)
    process.terminate(); process.wait(timeout=20); stream.close()
    raise RuntimeError(role+' API health timeout')


def end_api(role,handle):
    process,stream,api,web=handle
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=10)
    stream.close()
    RECORDS.append(dict(name=role+'-stop-only-owned-api',pid=process.pid,returncode=process.returncode))


def http(role,handle,path,method='GET',data=None):
    verify(role)
    _,_,api,web=handle
    assert 8093<=api<8200 and api not in [8085,8086,8087]
    request=urllib.request.Request('http://127.0.0.1:'+str(api)+'/api/v1'+path,
        data=None if data is None else json.dumps(data).encode(),method=method,
        headers={'Origin':'http://127.0.0.1:'+str(web),'X-Northstar-Request':'local-workspace','Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as response:
        body=response.read(); status=response.status; content_type=response.headers.get('Content-Type','')
    RECORDS.append(dict(name=role+'-http',method=method,path=path,httpStatus=status,responseSha256=hashlib.sha256(body).hexdigest()))
    return json.loads(body) if 'json' in content_type else body


def read_application(role,handle):
    for path in ['/books','/lessons','/study/resume','/reviews/due',
          '/writing?lessonId=demo-01&versionId=demo-01-v2','/recordings?lessonId=demo-01&versionId=demo-01-v2&sentenceId=demo-01-v2-s10',
          '/lessons/demo-01?versionId=demo-01-v1','/lessons/demo-01?versionId=demo-01-v2']:
        value=http(role,handle,path)
        if path.startswith('/lessons/demo-01'): assert len(value['sentences'])==10
    if role!='empty':
        original=json.loads((BACKUP/'source-snapshot.json').read_text())['personal_recording']
        for row in original['rows']:
            values={n:None if v is None else bytes.fromhex(v).decode() for n,v in zip(original['columns'],row)}
            if values['status']=='ready':
                audio=http(role,handle,'/recordings/'+values['id']+'/audio')
                assert len(audio)==int(values['byte_size']) and hashlib.sha256(audio).hexdigest()==values['sha256']
    media_check(role)


def continue_learning(role,handle):
    writing=http(role,handle,'/writing?lessonId=demo-01&versionId=demo-01-v2')
    before_count=len(writing['revisions'])
    parent=writing['revisions'][-1]['id'] if writing['revisions'] else None
    text='Please put the small plants beside the bench. I can bring water for the garden.'
    draft=http(role,handle,'/writing/draft','PUT',dict(lessonId='demo-01',versionId='demo-01-v2',text=text,rowVersion=writing['draft']['rowVersion']))
    event=str(uuid.uuid4())
    payload=dict(eventId=event,lessonId='demo-01',versionId='demo-01-v2',text=text,draftVersion=draft['rowVersion'],parentRevisionId=parent)
    result=http(role,handle,'/writing/revisions','POST',payload)
    retry=http(role,handle,'/writing/revisions','POST',payload)
    assert result==retry,'Continuation retry not idempotent'
    after=http(role,handle,'/writing?lessonId=demo-01&versionId=demo-01-v2')
    assert len(after['revisions'])==before_count+1
    assert after['revisions'][-1]['parentRevisionId']==parent
    save(OUT/(role+'-continuation.json'),dict(status='PASS',eventId=event,newRevisionId=result['id'],parentPreserved=True,exactlyOneNewRevision=True,idempotentReplay=True,
          note='Genuine isolated writing submission from explicit fixture text; not source learning or audio scoring'))
    return dict(eventId=event,revisionId=result['id'],taskId=writing['taskId'],parentId=parent,text=text)


def verify_continuation_delta(before,after,info):
    encode=lambda value: None if value is None else value.encode().hex().upper()
    def keyed(data):
        return {tuple(row[data['columns'].index(c)] for c in data['primaryKey']):row for row in data['rows']}
    for table,old in before.items():
        new=after[table]
        assert old['columns']==new['columns'] and old['createSql']==new['createSql'],'Continuation changed schema'
        a,b=keyed(old),keyed(new)
        if table in ['writing_revision','learning_evidence','command_receipt']:
            assert all(b.get(k)==v for k,v in a.items()),'Immutable original row changed: '+table
            assert len(b)==len(a)+1,'Unexpected continuation insert count: '+table
            row=next(v for k,v in b.items() if k not in a)
            value=dict(zip(new['columns'],row))
            assert value['event_id']==encode(info['eventId'])
            if table=='writing_revision':
                assert value['id']==encode(info['revisionId']) and value['task_id']==encode(info['taskId'])
                assert value['raw_text']==encode(info['text']) and value['parent_revision_id']==encode(info['parentId'])
            if table=='learning_evidence': assert value['writing_revision_id']==encode(info['revisionId'])
        elif table in ['writing_draft','practice_progress']:
            key=(encode(info['taskId']),) if table=='writing_draft' else (encode(info['taskId']),encode('writing'))
            assert {k:v for k,v in a.items() if k!=key}=={k:v for k,v in b.items() if k!=key},'Unrelated mutable projection changed'
            assert key in b
            value=dict(zip(new['columns'],b[key]))
            if table=='writing_draft': assert value['raw_text']==encode(info['text'])
            else: assert value['current_state']==encode('practiced')
        else: assert a==b,'Unapproved continuation delta: '+table


def candidate_assertions(role):
    assert int(sql(role,'SELECT COUNT(*) FROM paragraph',readonly=True).stdout)==2
    assert int(sql(role,'SELECT COUNT(*) FROM sentence WHERE paragraph_id IS NULL',readonly=True).stdout)==0
    assert int(sql(role,'SELECT COUNT(*) FROM sentence s LEFT JOIN paragraph p ON p.id=s.paragraph_id AND p.version_id=s.lesson_version_id WHERE p.id IS NULL',readonly=True).stdout)==0
    # Negative cases must be real DB errors in a disposable target, never source writes.
    tests=["START TRANSACTION; UPDATE sentence SET paragraph_id='a214bafb-e722-4f77-b5ed-62311f41b116' WHERE lesson_version_id='demo-01-v1' ORDER BY sequence_no LIMIT 1; ROLLBACK;",
           "START TRANSACTION; INSERT INTO paragraph(id,version_id,stable_key,sequence_no) VALUES ('negative-sequence','demo-01-v1','negative',0); ROLLBACK;",
           "START TRANSACTION; INSERT INTO paragraph(id,version_id,stable_key,sequence_no) VALUES ('negative-duplicate','demo-01-v1','original-dialogue',1); ROLLBACK;"]
    codes=[]
    for query in tests:
        p=sql(role,query,expected=(1,)); codes.append(p.stderr.decode())
    assert '1452' in codes[0] and '3819' in codes[1] and '1062' in codes[2]
    save(OUT/(role+'-constraints.json'),dict(status='PASS',crossVersionFkError=1452,checkError=3819,uniqueError=1062))


def prepare_tools():
    assert digest(OLD_JAR)=='99a3c24103d382c2330a872667c5d0b6d53494de9fd14c320c322cc14ef22619'
    LIB.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OLD_JAR) as source:
        for name in source.namelist():
            if name.startswith('BOOT-INF/lib/') and name.endswith('.jar'):
                path=LIB/Path(name).name
                if not path.exists(): path.write_bytes(source.read(name))
        with zipfile.ZipFile(PATCHED_JAR,'x') as target:
            for item in source.infolist(): target.writestr(item,source.read(item.filename))
            for file in sorted((BASE/'candidate').glob('*.sql')):
                target.writestr('BOOT-INF/classes/db/migration/'+file.name,file.read_bytes())
    with zipfile.ZipFile(OLD_JAR) as original,zipfile.ZipFile(PATCHED_JAR) as patched:
        assert all(original.read(n)==patched.read(n) for n in original.namelist())
    save(OUT/'artifacts.json',dict(oldJarSha256=digest(OLD_JAR),isolatedCandidateJarSha256=digest(PATCHED_JAR),
         allOriginalJarEntriesUnchanged=True,candidate=json.loads((BASE/'candidate/candidate-manifest.json').read_text())))


def run_upgrade():
    role='upgrade'; create(role); prepare_files(role); restore(role)
    expected=json.loads((BACKUP/'source-snapshot.json').read_text())
    before=snapshot(role,'v008-restored'); compare(expected,before); media_check(role)
    h=start_api(role)
    try: read_application(role,h)
    finally: end_api(role,h)
    compare(before,snapshot(role,'old-app-read'))
    for version in ['009.01','009.02','009.03','009.04']:
        if version=='009.03':
            assert int(sql(role,"SELECT COUNT(*) FROM sentence WHERE lesson_id='demo-01' AND lesson_version_id IN ('demo-01-v1','demo-01-v2')",readonly=True).stdout)==20
            assert int(sql(role,'SELECT COUNT(*) FROM lesson_version',readonly=True).stdout)==2
        harness(role,version)
        current=snapshot(role,'after-'+version)
        # The paragraph exists after first DDL; new column appears after second.
        compare(before,current,allow_new=True,paragraph_column_required=version!='009.01')
    candidate_assertions(role)
    final=snapshot(role,'candidate-baseline')
    for n in [1,2]:
        h=start_api(role,True)
        try: read_application(role,h)
        finally: end_api(role,h)
        compare(final,snapshot(role,'candidate-start-'+str(n)))
    save(OUT/'upgrade-result.json',dict(status='PASS',oldColumnsExact=True,mediaExact=True,repeatedStartupNonDestructive=True))
    stop(role)


def run_empty():
    role='empty'; create(role); prepare_files(role)
    harness(role,'008',True)
    grant_app(role)
    assert int(sql(role,"SELECT COUNT(*) FROM flyway_schema_history WHERE type='BASELINE'",readonly=True).stdout)==0
    h=start_api(role)
    try: read_application(role,h)
    finally: end_api(role,h)
    before=snapshot(role,'v008-seeded')
    for version in ['009.01','009.02','009.03','009.04']: harness(role,version)
    candidate_assertions(role)
    final=snapshot(role,'candidate-baseline'); compare(before,final,True)
    upgrade=json.loads((PRIVATE/'upgrade/candidate-baseline.json').read_text())
    assert {t:v['createSql'] for t,v in final.items()}=={t:v['createSql'] for t,v in upgrade.items()},'Empty/upgrade schema differs'
    for n in [1,2]:
        h=start_api(role,True)
        try: read_application(role,h)
        finally: end_api(role,h)
        compare(final,snapshot(role,'candidate-start-'+str(n)))
    save(OUT/'empty-result.json',dict(status='PASS',startsAtV001=True,noBaseline=True,sameCandidateAndSchema=True,repeatedStartupNonDestructive=True))
    stop(role)


def run_fault(role):
    create(role); prepare_files(role); restore(role)
    expected=json.loads((BACKUP/'source-snapshot.json').read_text())
    compare(expected,snapshot(role,'before-fault'))
    files=sorted((BASE/'candidate').glob('*.sql'))
    if role.startswith('fault-ddl-'):
        limit={'fault-ddl-01':1,'fault-ddl-02':2,'fault-ddl-04':4}[role]
        script='\n'.join(p.read_text() for p in files[:limit])+"\nSIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='injected-after-ddl-boundary';"
        p=sql(role,script,expected=(1,))
        assert 'injected-after-ddl-boundary' in p.stderr.decode()
    elif role=='fault-history':
        p=harness(role,'009.01',fault_account=True,expected=(1,))
        assert int(sql(role,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='paragraph'",readonly=True).stdout)==1
        assert int(sql(role,"SELECT COUNT(*) FROM flyway_schema_history WHERE version LIKE '009%'",readonly=True).stdout)==0
    else:
        sql(role,files[0].read_text()+'\n'+files[1].read_text())
        script=files[2].read_text().replace('COMMIT;',"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='injected-backfill-failure';")
        p=sql(role,script,expected=(1,))
        assert 'injected-backfill-failure' in p.stderr.decode()
        assert int(sql(role,'SELECT COUNT(*) FROM paragraph',readonly=True).stdout)==0
        assert int(sql(role,'SELECT COUNT(*) FROM sentence WHERE paragraph_id IS NOT NULL',readonly=True).stdout)==0
    after=snapshot(role,'after-fault')
    # Compare every original cell; fault targets have no candidate history entries.
    for table,data in expected.items():
        actual=after[table]
        columns=data['columns']
        assert all(c in actual['columns'] for c in columns),'Original column missing in fault target'
        projected=[[r[actual['columns'].index(c)] for c in columns] for r in actual['rows']]
        assert projected==data['rows'],'Original cell changed in fault target '+table
    save(OUT/(role+'-result.json'),dict(status='PASS',injectedFailureObserved=True,originalCellsUnchanged=True,
        schemaAndHistoryCaptured=True,repairCleanHistoryEdit=False,preservedFailureContainer=True))
    stop(role)


def run_recovery(role):
    create(role); prepare_files(role); restore(role)
    expected=json.loads((BACKUP/'source-snapshot.json').read_text())
    compare(expected,snapshot(role,'restored-v008')); media_check(role)
    h=start_api(role)
    try:
        read_application(role,h)
        compare(expected,snapshot(role,'old-read'))
        info=continue_learning(role,h)
        after=snapshot(role,'after-continuation')
        verify_continuation_delta(expected,after,info)
    finally: end_api(role,h)
    h=start_api(role)
    try: read_application(role,h)
    finally: end_api(role,h)
    compare(after,snapshot(role,'after-restart')); media_check(role)
    save(OUT/(role+'-result.json'),dict(status='PASS',restoredFromOriginalBackup=True,oldVersionReads=True,
        genuineWritingContinuation=True,retryIdempotent=True,onlyApprovedContinuationDeltas=True,restartExact=True,mediaExact=True))
    stop(role)


def main():
    global RECORDS
    resume=sys.argv[1:]==['--resume-after-upgrade-port-check']
    assert resume or sys.argv[1:]==['--run-approved-isolated-rehearsal']
    if not resume:
        OUT.mkdir(mode=0o700,exist_ok=False); PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=False)
    else:
        prior=json.loads((OUT/'result.json').read_text())
        assert prior['status']=='BLOCKED' and prior['reason']=='AssertionError: API port occupied'
        assert (OUT/'upgrade-candidate-start-1-summary.json').exists() and not (PRIVATE/'empty').exists()
        for name in ['result.json','commands.json']:
            shutil.copyfile(OUT/name,OUT/('execution-attempt1-'+name))
        RECORDS=json.loads((OUT/'commands.json').read_text())
    assert (BACKUP/'COMPLETE').is_file()
    for item in json.loads((BACKUP/'SHA256SUMS.json').read_text()):
        path=BACKUP/item['path']; assert path.stat().st_size==item['bytes'] and digest(path)==item['sha256']
    frozen=json.loads((BASE/'candidate/candidate-manifest.json').read_text())
    for item in frozen['files']: assert digest(ROOT/item['path'])==item['sha256']
    assert not any((ROOT/'apps/api/src/main/resources/db/migration').glob('V009*'))
    if not resume: prepare_tools()
    else:
        artifacts=json.loads((OUT/'artifacts.json').read_text())
        assert digest(OLD_JAR)==artifacts['oldJarSha256'] and digest(PATCHED_JAR)==artifacts['isolatedCandidateJarSha256']
    try:
        if resume:
            print('BEGIN remaining upgrade restart check',flush=True)
            d=verify('upgrade'); call('upgrade-start-owned',[DOCKER,'start',d['containerId']])
            for _ in range(40):
                p=call('upgrade-restart-probe',[DOCKER,'exec',d['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT 1"'],expected=(0,1),private=True)
                if p.returncode==0: break
                time.sleep(1)
            else: raise RuntimeError('Owned upgrade restart timeout')
            baseline=json.loads((PRIVATE/'upgrade/candidate-baseline.json').read_text())
            compare(baseline,snapshot('upgrade','resume-before-start2'))
            h=start_api('upgrade',True)
            try: read_application('upgrade',h)
            finally: end_api('upgrade',h)
            compare(baseline,snapshot('upgrade','candidate-start-2'))
            save(OUT/'upgrade-result.json',dict(status='PASS',oldColumnsExact=True,mediaExact=True,repeatedStartupNonDestructive=True,
                resumedOnlyReadChecksAfterKnownHarnessPortIssue=True))
            stop('upgrade')
        else:
            print('BEGIN upgrade',flush=True); run_upgrade()
        print('PASS upgrade',flush=True)
        print('BEGIN empty',flush=True); run_empty(); print('PASS empty',flush=True)
        for fault in ['fault-ddl-01','fault-ddl-02','fault-ddl-04','fault-history','fault-dml']:
            print('BEGIN '+fault,flush=True); run_fault(fault); print('PASS '+fault,flush=True)
            recovery=fault.replace('fault-','recover-',1)
            print('BEGIN '+recovery,flush=True); run_recovery(recovery); print('PASS '+recovery,flush=True)
        save(OUT/'result-success.json',dict(status='PASS_PENDING_INDEPENDENT_REVIEW',B01='PASS',B03='PASS',
            sourceDatabaseTouched=False,sourceServicesTouched=False,roles=ROLES,noRepairClean=True))
        return 0
    except Exception as e:
        cleanup=[]
        for role in ROLES:
            if (PRIVATE/role/'state.json').exists():
                try: stop(role); cleanup.append(dict(role=role,stopped=True))
                except Exception as failure: cleanup.append(dict(role=role,stopped=False,errorType=type(failure).__name__))
        save(OUT/('result-failure-'+str(time.time_ns())+'.json'),dict(status='BLOCKED',reason=type(e).__name__+': '+str(e),B01='BLOCKED',B03='BLOCKED',
            sourceDatabaseTouched=False,sourceServicesTouched=False,failedTargetsPreserved=True,ownedTargetCleanup=cleanup))
        print('BLOCKED '+type(e).__name__+': '+str(e),flush=True)
        return 2
    finally:
        save(OUT/'commands.json',RECORDS,exclusive=False)


if __name__=='__main__': sys.exit(main())
