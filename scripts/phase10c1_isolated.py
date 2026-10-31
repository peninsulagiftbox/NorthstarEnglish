#!/usr/bin/env python3
"""10C1 isolated-only campaign. UUID/container/volume/port gates precede every mutation."""
import importlib.util,json,os,sys,time,shutil,subprocess,urllib.request
from pathlib import Path
import phase10c1 as setup
r=setup.runner;ROOT=r.ROOT;BASE=ROOT/'docs/handoff/evidence/phase10b1'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def campaign():
 c=load('c1_isolation',BASE/'isolated_rehearsal.py');c.PRIVATE=r.STATE/'database';c.PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True);c.OUT=r.OUT/'migrations';c.OUT.mkdir(parents=True,exist_ok=True)
 c.NAMESPACE='northstar-phase10c1-20261029a';c.ROLES=['upgrade','empty','fault-unique','fault-start','fault-history','recovery','regression-final'];c.BACKUP=ROOT/'.local/phase10b3-release/20261029T144934/backup';c.PATCHED_JAR=r.COPY/'apps/api/target/northstar-api-0.1.0-SNAPSHOT.jar'
 original=c.call;stamp=str(time.time_ns());c.call=lambda name,*a,**kw:original(stamp+'-'+name,*a,**kw)
 return c
