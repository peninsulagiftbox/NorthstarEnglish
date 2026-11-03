#!/usr/bin/env python3
"""Read only the R3 synthetic fixture and load it into the NEW empty-role test schema."""
import subprocess,json,os,time
import qa_runtime as q
s=q.state();assert s['namespace']=='northstar-d02-risk-20261102'
subprocess.run(['docker','start',s['containerId']],check=True,capture_output=True)
for _ in range(60):
    try:
        q.sql('SELECT 1');break
    except AssertionError:time.sleep(1)
else:raise RuntimeError('new QA database not ready')
src='northstar-qa-d02-r3-20261101'
ident=subprocess.run(['docker','exec',src,'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -Nse "SELECT @@server_uuid"'],capture_output=True,text=True,check=True).stdout.strip()
assert ident=='6b1d2208-d5ea-11f1-afc1-aecb2137fbec'
assert q.sql("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='northstar_phase01_test'")=='0','refuse overwrite'
r=subprocess.run(['docker','exec',src,'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces --set-gtid-purged=OFF northstar_phase01_test'],capture_output=True,check=True)
(q.PRIVATE/'fixture-dump.sql').write_bytes(r.stdout)
q.sql('CREATE DATABASE northstar_phase01_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci')
env=dict(os.environ,MYSQL_PWD=q.credentials()['root'])
p=subprocess.run(['/usr/local/mysql/bin/mysql','--protocol=TCP','-h127.0.0.1','-P3364','-uroot',q.SCHEMA],input=r.stdout,capture_output=True,env=env)
assert p.returncode==0,p.stderr.decode()
q.sql("GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES,TRIGGER ON northstar_phase01_test.* TO 'northstar_migrator'@'%'; GRANT SELECT,INSERT,UPDATE,DELETE ON northstar_phase01_test.* TO 'northstar_app'@'%'")
(q.OUT/'logs/fixture-clone.json').write_text(json.dumps({'source_uuid':ident,'target':s,'counts':q.db('SELECT (SELECT COUNT(*) FROM concept_review_card),(SELECT COUNT(*) FROM concept_review_source)'),'exit_code':0},indent=2))
print('clone PASS')
