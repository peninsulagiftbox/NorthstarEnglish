#!/usr/bin/env python3
"""Fail closed on DDL/DML/history faults; recover only by restoring to another new isolated target."""
import copy,hashlib,json,shutil,sys,time
from pathlib import Path
import phase10c2_isolated as iso
r=iso.r

def main():
    c=iso.campaign();stamp=str(time.time_ns());c.PRIVATE=r.STATE/'migration-retest'/stamp;c.PRIVATE.mkdir(parents=True)
    c.OUT=r.OUT/'migration-retest'/stamp;c.OUT.mkdir(parents=True);c.NAMESPACE='northstar-c2-retest-'+stamp
    c.BACKUP=r.ROOT/'.local/phase10c-release/20261031T105434/backup'
    assert (c.BACKUP/'restore.sql').exists()
    first=3350
    while any(not c.available(first+i) for i in range(6)):first+=4
    assert first+5<3399
    c.ROLES=['reserved'+str(i) for i in range(first-3313)]+['ddl','dml','history','anomaly','recovery','constraints']
    checks=[]
    roles=('constraints',) if '--constraints-only' in sys.argv else (('anomaly',) if '--anomaly-only' in sys.argv else ('ddl','dml','history','anomaly','constraints','recovery'))
    for role in roles:
        created=False
        try:
            c.create(role);created=True;c.prepare_files(role);c.restore(role)
            before=c.snapshot(role,'before');iso.migrate(c,role,'010.06');baseline=c.snapshot(role,'v01006');iso.base.compare_old(before,baseline)
            if role=='ddl':
                c.sql(role,"REVOKE CREATE ON northstar_english.* FROM 'northstar_migrator'@'%';")
                failed=iso.migrate(c,role,expected=(1,));assert failed.returncode==1
                assert c.sql(role,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='exercise_set'",readonly=True).stdout.decode().strip()=='0'
            elif role=='dml':
                iso.migrate(c,role,'011.05')
                c.sql(role,"CREATE TRIGGER c2_retest_reject_item BEFORE INSERT ON exercise_set_item FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='isolated backfill rollback probe';")
                failed=iso.migrate(c,role,expected=(1,));assert failed.returncode==1
                for table in ('exercise_set','exercise_set_item','quiz_run_item'):
                    assert c.sql(role,'SELECT COUNT(*) FROM '+table,readonly=True).stdout.decode().strip()=='0',table
                assert c.sql(role,'SELECT COUNT(*) FROM quiz_run WHERE total_count IS NOT NULL',readonly=True).stdout.decode().strip()=='0'
            elif role=='constraints':
                iso.migrate(c,role,'011.05')
                sid='12345678-1234-1234-1234-123456789abc'
                c.sql(role,f"INSERT INTO exercise_set(id,version_id,purpose,protocol_version,snapshot_origin) VALUES ('{sid}','demo-01-v2','practice','quiz_choice_v1','version_content');")
                def insert(where,ordinal,sentence='sentence_id',version='version_id'):
                    return f"INSERT INTO exercise_set_item(set_id,exercise_id,version_id,sentence_id,knowledge_point_id,ordinal,question_json,item_hash) SELECT '{sid}',exercise_id,{version},{sentence},knowledge_point_id,{ordinal},payload_json,REPEAT('0',64) FROM quiz_question WHERE {where};"
                c.sql(role,insert("exercise_id='demo-01-v2-quiz-01'",1))
                for label,query,code in [
                    ('duplicate-member',insert("exercise_id='demo-01-v2-quiz-01'",2),'1062'),
                    ('duplicate-ordinal',insert("exercise_id='demo-01-v2-quiz-02'",1),'1062'),
                    ('ordinal-check',insert("exercise_id='demo-01-v2-quiz-02'",0),'3819'),
                    ('sentence-context-fk',insert("exercise_id='demo-01-v2-quiz-02'",2,"'demo-01-v2-s01'"),'1452'),
                    ('version-context-fk',insert("exercise_id='demo-01-v1-quiz-01'",2),'1452')]:
                    failure=c.sql(role,query,expected=(1,));assert code in failure.stderr.decode(),label
                    assert c.sql(role,'SELECT COUNT(*) FROM exercise_set_item',readonly=True).stdout.decode().strip()=='1'
                    print(label,'PASS',flush=True)
            elif role=='history':
                c.sql(role,"DELIMITER //\nCREATE TRIGGER c2_retest_reject_history BEFORE INSERT ON flyway_schema_history FOR EACH ROW BEGIN IF NEW.version='011.02' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='isolated history write probe'; END IF; END//\nDELIMITER ;")
                failed=iso.migrate(c,role,expected=(1,));assert failed.returncode==1
                assert c.sql(role,"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='exercise_set'",readonly=True).stdout.decode().strip()=='1'
                assert c.sql(role,"SELECT COUNT(*) FROM flyway_schema_history WHERE version='011.02' AND success=1",readonly=True).stdout.decode().strip()=='0'
            elif role=='anomaly':
                c.sql(role,"UPDATE quiz_run SET correct_count=IF(correct_count=3,2,3) LIMIT 1")
                before=c.snapshot(role,'anomalous-input')
                assert iso.migrate(c,role,expected=(1,)).returncode==1
                assert c.sql(role,'SELECT COUNT(*) FROM exercise_set',readonly=True).stdout.decode().strip()=='0'
            else:
                iso.migrate(c,role);iso.grant(c,role)
                target=c.snapshot(role,'recovered');iso.base.compare_old(before,target)
                assert c.sql(role,"SELECT version FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 1",readonly=True).stdout.decode().strip()=='011.09'
                assert c.sql(role,'SELECT COUNT(*) FROM quiz_run_item',readonly=True).stdout.decode().strip()=='6'
            after=c.snapshot(role,'after');iso.base.compare_old(before,after)
            checks.append(dict(role=role,status='PASS',oldCellsExact=True,targetRetained=True))
            print(role,'PASS',flush=True)
        finally:
            if created:c.stop(role)
    result=dict(status='PASS',backupSha256=hashlib.sha256((c.BACKUP/'restore.sql').read_bytes()).hexdigest(),checks=checks,notes='Failure targets preserved; no repair/clean/history edits. Recovery restored same fixed backup to a new UUID/container.')
    c.save(c.OUT/'acceptance.json',result);print(json.dumps(result))
if __name__=='__main__':main()
