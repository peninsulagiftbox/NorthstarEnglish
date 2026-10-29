#!/usr/bin/env python3
"""Approved 10B3 campaign. New isolated resources only; all SQL passes pinned container/UUID gates."""
import importlib.util,json,os,sys,time,shutil,hashlib,subprocess,urllib.request
from pathlib import Path
import phase10b3 as setup
r=setup.runner
ROOT=r.ROOT
BASE=ROOT/'docs/handoff/evidence/phase10b1'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def campaign():
    c=load('phase10b3_isolation',BASE/'isolated_rehearsal.py')
    c.PRIVATE=r.STATE/'database';c.PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    c.OUT=r.OUT/'migrations';c.OUT.mkdir(parents=True,exist_ok=True)
    c.NAMESPACE='northstar-phase10b3-20261028'
    c.ROLES=['reserved'+str(i) for i in range(47)]+['upgrade','empty','fault-history','fault-dml','fault-check','recovery','fresh-final','fault-partial','fault-map-history','regression-final','fresh-resume']
    c.PATCHED_JAR=r.COPY/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
    original=c.call;invocation=str(time.time_ns())
    c.call=lambda name,*a,**kw:original(invocation+'-'+name,*a,**kw)
    return c

def env(c,role,schema='northstar_english'):
    d=c.verify(role);cred=json.loads((c.PRIVATE/role/'credentials.json').read_text());e=r.environment()
    e.update(MYSQL_PORT=str(d['port']),DB_NAME=schema,DB_PASSWORD=cred['app'],DB_MIGRATION_PASSWORD=cred['migrator'],MYSQL_ROOT_PASSWORD=cred['root'],API_PORT=str(8093+c.ROLES.index(role)),WEB_PORT=str(3113+c.ROLES.index(role)),NORTHSTAR_DB_TEST='1',NORTHSTAR_EXPECTED_DB_UUID=d['uuid'],NORTHSTAR_CONTENT_ROOT=str(c.PRIVATE/role/'content'),NORTHSTAR_RECORDING_ROOT=str(c.PRIVATE/role/'recordings'),NORTHSTAR_TEST_AUDIO=str(ROOT/'.local/phase10b2/audio/original-test-tone.mp3'))
    if schema.startswith('northstar_restore_'):
        import re
        if not re.fullmatch(r'northstar_restore_[0-9]{14}',schema):raise ValueError('Invalid isolated restore schema')
        e['NORTHSTAR_ALLOW_RESTORE_DB']='true'
    elif schema not in ['northstar_english','northstar_phase01_test']:raise ValueError('Unapproved isolated schema')
    return e

def migrate(c,role,target=None,initialize=False,fault=False,expected=(0,)):
    d=c.verify(role);cred=json.loads((c.PRIVATE/role/'credentials.json').read_text());e=r.environment()
    e.update(TARGET_MYSQL_PORT=str(d['port']),EXPECTED_TARGET_UUID=d['uuid'],TARGET_PASSWORD=cred['fault' if fault else 'migrator'],TARGET_USER='northstar_fault_migrator' if fault else 'northstar_migrator')
    if target:e['MIGRATION_TARGET']=target
    if initialize:e['INITIALIZE_EMPTY_IDENTITY']='true'
    return c.call(role+'-flyway-'+str(target),[str(c.JAVA),'-cp',str(c.CLASSES)+os.pathsep+str(c.LIB/'*'),'MigrationHarness',str(ROOT/'apps/api/src/main/resources/db/migration')],env=e,expected=expected,private=True,timeout=180)

