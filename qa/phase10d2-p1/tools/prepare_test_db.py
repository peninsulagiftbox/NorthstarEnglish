#!/usr/bin/env python3
"""New UUID-guarded MySQL instance for destructive Java fixture tests only."""
import sys,json,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import phase10d_isolated as p
c=p.campaign();c.NAMESPACE='northstar-d02-p1-20261102';c.ROLES=['reserved'+str(i) for i in range(60)]+['p1']
c.PRIVATE=ROOT/'.local/d02-p1/database';c.OUT=ROOT/'qa/phase10d2-p1/evidence/database';c.PRIVATE.mkdir(parents=True,exist_ok=True);c.OUT.mkdir(parents=True,exist_ok=True)
c.PATCHED_JAR=ROOT/'.local/d02-p1/previous-frozen.jar'
c.create('p1');c.prepare_files('p1');p.migrate(c,'p1',initialize=True);p.grant(c,'p1')
h=p.start(c,'p1',True);c.end_api('p1',h)
s=c.verify('p1')
r=c.call('dump-demo',['docker','exec',s['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF northstar_english'],private=True)
c.sql('p1','CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;')
c.call('load-test',['docker','exec','-i',s['containerId'],'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot northstar_phase01_test'],stdin=r.stdout,private=True)
c.sql('p1',"GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,DROP,ALTER,INDEX,REFERENCES,TRIGGER ON northstar_phase01_test.* TO 'northstar_migrator'@'%'; GRANT SELECT,INSERT,UPDATE,DELETE ON northstar_phase01_test.* TO 'northstar_app'@'%';")
creds=json.loads((c.PRIVATE/'p1/credentials.json').read_text())
env={k:v for k,v in os.environ.items() if not k.startswith(('SPRING_','NORTHSTAR_'))}
env.update(DB_NAME='northstar_phase01_test',MYSQL_PORT=str(s['port']),DB_PASSWORD=creds['app'],DB_MIGRATION_PASSWORD=creds['migrator'],NORTHSTAR_DB_TEST='1',NORTHSTAR_EXPECTED_DB_UUID=s['uuid'],NORTHSTAR_CONTENT_ROOT=str(c.PRIVATE/'p1/content'),NORTHSTAR_RECORDING_ROOT=str(c.PRIVATE/'p1/recordings'),NORTHSTAR_TEST_AUDIO=str(ROOT/'.local/phase10b2/audio/original-test-tone.mp3'),API_PORT='8187',WEB_PORT='3196',JAVA_HOME=str(ROOT/'.local/jdk21/jdk-21.0.12.1+1/Contents/Home'))
env['PATH']=env['JAVA_HOME']+'/bin:'+env['PATH']
path=ROOT/'.local/d02-p1/test-env.json';path.write_text(json.dumps(env));path.chmod(0o600)
print('READY',s['port'],s['uuid'])