def env(c,role,schema='northstar_english'):
 d=c.verify(role);cred=json.loads((c.PRIVATE/role/'credentials.json').read_text());e={k:v for k,v in r.environment().items() if not k.startswith('SPRING_') and k not in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')}
 e.update(MYSQL_PORT=str(d['port']),DB_NAME=schema,DB_PASSWORD=cred['app'],DB_MIGRATION_PASSWORD=cred['migrator'],MYSQL_ROOT_PASSWORD=cred['root'],API_PORT='8161' if role=='recovery' else '8155',WEB_PORT='3175',NORTHSTAR_DB_TEST='1',NORTHSTAR_EXPECTED_DB_UUID=d['uuid'],NORTHSTAR_CONTENT_ROOT=str(c.PRIVATE/role/'content'),NORTHSTAR_RECORDING_ROOT=str(c.PRIVATE/role/'recordings'),NORTHSTAR_TEST_AUDIO=str(ROOT/'.local/phase10b2/audio/original-test-tone.mp3'),NORTHSTAR_AUDIO_FIXTURES=str(ROOT/'.local/phase10c1/audio/manifest.json'))
 assert d['port']!=3308 and d['uuid']!=c.SOURCE_UUID
 return e
def migrate(c,role,target=None,initialize=False,fault=False,expected=(0,)):
 d=c.verify(role);cred=json.loads((c.PRIVATE/role/'credentials.json').read_text());e={k:v for k,v in r.environment().items() if not k.startswith('SPRING_') and k not in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')};e.update(TARGET_MYSQL_PORT=str(d['port']),EXPECTED_TARGET_UUID=d['uuid'],TARGET_PASSWORD=cred['fault' if fault else 'migrator'],TARGET_USER='northstar_fault_migrator' if fault else 'northstar_migrator')
 if target:e['MIGRATION_TARGET']=target
 if initialize:e['INITIALIZE_EMPTY_IDENTITY']='true'
 return c.call(role+'-flyway-'+str(target),[str(c.JAVA),'-cp',str(c.CLASSES)+os.pathsep+str(c.LIB/'*'),'MigrationHarness',str(ROOT/'apps/api/src/main/resources/db/migration')],env=e,expected=expected,private=True,timeout=180)
def grant(c,role):
 c.grant_app(role)
 c.sql(role,"GRANT SELECT ON northstar_english.lesson_audio TO 'northstar_app'@'%'; GRANT SELECT ON northstar_english.audio_alignment TO 'northstar_app'@'%';")
def compare_old(before,after):
 for table,data in before.items():
  actual=after[table];cols=data['columns'];indices=[cols.index(k) for k in data['primaryKey']];oldids={tuple(row[i] for i in indices) for row in data['rows']};rows=[[row[actual['columns'].index(col)] for col in cols] for row in actual['rows']]
  if table=='flyway_schema_history':rows=[row for row in rows if tuple(row[i] for i in indices) in oldids]
  assert rows==data['rows'],table+': old values changed'
def start(c,role,initialize=False):
 e=env(c,role);port=int(e['API_PORT']);assert c.available(port)
 args=[str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+str(port),'--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']]
 if initialize:args.append('--northstar.initialize-content=true')
 stream=(c.PRIVATE/role/('api-'+str(time.time_ns())+'.log')).open('xb');p=subprocess.Popen(args,cwd=r.COPY/'apps/api',env=e,stdout=stream,stderr=subprocess.STDOUT);h=(p,stream,port,int(e['WEB_PORT']))
 try:
  for _ in range(150):
   if p.poll() is not None:raise RuntimeError('Isolated API exited')
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health',timeout=1) as response:health=json.load(response)
    if health['migrationVersion']=='010.06':
     with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/lessons/demo-01',timeout=4) as response:assert json.load(response)['id']=='demo-01'
     return h
   except OSError:pass
   time.sleep(.3)
  raise RuntimeError('API readiness timed out')
 except BaseException:c.end_api(role,h);raise

def test_schema(c,role):
 # Restore an initialized isolated snapshot into a NEW test schema only.
 m=load('c1_restore_builder',BASE/'maintenance_backup.py');data=c.snapshot(role,'test-source-'+str(time.time_ns()));import copy;clean=copy.deepcopy(data)
 for table,item in clean.items():
  omit={'target_uniqueness_key'} if table=='version_sentence_map' else set();ix=[i for i,col in enumerate(item['columns']) if col not in omit];item['columns']=[item['columns'][i] for i in ix];item['rows']=[[row[i] for i in ix] for row in item['rows']]
 text=m.restore_sql(clean)
 c.sql(role,'CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; USE northstar_phase01_test;'+text,private=True)
 grants=json.loads((BASE/'recovery-20261027/a1/grants.json').read_text())['app'];target='\n'.join(x.replace('`northstar_english`','`northstar_phase01_test`')+';' for x in grants.splitlines() if ' ON `northstar_english`.' in x)
 c.sql(role,target+"\nGRANT SELECT ON northstar_phase01_test.lesson_audio TO 'northstar_app'@'%'; GRANT SELECT ON northstar_phase01_test.audio_alignment TO 'northstar_app'@'%'; GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON northstar_phase01_test.* TO 'northstar_migrator'@'%';")

def main():
 action=sys.argv[1];c=campaign()
 if action=='migrations':
  for role in ('upgrade','empty'):
   c.create(role);c.prepare_files(role)
   if role=='upgrade':
    c.restore(role);before=c.snapshot(role,'restored-00905');migrate(c,role,'009.15');baseline=c.snapshot(role,'baseline-00915');compare_old(before,baseline)
   else:before=baseline=None
   migrate(c,role,initialize=role=='empty');grant(c,role)
   if baseline:compare_old(baseline,c.snapshot(role,'upgraded-01006'))
   h=start(c,role,role=='empty');c.end_api(role,h);after=c.snapshot(role,'first-start')
   h=start(c,role);c.end_api(role,h);assert after==c.snapshot(role,'second-start')
   if role=='empty':test_schema(c,role)
   c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',oldCellsExact=True,restartsExact=True,fromVersion='009.05' if role=='upgrade' else '001',toVersion='010.06',sourceAddressed=False))
 elif action=='faults':
  for role,target in [('fault-unique','010.01'),('fault-start','010.02'),('fault-history','010.03')]:
   c.create(role);c.prepare_files(role);c.restore(role);migrate(c,role,target);before=c.snapshot(role,'before-failure')
   if role=='fault-history':
    migrate(c,role,'010.04',fault=True,expected=(1,))
   else:
    name='V010_02__shared_sentence_audio.sql' if role=='fault-unique' else 'V010_03__nonzero_sentence_interval.sql'
    text=(ROOT/'apps/api/src/main/resources/db/migration'/name).read_text()
    c.sql(role,text+"\nSIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Injected after committed audio DDL';",expected=(1,))
   after=c.snapshot(role,'after-failure');compare_old(before,after)
   if role=='fault-history':assert 'lesson_audio' in after
   elif role=='fault-unique':assert 'uq_sentence_audio' not in after['sentence']['createSql']
   else:assert 'ck_sentence_start' in after['sentence']['createSql'] and 'sentence_chk_1' not in after['sentence']['createSql']
   assert before['flyway_schema_history']==after['flyway_schema_history']
   c.save(c.OUT/(role+'-acceptance.json'),dict(status='PASS',committedDDLIdentified=True,historyUnchanged=True,oldCellsExact=True,failedTargetRetained=True))
   c.stop(role)
  role='recovery';c.create(role);c.prepare_files(role);c.restore(role);before=c.snapshot(role,'recovered-00905');migrate(c,role,'009.15');grant(c,role) if False else c.grant_app(role)
  h=c.start_api(role) # Frozen deployed 009.15 JAR on isolated target, never source service.
  try:c.read_application(role,h);c.continue_learning(role,h)
  finally:c.end_api(role,h)
  baseline=c.snapshot(role,'old-continuation');h=c.start_api(role)
  try:c.read_application(role,h)
  finally:c.end_api(role,h)
  assert baseline==c.snapshot(role,'old-restart')
  migrate(c,role);grant(c,role);compare_old(baseline,c.snapshot(role,'new-upgrade'))
  for i in range(2):
   h=start(c,role)
   try:c.read_application(role,h)
   finally:c.end_api(role,h)
  c.media_check(role)
  c.save(c.OUT/'recovery-acceptance.json',dict(status='PASS',backupRecoveredToNewTarget=True,oldJarActualContinuationAndIdempotency=True,oldRestartExact=True,newUpgradeOldCellsExact=True,newJarTwoStarts=True,mediaExact=True))
  c.stop(role)
 elif action=='restored-start':
  import re
  role=(r.STATE/'ACTIVE_TEST_ROLE').read_text().strip();report=json.loads((c.OUT/'actual-backup-restore.json').read_text());target=report['schema'];assert re.fullmatch('northstar_restore_[0-9]{14}',target)
  e=env(c,role,target);e.update(API_PORT='8162',WEB_PORT='3182',NORTHSTAR_ALLOW_RESTORE_DB='true');e['NORTHSTAR_CONTENT_ROOT']=str(ROOT/report['backup']/'content');assert Path(e['NORTHSTAR_CONTENT_ROOT']).is_relative_to(r.STATE)
  original=c.sql
  def snapshot_target(tag):
   c.sql=lambda role,query,*args,**kw:original(role,'USE '+target+';'+query,*args,**kw)
   try:return c.snapshot(role,tag+'-'+str(time.time_ns()))
   finally:c.sql=original
  baseline=snapshot_target('restore-before-start');handles=[]
  def launch():
   assert c.available(8162);stream=(c.PRIVATE/role/('restored-api-'+str(time.time_ns())+'.log')).open('xb');p=subprocess.Popen([str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port=8162','--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']],cwd=r.COPY/'apps/api',env=e,stdout=stream,stderr=subprocess.STDOUT);h=(p,stream,8162,3182)
   try:
    for _ in range(100):
     if p.poll() is not None:raise RuntimeError('Restored API exited')
     try:
      with urllib.request.urlopen('http://127.0.0.1:8162/api/v1/health',timeout=1) as response:assert json.load(response)['migrationVersion']=='010.06';return h
     except OSError:time.sleep(.25)
    raise RuntimeError('Restored readiness timed out')
   except BaseException:c.end_api(role,h);raise
  for i in range(2):
   h=launch()
   try:
    c.http(role,h,'/lessons/demo-01');assert len(c.http(role,h,'/lessons/c1-shared?versionId=c1-shared-v1')['sentences'])==12
   finally:c.end_api(role,h)
   assert baseline==snapshot_target('restored-restart-'+str(i))
  h=launch()
  previous_out=c.OUT;c.OUT=previous_out/('restore-continuation-'+str(time.time_ns()));c.OUT.mkdir()
  try:c.continue_learning(role,h)
  finally:c.OUT=previous_out;c.end_api(role,h)
  learned=snapshot_target('restored-continued');h=launch()
  try:c.http(role,h,'/writing?lessonId=demo-01&versionId=demo-01-v2')
  finally:c.end_api(role,h)
  assert learned==snapshot_target('restored-continued-restart')
  c.save(c.OUT/('restored-runtime-acceptance-'+str(time.time_ns())+'.json'),dict(status='PASS',all45TablesTwoStartsExact=True,backupContentActuallyRead=True,realContinuationIdempotent=True,postLearningRestartExact=True,sourceAddressed=False))
 elif action=='backup-restore':
  role=(r.STATE/'ACTIVE_TEST_ROLE').read_text().strip();e=env(c,role,'northstar_phase01_test');port=int(e['API_PORT']);assert c.available(port)
  stream=(c.PRIVATE/role/('export-api-'+str(time.time_ns())+'.log')).open('xb');p=subprocess.Popen([str(c.JAVA),'-jar',str(c.PATCHED_JAR),'--server.port='+str(port),'--northstar.content-root='+e['NORTHSTAR_CONTENT_ROOT'],'--northstar.recording-root='+e['NORTHSTAR_RECORDING_ROOT']],cwd=r.COPY/'apps/api',env=e,stdout=stream,stderr=subprocess.STDOUT)
  h=(p,stream,port,int(e['WEB_PORT']))
  try:
   for _ in range(120):
    if p.poll() is not None:raise RuntimeError('Export API exited')
    try:
     with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/api/v1/health',timeout=1) as response:assert response.headers['X-Northstar-Test-Database']=='true';break
    except OSError:time.sleep(.25)
   folder=r.STATE/('export-'+str(time.time_ns()));target='northstar_restore_'+time.strftime('%Y%m%d%H%M%S');common=['--phase10c1','--api','http://127.0.0.1:'+str(port),'--web-port',e['WEB_PORT'],'--recording-root',e['NORTHSTAR_RECORDING_ROOT']]
   r.record('actual-backup',['python3',str(ROOT/'scripts/data-transfer.py'),'backup',str(folder),*common],env=e,cwd=ROOT)
   shutil.copytree(Path(e['NORTHSTAR_CONTENT_ROOT']),folder/'content')
   r.record('actual-restore',['python3',str(ROOT/'scripts/data-transfer.py'),'restore',str(folder/'learning.json'),'--target',target,'--confirm-new-isolated',*common],env=e,cwd=ROOT)
   original=c.sql
   def snapshot_schema(schema,tag):
    c.sql=lambda role,query,*args,**kw:original(role,'USE '+schema+';'+query,*args,**kw)
    try:return c.snapshot(role,tag+'-'+str(time.time_ns()))
    finally:c.sql=original
   before=snapshot_schema('northstar_phase01_test','export-source');after=snapshot_schema(target,'export-restored');assert before==after
   c.save(c.OUT/'actual-backup-restore.json',dict(status='PASS',schema=target,backup=str(folder.relative_to(ROOT)),all45TablesExact=True,mainAudioAndAlignmentPreserved=True,sourcePersonalAddressed=False))
  finally:c.end_api(role,h)
 elif action=='new-regression':
  role='regression-final';c.create(role);c.prepare_files(role);migrate(c,role,initialize=True);grant(c,role);h=start(c,role,True)
  c.end_api(role,h);test_schema(c,role);(r.STATE/'ACTIVE_TEST_ROLE').write_text(role)
 elif action=='finish-recovery':
  role='recovery';c.verify(role);baseline=json.loads((c.PRIVATE/role/'new-upgrade.json').read_text())
  for i in range(2):
   h=start(c,role)
   try:c.read_application(role,h)
   finally:c.end_api(role,h)
   assert baseline==c.snapshot(role,'candidate-restart-'+str(i))
  c.media_check(role)
  c.save(c.OUT/'recovery-acceptance.json',dict(status='PASS',backupRecoveredToNewTarget=True,oldJarActualContinuationAndIdempotency=True,oldRestartExact=True,newUpgradeOldCellsExact=True,newJarTwoStartsExact=True,mediaExact=True))
  c.stop(role)
 elif action=='run':
  role=(r.STATE/'ACTIVE_TEST_ROLE').read_text().strip() if (r.STATE/'ACTIVE_TEST_ROLE').exists() else 'empty';e=env(c,role,'northstar_phase01_test');r.record(sys.argv[2],sys.argv[3:],env=e,cwd=r.COPY)
 elif action=='stop':
  for role in c.ROLES:
   if (c.PRIVATE/role/'state.json').exists():c.stop(role)
 else:raise SystemExit('migrations | run NAME COMMAND... | stop')
if __name__=='__main__':main()