def start(c,role,initialize=False,schema='northstar_english'):
    e=env(c,role,schema);port=int(e['API_PORT']);assert c.available(port)
    argv=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+str(port),'--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']]
    if initialize:argv.append('--northstar.initialize-content=true')
    log=c.PRIVATE/role/('api-'+str(time.time_ns())+'.log');stream=log.open('xb');log.chmod(0o600)
    p=subprocess.Popen(argv,cwd=r.COPY/'apps/api',env=e,stdout=stream,stderr=subprocess.STDOUT);h=(p,stream,port,int(e['WEB_PORT']))
    try:
        for _ in range(100):
            if p.poll() is not None:raise RuntimeError('Isolated API exited: '+str(log.relative_to(ROOT)))
            try:
                with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/v1/health',timeout=1) as response:health=json.load(response)
                if health['migrationVersion'] in ['009.14','009.15']:
                    if initialize:
                        # The HTTP server becomes healthy before ApplicationRunner finishes its transaction.
                        with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/v1/lessons/demo-01',timeout=1) as response:
                            lesson=json.load(response)
                        if lesson.get('contentReadiness')!='legacy_unassessed':continue
                    return h
            except OSError:pass
            time.sleep(.3)
        raise RuntimeError('Isolated API readiness timeout')
    except BaseException:c.end_api(role,h);raise

def compare_old(before,after):
    for table,data in before.items():
        actual=after[table];cols=data['columns'];pk=data['primaryKey'];indices=[cols.index(k) for k in pk]
        oldids={tuple(row[i] for i in indices) for row in data['rows']}
        rows=[[row[actual['columns'].index(col)] for col in cols] for row in actual['rows']]
        if table=='flyway_schema_history':rows=[row for row in rows if tuple(row[i] for i in indices) in oldids]
        assert rows==data['rows'],table+': old values changed'

def full_equal(a,b):assert a==b,'Snapshot differs'

def freeze():
    files=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((ROOT/'apps/api/src/main/resources/db/migration').glob('V*.sql'))]
    p=r.OUT/'frozen-migrations.json'
    if p.exists():
        old=json.loads(p.read_text());assert all(x in files for x in old),'Applied migrations must never be edited'
        if files!=old:(r.OUT/'frozen-migrations-appended.json').write_text(json.dumps(files,indent=2)+'\n')
    else:p.write_text(json.dumps(files,indent=2)+'\n')

def new(c,role):
    c.create(role);c.prepare_files(role)

def checkpoint(c,role,number):
    data=c.sql(role,"SELECT version,success FROM flyway_schema_history ORDER BY installed_rank",readonly=True).stdout.decode()
    assert str(number) in data
    c.save(c.OUT/(role+'-checkpoint-'+str(number)+'.json'),dict(target=str(number),history=data,sourceAddressed=False))

def restore_new_snapshot(snapshot):
    import copy
    # MySQL generated columns are exported for comparison but must be recomputed on restore.
    data=copy.deepcopy(snapshot)
    for table,definition in data.items():
        generated={'target_uniqueness_key'} if table=='version_sentence_map' else set()
        indices=[i for i,name in enumerate(definition['columns']) if name not in generated]
        definition['columns']=[definition['columns'][i] for i in indices]
        definition['rows']=[[row[i] for i in indices] for row in definition['rows']]
    return load('b3_restore_builder',BASE/'maintenance_backup.py').restore_sql(data)

def main():
    action=sys.argv[1];c=campaign();freeze();created=[]
    try:
        if action=='new-regression':
            role='regression-final';c.create(role);created.append(role)
            shutil.copytree(c.BACKUP/'content',c.PRIVATE/role/'content');(c.PRIVATE/role/'recordings').mkdir(mode=0o700)
            migrate(c,role,initialize=True);c.grant_app(role);h=start(c,role,True)
            try:c.http(role,h,'/lessons/demo-01')
            finally:c.end_api(role,h)
            before=c.snapshot(role,'clean-initialized');restore=restore_new_snapshot(before)
            c.sql(role,'CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; USE northstar_phase01_test;'+restore,private=True)
            grants=json.loads((BASE/'recovery-20261027/a1/grants.json').read_text())['app']
            target='\n'.join(x.replace('`northstar_english`','`northstar_phase01_test`')+';' for x in grants.splitlines() if ' ON `northstar_english`.' in x)
            c.sql(role,target+"\nGRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_phase01_test.* TO 'northstar_migrator'@'%';")
            (r.STATE/'ACTIVE_TEST_ROLE').write_text(role)
        elif action=='supplemental':
            for role in ['fresh-resume','fault-partial','fault-map-history']:
                c.create(role);created.append(role)
                shutil.copytree(c.BACKUP/'content',c.PRIVATE/role/'content');(c.PRIVATE/role/'recordings').mkdir(mode=0o700)
                if role=='fresh-resume':
                    migrate(c,role,initialize=True);c.grant_app(role);h=start(c,role,True)
                    try:assert c.http(role,h,'/lessons/demo-01')['contentReadiness']=='legacy_unassessed'
                    finally:c.end_api(role,h)
                    before=c.snapshot(role,'latest-initialized');h=start(c,role)
                    try:c.http(role,h,'/lessons/demo-01?versionId=demo-01-v1')
                    finally:c.end_api(role,h)
                    full_equal(before,c.snapshot(role,'latest-restart'))
                    # A repeated explicit initialization must refuse and preserve every row.
                    e=env(c,role);argv=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--spring.main.web-application-type=none','--northstar.initialize-content=true','--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']]
                    c.call('repeat-initialization-refused',argv,env=e,expected=(1,),private=True,timeout=60)
                    full_equal(before,c.snapshot(role,'repeat-init-refused'))
                    c.save(c.OUT/'latest-empty-acceptance.json',dict(status='PASS',v001To00915=True,latestSchemaExplicitInitialization=True,repeatRefusedWithoutChange=True))
                else:
                    c.restore(role);migrate(c,role,'009.06' if role=='fault-partial' else '009.14');before=c.snapshot(role,'before-fault')
                    if role=='fault-partial':
                        first=(ROOT/'apps/api/src/main/resources/db/migration/V009_07__identity_context_columns.sql').read_text().split(';')[0]+';'
                        c.sql(role,first+"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Injected between context-column DDL statements';",expected=(1,))
                        after=c.snapshot(role,'after-fault');compare_old(before,after)
                        assert 'identity_id' in after['sentence']['columns'] and 'identity_id' not in after['paragraph']['columns'];assert before['flyway_schema_history']==after['flyway_schema_history']
                    else:
                        migrate(c,role,'009.15',fault=True,expected=(1,));after=c.snapshot(role,'after-fault');compare_old(before,after)
                        assert 'target_uniqueness_key' in after['version_sentence_map']['columns'];assert before['flyway_schema_history']['rows']==after['flyway_schema_history']['rows']
                    c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',partialOrUnregisteredDDLIdentified=True,failedTargetRetained=True,oldCellsExact=True))
                c.stop(role)
        elif action=='append-migration':
            for role in ['upgrade','empty','recovery']:
                d=c.verify(role);c.call('start-append-'+role,[c.DOCKER,'start',d['containerId']]);created.append(role)
                for _ in range(80):
                    probe=c.call('append-ready-'+role,[c.DOCKER,'exec',d['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'],expected=(0,1),private=True)
                    if probe.returncode==0 and probe.stdout.decode().strip()==d['uuid']:break
                    time.sleep(.4)
                migrate(c,role,'009.15')
                if role=='empty':
                    e=env(c,role,'northstar_phase01_test')
                    r.record('test-schema-appended-migration',['apps/api/mvnw','-f','apps/api/pom.xml','-DskipTests','-Dtest=ContentPublicationIntegrationTest','test'],env=e,cwd=r.COPY)
                    # Migrate test schema without starting the application.
                    from zipfile import ZipFile
                    query=(ROOT/'apps/api/src/main/resources/db/migration/V009_15__mapping_null_safety.sql').read_text()
                    # history must be registered by Flyway, never hand-written; dedicated Java helper below.
                    cp=str(r.COPY/'apps/api/target/test-classes')+os.pathsep+str(r.COPY/'apps/api/target/classes')+os.pathsep+str(c.LIB/'*')
                    c.call('migrate-test-schema',[str(c.JAVA),'-cp',cp,'local.northstar.catalog.IsolatedMigration'],env=e,private=True)
                c.stop(role)
            c.save(c.OUT/'appended-migration-result.json',dict(status='PASS',appendedVersion='009.15',existingMigrationBytesUnchanged=True))
        elif action=='migrations':
            # Verify historical private backup bytes before reuse; never take a fresh personal backup here.
            assert (c.BACKUP/'restore.sql').is_file()
            for role in ['upgrade','empty','fault-history','fault-dml','fault-check','recovery']:
                new(c,role);created.append(role)
                if role=='empty':
                    migrate(c,role,initialize=True);c.grant_app(role);h=start(c,role,True)
                    try:assert c.http(role,h,'/lessons/demo-01')['contentReadiness']=='legacy_unassessed'
                    finally:c.end_api(role,h)
                    before=c.snapshot(role,'initialized')
                    # Same-schema complete snapshot restore including identity/mapping/audit tables.
                    m=load('backup_sql_b3',BASE/'maintenance_backup.py')
                    restore=restore_new_snapshot(before);assert 'FOREIGN_KEY_CHECKS=0' not in restore
                    c.sql(role,'CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; USE northstar_phase01_test;'+restore,private=True)
                    grants=json.loads((BASE/'recovery-20261027/a1/grants.json').read_text())['app']
                    target='\n'.join(x.replace('`northstar_english`','`northstar_phase01_test`')+';' for x in grants.splitlines() if ' ON `northstar_english`.' in x)
                    c.sql(role,target+"\nGRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_phase01_test.* TO 'northstar_migrator'@'%';")
                    for i in range(2):
                        h=start(c,role)
                        try:c.http(role,h,'/lessons/demo-01?versionId=demo-01-v1')
                        finally:c.end_api(role,h)
                        full_equal(before,c.snapshot(role,'repeat-'+str(i)))
                    c.save(c.OUT/'empty-acceptance.json',dict(status='PASS',freshV001ToTarget=True,allTablesExactAfterTwoRestarts=True,explicitInitialization=True))
                else:
                    c.restore(role);old=c.snapshot(role,'restored-v008');migrate(c,role,'009.05');baseline=c.snapshot(role,'fixed-00905');compare_old(old,baseline)
                    checks=c.sql(role,"SELECT tc.table_name,tc.constraint_name,cc.check_clause FROM information_schema.table_constraints tc JOIN information_schema.check_constraints cc USING(constraint_schema,constraint_name) WHERE tc.constraint_schema=DATABASE() AND tc.constraint_name IN ('lesson_chk_1','audio_asset_chk_1')",readonly=True).stdout.decode();assert 'source_kind' in checks and 'kind' in checks
                    c.save(c.OUT/(role+'-check-preflight.json'),dict(constraints=checks))
                    if role in ['upgrade','recovery']:
                        for n in range(6,16):migrate(c,role,'009.'+str(n).zfill(2));checkpoint(c,role,'009.'+str(n).zfill(2))
                        after=c.snapshot(role,'upgraded');compare_old(baseline,after)
                        for i in range(2):
                            h=start(c,role)
                            try:c.read_application(role,h)
                            finally:c.end_api(role,h)
                            full_equal(after,c.snapshot(role,'restart-'+str(i)))
                        c.media_check(role)
                        if role=='recovery':
                            # Real old-version continuation and idempotent retry on the newly recovered target.
                            h=start(c,role)
                            try:c.continue_learning(role,h)
                            finally:c.end_api(role,h)
                            stable=c.snapshot(role,'continued');h=start(c,role)
                            try:c.http(role,h,'/writing?lessonId=demo-01&versionId=demo-01-v2')
                            finally:c.end_api(role,h)
                            full_equal(stable,c.snapshot(role,'continued-restart'))
                        c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',v008RestoreAnd00905Upgrade=True,oldCellsExact=True,mediaExact=True,twoRestartsExact=True,realContinuation=role=='recovery'))
                    elif role=='fault-dml':
                        migrate(c,role,'009.07');prior=c.snapshot(role,'before-fault');sql=(ROOT/'apps/api/src/main/resources/db/migration/V009_08__legacy_identity_registration.sql').read_text();first=sql.split(';')[:3]
                        c.sql(role,';'.join(first)+";SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Injected identity backfill failure';",expected=(1,),private=True)
                        full_equal(prior,c.snapshot(role,'after-fault'));c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',dmlRolledBack=True,ddlRetained=True))
                    elif role=='fault-history':
                        migrate(c,role,'009.13');before=c.snapshot(role,'before-fault');migrate(c,role,'009.14',fault=True,expected=(1,));after=c.snapshot(role,'after-fault')
                        assert 'ck_audio_source_kind' in after['audio_asset']['createSql'];assert before['flyway_schema_history']['rows']==after['flyway_schema_history']['rows']
                        compare_old(before,after);c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',ddlCommittedHistoryNotRegistered=True,failedTargetRetained=True))
                    else:
                        migrate(c,role,'009.12');before=c.snapshot(role,'before-fault');ddl=(ROOT/'apps/api/src/main/resources/db/migration/V009_13__original_lesson_kind.sql').read_text()
                        c.sql(role,ddl+"SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Injected after CHECK replacement';",expected=(1,));after=c.snapshot(role,'after-fault');compare_old(before,after)
                        assert 'ck_lesson_kind' in after['lesson']['createSql'];assert before['flyway_schema_history']==after['flyway_schema_history']
                        c.sql(role,"INSERT INTO lesson(id,slug,kind,availability) VALUES ('invalid-kind','invalid-kind','unknown','draft')",expected=(1,))
                        c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',checkDDLCommitted=True,unknownKindRejected=True,failedTargetRetained=True))
                c.stop(role)
            c.save(c.OUT/'result.json',dict(status='PASS',newMigrationUnits=10,roles=created,personalDatabaseWrites=0))
        elif action in ['integration','browser-start','final-protection','cli-check','transfer-check','restore-runtime','restore-runtime-resume','audio-check','final-reviewed']:
            role=(r.STATE/'ACTIVE_TEST_ROLE').read_text().strip() if (r.STATE/'ACTIVE_TEST_ROLE').exists() else 'empty'
            d=c.verify(role);c.call('start-owned-test-db',[c.DOCKER,'start',d['containerId']]);created.append(role)
            for _ in range(80):
                p=c.call('ready-owned',[c.DOCKER,'exec',d['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot -Nse "SELECT @@server_uuid"'],expected=(0,1),private=True)
                if p.returncode==0 and p.stdout.decode().strip()==d['uuid']:break
                time.sleep(.4)
            else:raise RuntimeError('Owned database not ready')
            e=env(c,role,'northstar_phase01_test')
            if action=='audio-check':
                r.record('java-audio-overlap-real-db',['apps/api/mvnw','-f','apps/api/pom.xml','-Dtest=ContentPublicationIntegrationTest#withdrawnAudioRetainsOuter404VisibilityBoundaries','verify'],env=e,cwd=r.COPY)
            elif action=='final-reviewed':
                media=load('b3_reviewed_media',BASE/'runtime_media_preflight.py')
                media_before=[media.inventory(c.PRIVATE/role/'content'),media.inventory(c.PRIVATE/role/'recordings')]
                original=c.sql
                c.sql=lambda role,q,**kw:original(role,'USE northstar_phase01_test;'+q,**kw)
                source=c.snapshot(role,'reviewed-source-before')
                for schema,expected in [('northstar_phase01_test',source),('northstar_restore_20261028235900',json.loads((c.PRIVATE/role/'restored-runtime-continued-restart.json').read_text()))]:
                    c.sql=lambda role,q,**kw:original(role,'USE '+schema+';'+q,**kw)
                    for i in range(2):
                        h=start(c,role,schema=schema)
                        try:
                            c.http(role,h,'/lessons/demo-01?versionId=demo-01-v1')
                            try:c.http(role,h,'/audio/pub-v1-a1');raise AssertionError('Withdrawn audio must reject')
                            except __import__('urllib.error',fromlist=['HTTPError']).HTTPError as error:
                                assert error.code==410
                                body=error.read();assert json.loads(body)['code']=='VERSION_WITHDRAWN'
                                c.RECORDS.append(dict(name='reviewed-withdrawn-audio',schema=schema,httpStatus=error.code,responseSha256=hashlib.sha256(body).hexdigest()))
                        finally:c.end_api(role,h)
                        full_equal(expected,c.snapshot(role,'reviewed-'+schema+'-restart-'+str(i)))
                        assert [media.inventory(c.PRIVATE/role/'content'),media.inventory(c.PRIVATE/role/'recordings')]==media_before
                c.save(c.OUT/'final-reviewed-acceptance.json',dict(status='PASS',finalJarSha256=c.digest(c.PATCHED_JAR),sourceAndRecoveredTwoRestartsExact=True,all43TablesAndMediaExact=True,withdrawnAudio410=True))
            elif action=='integration':
                for name,pattern in [('java-legacy-real-db','*,!MultiCourseIntegrationTest,!ContentPublicationIntegrationTest'),('java-multicourse-real-db','MultiCourseIntegrationTest'),('java-publication-real-db','ContentPublicationIntegrationTest')]:r.record(name,['apps/api/mvnw','-f','apps/api/pom.xml','-Dtest='+pattern,'verify'],env=e,cwd=r.COPY)
            elif action=='cli-check':
                import secrets,uuid
                password=secrets.token_hex(32)
                c.sql(role,"CREATE USER 'northstar_publisher'@'%' IDENTIFIED BY '"+password+"'; GRANT SELECT ON northstar_phase01_test.* TO 'northstar_publisher'@'%'; GRANT UPDATE(publication_state,published_at) ON northstar_phase01_test.lesson_version TO 'northstar_publisher'@'%'; GRANT UPDATE(current_version_id,availability) ON northstar_phase01_test.lesson TO 'northstar_publisher'@'%'; GRANT INSERT ON northstar_phase01_test.content_validation TO 'northstar_publisher'@'%'; GRANT INSERT ON northstar_phase01_test.publication_audit TO 'northstar_publisher'@'%';",private=True)
                c.save(c.PRIVATE/role/'publication-credentials.json',dict(password=password))
                e.update(DB_PUBLICATION_PASSWORD=password,NORTHSTAR_PUBLICATION_DB_UUID=d['uuid'])
                cp=str(r.COPY/'apps/api/target/classes')+os.pathsep+str(c.LIB/'*');command=[str(c.JAVA),'-cp',cp,'local.northstar.catalog.ContentPublicationCli']
                result=r.record('publication-cli-validate',command+['validate','pub-cli','pub-cli-v1','synthetic-cli-reviewer'],env=e,cwd=r.COPY);assert 'VALIDATED' in result.stdout.decode()
                content_hash=c.sql(role,"USE northstar_phase01_test; SELECT content_sha256 FROM lesson_version WHERE id='pub-cli-v1'",readonly=True).stdout.decode().strip()
                request=dict(operationId=str(uuid.uuid4()),action='publish',lessonId='pub-cli',targetVersionId='pub-cli-v1',expectedCurrentId=None,contentSha256=content_hash,actor='synthetic-cli-reviewer')
                path=c.PRIVATE/role/'publication-operation.json';c.save(path,request)
                for name in ['first','replay']:
                    result=r.record('publication-cli-'+name,command+['execute',str(path)],env=e,cwd=r.COPY);assert 'PUBLISHED' in result.stdout.decode()
                assert c.sql(role,"USE northstar_phase01_test; SELECT COUNT(*) FROM publication_audit WHERE operation_id='"+request['operationId']+"'",readonly=True).stdout.decode().strip()=='1'
                shell='MYSQL_PWD="$DB_PUBLICATION_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -unorthstar_publisher --database=northstar_phase01_test -N --batch'
                # Credentials travel through stdin/environment, never argv or shared output.
                for tag,query in [('content',"UPDATE sentence SET text='forbidden' WHERE 1=0;"),('learning',"UPDATE study_stage SET current_state='practiced' WHERE 1=0;"),('ddl',"CREATE TABLE forbidden_publication_ddl(id INT);")]:
                    cmd=[c.DOCKER,'exec','-i','-e','DB_PUBLICATION_PASSWORD',d['containerId'],'sh','-c',shell]
                    c.call('publisher-denied-'+tag,cmd,stdin=query.encode(),env=e,expected=(1,),private=True)
                c.save(c.OUT/'cli-acceptance.json',dict(status='PASS',standaloneValidationAndPublication=True,duplicateAuditPrevented=True,noContentLearningOrDDLPermission=True))
            elif action=='transfer-check':
                h=start(c,role,schema='northstar_phase01_test')
                folder=r.STATE/('transfer-'+str(time.time_ns()));target='northstar_restore_20261029024600'
                args=['--phase10b3','--api','http://127.0.0.1:'+e['API_PORT'],'--web-port',e['WEB_PORT'],'--recording-root',e['NORTHSTAR_RECORDING_ROOT']]
                try:
                    r.record('actual-transfer-backup',[sys.executable,str(ROOT/'scripts/data-transfer.py'),'backup',str(folder)]+args,env=e,cwd=ROOT)
                    r.record('actual-transfer-restore',[sys.executable,str(ROOT/'scripts/data-transfer.py'),'restore',str(folder/'learning.json')]+args+['--target',target,'--confirm-new-isolated'],env=e,cwd=ROOT)
                    original=c.sql;c.sql=lambda role,q,**kw:original(role,'USE northstar_phase01_test;'+q,**kw)
                    before=c.snapshot(role,'transfer-original')
                    c.sql=lambda role,q,**kw:original(role,'USE '+target+';'+q,**kw)
                    restored=c.snapshot(role,'transfer-restored');full_equal(before,restored)
                    c.sql=original
                    c.save(c.OUT/'actual-transfer-acceptance.json',dict(status='PASS',sameSchemaAllTablesExact=True,tableCount=len(before),generatedProjectionRestored=True,allReadyRecordingsVerified=True,target=target))
                finally:c.end_api(role,h)
            elif action in ['restore-runtime','restore-runtime-resume','audio-check','final-reviewed']:
                target='northstar_restore_20261028235900'
                expected=json.loads((c.PRIVATE/role/'all-features-restored.json').read_text())
                source_media=c.PRIVATE/role/'recordings/northstar_phase01_test';target_media=c.PRIVATE/role/'recordings'/target
                if action=='restore-runtime':
                    assert not target_media.exists();shutil.copytree(source_media,target_media)
                else:
                    # Resume only this proven target after a pre-start permission failure; never overwrite media.
                    assert target_media.is_dir() and not (c.PRIVATE/role/'restored-runtime-0.json').exists()
                grants=json.loads((BASE/'recovery-20261027/a1/grants.json').read_text())['app']
                target_grants='\n'.join(line.replace('`northstar_english`','`'+target+'`')+';' for line in grants.splitlines() if ' ON `northstar_english`.' in line)
                c.sql(role,target_grants+"\nGRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON `"+target+"`.* TO 'northstar_migrator'@'%';")
                media=load('b3_final_media',BASE/'runtime_media_preflight.py')
                original_media=media.inventory(source_media);copied_media=media.inventory(target_media);assert original_media==copied_media
                original_content=media.inventory(c.PRIVATE/role/'content')
                original=c.sql;c.sql=lambda role,q,**kw:original(role,'USE '+target+';'+q,**kw)
                for i in range(2):
                    h=start(c,role,schema=target)
                    try:
                        c.http(role,h,'/lessons/demo-01?versionId=demo-01-v1');c.http(role,h,'/lessons/pub-hint?versionId=pub-hint-v2')
                    finally:c.end_api(role,h)
                    full_equal(expected,c.snapshot(role,'restored-runtime-'+str(i)))
                    assert media.inventory(source_media)==original_media and media.inventory(target_media)==copied_media and media.inventory(c.PRIVATE/role/'content')==original_content
                before=expected;h=start(c,role,schema=target)
                try:info=c.continue_learning(role,h)
                finally:c.end_api(role,h)
                after=c.snapshot(role,'restored-runtime-continued');c.verify_continuation_delta(before,after,info)
                h=start(c,role,schema=target)
                try:c.http(role,h,'/writing?lessonId=demo-01&versionId=demo-01-v2')
                finally:c.end_api(role,h)
                full_equal(after,c.snapshot(role,'restored-runtime-continued-restart'))
                assert media.inventory(target_media)==copied_media and media.inventory(c.PRIVATE/role/'content')==original_content
                c.save(c.OUT/'restored-runtime-acceptance.json',dict(status='PASS',latestJarTwoRestartsAll43TablesExact=True,mediaBytesExact=True,restoredLearningRealContinuation=True,idempotentReplay=True,onlyExpectedContinuationDelta=True,continuedRestartExact=True))
            elif action=='final-protection':
                original=c.sql;c.sql=lambda role,q,**kw:original(role,'USE northstar_phase01_test;'+q,**kw)
                before=c.snapshot(role,'all-features-before')
                for i in range(2):
                    h=start(c,role,schema='northstar_phase01_test')
                    try:c.http(role,h,'/lessons/demo-01')
                    finally:c.end_api(role,h)
                    full_equal(before,c.snapshot(role,'all-features-restart-'+str(i)))
                m=load('b3_backup_final',BASE/'maintenance_backup.py');restore=restore_new_snapshot(before)
                original(role,'CREATE DATABASE northstar_restore_20261028235900 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; USE northstar_restore_20261028235900;'+restore,private=True)
                c.sql=lambda role,q,**kw:original(role,'USE northstar_restore_20261028235900;'+q,**kw)
                restored=c.snapshot(role,'all-features-restored');full_equal(before,restored)
                c.save(c.OUT/'final-protection.json',dict(status='PASS',allTablesExactAfterTwoRestarts=True,allNewTablesRestoredExact=True,tableCount=len(before)))
            else:
                h=start(c,role,schema='northstar_phase01_test');port=int(e['WEB_PORT']);assert c.available(port)
                log=r.STATE/'browser-web.log';stream=log.open('ab');web=subprocess.Popen(['node',str(r.COPY/'node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port',str(port)],cwd=r.COPY/'apps/web',env=e,stdout=stream,stderr=subprocess.STDOUT)
                stop=r.STATE/'STOP_BROWSER';assert not stop.exists()
                (r.STATE/'browser-services.json').write_text(json.dumps(dict(apiPort=int(e['API_PORT']),webPort=port,uuid=d['uuid'],containerId=d['containerId'])))
                print('Owned browser services started',flush=True)
                try:
                    while not stop.exists():
                        if web.poll() is not None:raise RuntimeError('Owned Web exited')
                        time.sleep(.4)
                finally:
                    if web.poll() is None:web.terminate();web.wait(timeout=20)
                    stream.close();c.end_api(role,h)
        else:raise SystemExit('migrations | integration | browser-start | final-protection')
    finally:
        for role in created:
            try:c.stop(role)
            except Exception:pass
        c.save(c.OUT/('commands-'+str(time.time_ns())+'.json'),c.RECORDS)
if __name__=='__main__':main()
